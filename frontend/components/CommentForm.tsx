"use client";

import { useId, useState } from "react";
import { ApiError, api } from "@/lib/api";

const BATAS_PANJANG = 500;

export type ApiComment = {
  id: string;
  author_name: string;
  body: string;
  created_at: string;
  is_mine: boolean;
};

type CommentFormProps = {
  proposalId: string;
  /** Dipanggil setiap komentar baru berhasil terkirim, supaya daftar di
   * sebelahnya bisa menambahkannya tanpa menunggu refetch penuh. */
  onKirim?: (comment: ApiComment) => void;
};

// Form komentar komunitas (05-feature-komunitas.md): maksimal 500 karakter,
// tanpa format kaya, tanpa lampiran. Validasi kosong ditangani di klien
// supaya pengguna tidak menunggu roundtrip server untuk kesalahan yang sudah
// jelas dari sisi klien, tapi batas panjang tetap ditegakkan ulang oleh
// server sebagai sumber kebenaran.
export function CommentForm({ proposalId, onKirim }: CommentFormProps) {
  const id = useId();
  const [body, setBody] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = body.trim();
    if (trimmed === "") {
      setFormError("Komentar tidak boleh kosong.");
      return;
    }
    if (trimmed.length > BATAS_PANJANG) {
      setFormError(`Komentar maksimal ${BATAS_PANJANG} karakter.`);
      return;
    }

    setFormError(null);
    setSubmitting(true);
    try {
      const comment = await api.post<ApiComment>(`/proposals/${proposalId}/comments`, {
        body: trimmed,
      });
      setBody("");
      onKirim?.(comment);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="flex max-w-measure flex-col gap-space-2">
      <label htmlFor={id} className="text-[0.8125rem] font-medium text-muted">
        Komentar
      </label>
      <textarea
        id={id}
        value={body}
        onChange={(event) => setBody(event.target.value)}
        maxLength={BATAS_PANJANG}
        rows={3}
        aria-invalid={formError ? true : undefined}
        className="min-h-[88px] rounded-sm border border-ink bg-paper px-space-3 py-space-2 text-base leading-[1.6] text-ink"
      />
      {formError && (
        <p role="alert" className="text-[0.8125rem] text-danger">
          {formError}
        </p>
      )}
      <button
        type="submit"
        disabled={submitting}
        aria-busy={submitting}
        className="min-h-[44px] self-start rounded-sm border border-ink px-space-4 py-space-2 text-base leading-[1.6] font-semibold text-ink"
      >
        Kirim
      </button>
    </form>
  );
}
