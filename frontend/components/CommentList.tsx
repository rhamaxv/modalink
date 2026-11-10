"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui";
import type { ApiComment } from "@/components/CommentForm";
import { ApiError, api, daftarDariRespons } from "@/lib/api";

type VoteOut = {
  voted: boolean;
  vote_count: number;
};

type CommentListProps = {
  proposalId: string;
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
export function CommentList({ proposalId, currentUserId = null }: CommentListProps) {
  const [keadaan, setKeadaan] = useState<Keadaan>("loading");
  const [pesanGalat, setPesanGalat] = useState("");
  const [items, setItems] = useState<ApiComment[]>([]);
  // null, bukan 0: GET .../comments (backend/app/schemas/community.py:
  // CommentListOut) tidak mengirim vote_count maupun voted_by_me sama sekali
  // -- keduanya dulu dibaca dari respons ini dan selalu undefined terhadap
  // backend asli, yang membuat tombol vote kehilangan aria-pressed sama
  // sekali (React menghilangkan atribut untuk nilai undefined) dan jumlah
  // dukungan tampil sebagai "undefined dukungan" (laporan Fase 11 Task 12).
  // null di sini berarti "belum diketahui", beda dari 0 ("diketahui kosong"),
  // supaya layar tidak berbohong dengan angka yang kita tidak punya sumbernya.
  // Satu-satunya cara jujur mendapatkan nilai sungguhan hari ini adalah dari
  // respons POST /vote sendiri, sesudah pengguna menekannya.
  const [voteCount, setVoteCount] = useState<number | null>(null);
  const [votedByMe, setVotedByMe] = useState(false);
  const [voteError, setVoteError] = useState<string | null>(null);

  const muat = useCallback(async () => {
    setKeadaan("loading");
    const jalur = `/proposals/${proposalId}/comments`;
    try {
      const data = daftarDariRespons<ApiComment>(await api.get(jalur), jalur);
      setItems(data);
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
      setVoteError(error instanceof ApiError ? error.message : "Gagal mencatat vote. Coba lagi sebentar lagi.");
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
      <div className="flex flex-wrap items-center gap-space-3">
        <button
          type="button"
          aria-pressed={votedByMe}
          onClick={toggleVote}
          className="min-h-[44px] rounded-sm border border-ink px-space-3 py-space-2 text-body font-semibold text-ink aria-pressed:bg-ink aria-pressed:text-paper"
        >
          Dukung proposal ini
        </button>
        <span className="tabular text-body text-muted">
          {voteCount === null ? "Jumlah dukungan belum tersedia" : `${voteCount} dukungan`}
        </span>
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
