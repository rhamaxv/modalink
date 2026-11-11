"use client";

import { useState } from "react";
import { Field } from "@/components/ui/Field";
import { ApiError, api } from "@/lib/api";
import { formatRupiah } from "@/lib/money";

type PledgeOut = {
  id: string;
  proposal_id: string;
  investor_id: string;
  amount: number;
  status: string;
  created_at: string;
};

type PledgeFormProps = {
  /** Opsional di test terisolasi; diisi sungguhan oleh halaman detail proposal. */
  proposalId?: string;
  /** Sisa dana yang masih dibutuhkan, dihitung dari bilah funding di atasnya. */
  sisa: number;
  onSukses?: (pledge: PledgeOut) => void;
};

// Form pledge: satu-satunya tombol aksi utama di halaman ini, jadi memakai
// --accent (DESIGN.md). Validasi klien ("melebihi sisa") hanya mencegah
// kesalahan yang sudah jelas sebelum kirim; ia tidak bisa mencegah balapan
// antar investor (RF-1), jadi 409 dari server tetap ditampilkan apa adanya
// dan sisa dana diperbarui dari detail.remaining_amount yang dikirim backend,
// bukan dihitung ulang sendiri di klien (sumber kebenarannya tetap server).
export function PledgeForm({ proposalId = "", sisa, onSukses }: PledgeFormProps) {
  const [nominal, setNominal] = useState("");
  const [sisaSekarang, setSisaSekarang] = useState(sisa);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const nilaiAngka = Number(nominal);
  const nominalValid = nominal.trim() !== "" && Number.isFinite(nilaiAngka) && nilaiAngka > 0;
  const melebihiSisa = nominalValid && nilaiAngka > sisaSekarang;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    if (!nominalValid || melebihiSisa) return;

    setSubmitting(true);
    try {
      const pledge = await api.post<PledgeOut>(`/proposals/${proposalId}/pledges`, {
        amount: nilaiAngka,
      });
      setNominal("");
      onSukses?.(pledge);
    } catch (error) {
      if (error instanceof ApiError) {
        setFormError(error.message);
        const sisaBaru = error.detail.remaining_amount;
        if (typeof sisaBaru === "number") setSisaSekarang(sisaBaru);
      } else {
        setFormError("Terjadi kesalahan. Coba lagi sebentar lagi.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-space-3">
      <p className="tabular text-label font-medium text-muted">
        Maksimal {formatRupiah(sisaSekarang)} lagi bisa didanai.
      </p>

      {formError && (
        <p role="alert" className="rounded-sm border border-danger bg-panel px-space-3 py-space-2 text-body text-danger">
          {formError}
        </p>
      )}

      <Field label="Nominal pledge (Rp)" value={nominal} onChange={setNominal} required />

      {melebihiSisa && (
        // Menyebut ANGKA sisanya, bukan hanya menyatakan nominalnya terlalu
        // besar. Tombolnya dinonaktifkan di bawah, jadi tanpa angka ini
        // investor menghadapi tombol mati dan harus menebak berapa yang
        // sebenarnya boleh dimasukkan. Kontrak backend sendiri mengirim
        // remaining_amount di detail 409 justru untuk tujuan ini
        // (10-api-contract.md baris POST pledges), dan nilai itulah yang
        // dipegang sisaSekarang setelah balapan antar investor.
        <p role="status" className="text-label font-medium text-warn">
          Sisa dana yang dibutuhkan tinggal {formatRupiah(sisaSekarang)}.
        </p>
      )}

      <button
        type="submit"
        disabled={submitting || !nominalValid || melebihiSisa}
        aria-busy={submitting}
        className="min-h-[44px] rounded-sm bg-accent px-space-4 py-space-2 text-body font-semibold text-on-accent disabled:border disabled:border-line disabled:bg-panel disabled:text-muted"
      >
        Danai
      </button>
    </form>
  );
}
