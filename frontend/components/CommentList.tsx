"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui";
import type { ApiComment } from "@/components/CommentForm";
import { ApiError, api } from "@/lib/api";

type CommentsEnvelope = {
  items: ApiComment[];
  vote_count: number;
  voted_by_me: boolean;
};

type VoteOut = {
  voted: boolean;
  vote_count: number;
};

type CommentListProps = {
  proposalId: string;
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
export function CommentList({ proposalId }: CommentListProps) {
  const [keadaan, setKeadaan] = useState<Keadaan>("loading");
  const [pesanGalat, setPesanGalat] = useState("");
  const [items, setItems] = useState<ApiComment[]>([]);
  const [voteCount, setVoteCount] = useState(0);
  const [votedByMe, setVotedByMe] = useState(false);
  const [voteError, setVoteError] = useState<string | null>(null);

  const muat = useCallback(async () => {
    setKeadaan("loading");
    try {
      const data = await api.get<CommentsEnvelope>(`/proposals/${proposalId}/comments`);
      setItems(data.items);
      setVoteCount(data.vote_count);
      setVotedByMe(data.voted_by_me);
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
          className="min-h-[44px] rounded-sm border border-ink px-space-3 py-space-2 text-base leading-[1.6] font-semibold text-ink aria-pressed:bg-ink aria-pressed:text-paper"
        >
          Dukung proposal ini
        </button>
        <span className="tabular text-base leading-[1.6] text-muted">{voteCount} dukungan</span>
      </div>
      {voteError && (
        <p role="alert" className="text-[0.8125rem] text-danger">
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
            className="min-h-[44px] rounded-sm border border-ink px-space-3 py-space-2 text-base leading-[1.6] font-semibold text-ink"
          >
            Tulis komentar pertama
          </button>
        </div>
      ) : (
        <ul className="flex flex-col gap-space-4">
          {items.map((item) => (
            <li key={item.id} className="max-w-measure border-t border-line pt-space-3 first:border-t-0 first:pt-0">
              <p className="text-[0.8125rem] font-medium text-muted">{item.author_name}</p>
              <p className="text-base leading-[1.6] text-ink">{item.body}</p>
              {item.is_mine && (
                <button
                  type="button"
                  onClick={() => hapusKomentar(item.id)}
                  className="mt-space-1 min-h-[44px] text-[0.8125rem] font-medium text-muted underline"
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
