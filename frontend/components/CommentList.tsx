"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui";
import type { ApiComment } from "@/components/CommentForm";
import type { Role } from "@/lib/auth";
import { ApiError, api } from "@/lib/api";

type VoteOut = {
  voted: boolean;
  vote_count: number;
};

type CommentListOut = {
  items: ApiComment[];
  vote_count: number;
  voted_by_me: boolean | null;
};

type CommentListProps = {
  proposalId: string;
  /** Peran akun yang sedang masuk, atau null kalau anonim/belum diketahui.
   * Menentukan apakah tombol dukungan ditawarkan sama sekali: POST /vote
   * hanya untuk peran community (10-api-contract.md:82). */
  currentRole?: Role | null;
  /** Id akun yang sedang masuk, atau null kalau anonim/belum diketahui.
   * CommentOut (backend/app/schemas/community.py) tidak mengirim "is_mine":
   * komponen ini menentukannya sendiri lewat perbandingan user_id, bukan
   * membaca field yang tidak pernah ada (laporan Fase 11 Task 12). */
  currentUserId?: string | null;
};

type Keadaan = "loading" | "error" | "loaded";

// Daftar komentar dan vote komunitas (05-feature-komunitas.md). Satu keputusan
// di layar ini: apakah pembaca lain menilai proposal ini layak, dan apakah
// saya ikut menyuarakannya. Bagian ini mengambil datanya sendiri dan punya
// tiga keadaannya sendiri (memuat, galat, isi), supaya bagian lain di
// halaman proposal tidak ikut jatuh kalau komentar gagal dimuat.
//
// Sengaja TIDAK memakai --accent: anggaran aksen di halaman proposal sudah
// penuh oleh bilah funding, tombol pledge, dan penanda milestone aktif.
// Vote memakai --ink dan --line, dan statusnya terbaca lewat aria-pressed,
// bukan warna saja.
export function CommentList({
  proposalId,
  currentRole = null,
  currentUserId = null,
}: CommentListProps) {
  const [keadaan, setKeadaan] = useState<Keadaan>("loading");
  const [pesanGalat, setPesanGalat] = useState("");
  const [items, setItems] = useState<ApiComment[]>([]);
  // null berarti "belum diketahui", beda dari 0 ("diketahui kosong").
  // Sebelumnya nilainya HANYA bisa diketahui dari respons POST /vote, jadi
  // setiap pengunjung yang belum pernah menekan tombolnya membaca "Jumlah
  // dukungan belum tersedia" -- termasuk pengunjung anonim, yang memang
  // tidak boleh menekannya sama sekali, sehingga angka itu tidak pernah
  // muncul untuk mereka. GET .../comments sekarang mengirimnya.
  const [voteCount, setVoteCount] = useState<number | null>(null);
  const [votedByMe, setVotedByMe] = useState(false);
  const [voteError, setVoteError] = useState<string | null>(null);

  const muat = useCallback(async () => {
    setKeadaan("loading");
    const jalur = `/proposals/${proposalId}/comments`;
    try {
      const data = await api.get<CommentListOut>(jalur);
      if (!Array.isArray(data?.items)) {
        throw new ApiError(
          "bentuk_respons_tidak_terduga",
          "Terjadi kesalahan. Coba lagi sebentar lagi.",
          0,
        );
      }
      setItems(data.items);
      setVoteCount(data.vote_count ?? null);
      setVotedByMe(data.voted_by_me ?? false);
      setKeadaan("loaded");
    } catch (error) {
      setPesanGalat(
        error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.",
      );
      setKeadaan("error");
    }
  }, [proposalId]);

  useEffect(() => {
    muat();
  }, [muat]);

  async function toggleVote() {
    setVoteError(null);
    try {
      const hasil = await api.post<VoteOut>(`/proposals/${proposalId}/vote`);
      setVotedByMe(hasil.voted);
      setVoteCount(hasil.vote_count);
    } catch (error) {
      // Pesan server diteruskan apa adanya untuk galat yang memang menjelaskan
      // sesuatu kepada pengguna (misalnya proposal belum terbuka untuk
      // dukungan publik), TAPI tidak untuk 401 dan 403. Keduanya membalas
      // kalimat internal seperti "Token tidak ada.", dan kalimat itu sempat
      // tampil mentah di halaman proposal untuk pengunjung tanpa akun. Pola
      // penanganan yang sama sudah lebih dulu dipasang di jalur pledge
      // (ProposalDetailView.muatPledges) dan tidak pernah ikut ke sini.
      //
      // Sesudah perbaikan ini, keduanya seharusnya tidak tercapai lewat UI:
      // tombolnya hanya dirender untuk akun community. Cabang ini tetap ada
      // untuk token yang kedaluwarsa setelah halaman terbuka.
      if (error instanceof ApiError && error.status === 401) {
        setVoteError("Sesi Anda sudah berakhir. Masuk lagi untuk memberi dukungan.");
      } else if (error instanceof ApiError && error.status === 403) {
        setVoteError("Hanya akun komunitas yang bisa memberi dukungan.");
      } else {
        setVoteError(
          error instanceof ApiError
            ? error.message
            : "Gagal mencatat dukungan. Coba lagi sebentar lagi.",
        );
      }
    }
  }

  async function hapusKomentar(commentId: string) {
    try {
      await api.del(`/comments/${commentId}`);
      setItems((prev) => prev.filter((item) => item.id !== commentId));
    } catch {
      // Kegagalan hapus tidak menghilangkan komentar dari layar: pengguna
      // tetap melihat apa yang sungguh masih ada di server.
    }
  }

  function arahkanKeFormKomentar() {
    const form = document.getElementById("form-komentar");
    form?.scrollIntoView({ behavior: "smooth" });
    form?.querySelector("textarea")?.focus();
  }

  if (keadaan === "loading") return <LoadingState label="Memuat komentar" />;
  if (keadaan === "error") return <ErrorState message={pesanGalat} onRetry={muat} />;

  return (
    <div className="flex flex-col gap-space-4">
      {/* Tombolnya hanya ditawarkan kepada yang memang boleh memakainya.
          Sebelumnya setiap pengunjung melihat "Dukung proposal ini", dan
          menekannya membalas pesan mentah server "Token tidak ada." tepat di
          bawahnya. Menawarkan aksi yang pasti ditolak lalu menjelaskan
          penolakannya dengan kalimat internal adalah dua kesalahan, bukan
          satu. */}
      <div className="flex flex-wrap items-center gap-space-3">
        {currentRole === "community" ? (
          <button
            type="button"
            aria-pressed={votedByMe}
            onClick={toggleVote}
            className="min-h-[44px] rounded-sm border border-line-strong px-space-3 py-space-2 text-body font-semibold text-ink transition-colors hover:bg-panel aria-pressed:bg-ink aria-pressed:text-paper"
          >
            {votedByMe ? "Dukungan Anda tercatat" : "Dukung proposal ini"}
          </button>
        ) : null}
        <span className="tabular text-body text-muted">
          {voteCount === null ? "Jumlah dukungan belum tersedia" : `${voteCount} dukungan`}
        </span>
        {currentRole === null && (
          <Link
            href="/masuk"
            className="inline-flex min-h-[44px] items-center text-body font-medium text-ink underline underline-offset-2"
          >
            Masuk sebagai komunitas untuk ikut mendukung
          </Link>
        )}
      </div>
      {voteError && (
        <p role="alert" className="text-label text-danger">
          {voteError}
        </p>
      )}

      {items.length === 0 ? (
        <div className="flex flex-col items-start gap-space-3">
          <EmptyState reason="Belum ada yang berkomentar di proposal ini." />
          {/* Tombol sekunder, bukan EmptyState.action: action bawaannya memakai
              --accent, dan anggaran aksen halaman ini sudah penuh. */}
          <button
            type="button"
            onClick={arahkanKeFormKomentar}
            className="min-h-[44px] rounded-sm border border-ink px-space-3 py-space-2 text-body font-semibold text-ink"
          >
            Tulis komentar pertama
          </button>
        </div>
      ) : (
        <ul className="flex flex-col gap-space-4">
          {items.map((item) => (
            <li key={item.id} className="max-w-measure border-t border-line pt-space-3 first:border-t-0 first:pt-0">
              {/* CommentOut tidak membawa nama tampilan (backend/app/schemas/
                  community.py), hanya user_id. Pola anonimisasi yang sama
                  dipakai ProposalDetailView untuk investor_id pledge di
                  bagian funding, supaya satu komentar tetap bisa dibedakan
                  dari komentar lain tanpa membocorkan identitas penuh. */}
              <p className="text-label font-medium text-muted">
                Pengguna &hellip;{item.user_id.slice(-4)}
              </p>
              <p className="text-body text-ink">{item.body}</p>
              {item.user_id === currentUserId && (
                <button
                  type="button"
                  onClick={() => hapusKomentar(item.id)}
                  className="mt-space-1 min-h-[44px] text-label font-medium text-muted underline"
                >
                  Hapus komentar
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
