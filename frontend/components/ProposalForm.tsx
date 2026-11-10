"use client";

import { useId, useState } from "react";
import { Field } from "@/components/ui/Field";
import {
  MIN_MILESTONES,
  MilestonePlan,
  totalMilestone,
  type MilestoneDraft,
} from "@/components/MilestonePlan";

// Minimum panjang field sesuai .claude/prd/04-feature-umkm.md. Diekspor
// supaya halaman pemanggil (umkm/proposal/baru) bisa menyusun pesan yang
// sama tanpa mengetik ulang angkanya.
export const MIN_BUSINESS_NAME = 3;
export const MAX_BUSINESS_NAME = 120;
export const MIN_BUSINESS_PROFILE = 100;
export const MIN_FUND_USAGE_PLAN = 100;
export const MIN_BUSINESS_PROJECTION = 50;
// BR-12: requested_amount minimal Rp500.000.
export const MIN_REQUESTED_AMOUNT = 500_000;

export type ProposalSubmission = {
  business_name: string;
  business_profile: string;
  requested_amount: number;
  fund_usage_plan: string;
  business_projection: string;
  milestones: { seq: number; title: string; description: string; amount: number }[];
};

type ProposalFormProps = {
  /** Nilai awal dana yang diminta. Form tetap mengizinkan pengguna
   *  mengubahnya; prop ini hanya titik mula, bukan nilai terkunci. */
  requestedAmount?: number;
  /** target_amount campaign, batas atas requested_amount (BR-11). */
  maxAmount?: number;
  /** Alasan form tidak bisa dikirim sama sekali, misal tenggat pengajuan
   *  campaign sudah lewat (BR-17). Diperiksa dan ditampilkan sebelum
   *  request dikirim, bukan menunggu jawaban server. */
  disabledReason?: string;
  submitting?: boolean;
  onSubmit?: (payload: ProposalSubmission) => void;
};

function kurangKarakter(nilai: string, minimum: number): number {
  return Math.max(0, minimum - nilai.trim().length);
}

export function ProposalForm({
  requestedAmount,
  maxAmount,
  disabledReason,
  submitting = false,
  onSubmit,
}: ProposalFormProps) {
  const [businessName, setBusinessName] = useState("");
  const [businessProfile, setBusinessProfile] = useState("");
  const [requestedAmountInput, setRequestedAmountInput] = useState(
    requestedAmount !== undefined ? String(requestedAmount) : "",
  );
  const [fundUsagePlan, setFundUsagePlan] = useState("");
  const [businessProjection, setBusinessProjection] = useState("");
  const [milestones, setMilestones] = useState<MilestoneDraft[]>(
    Array.from({ length: MIN_MILESTONES }, () => ({ title: "", description: "", amount: "" })),
  );

  const requestedAmountValue = Number(requestedAmountInput) || 0;
  const milestoneTotal = totalMilestone(milestones);
  const milestoneCocok = milestoneTotal === requestedAmountValue;

  const kurangFundUsagePlan = kurangKarakter(fundUsagePlan, MIN_FUND_USAGE_PLAN);
  const kurangBusinessProfile = kurangKarakter(businessProfile, MIN_BUSINESS_PROFILE);
  const kurangBusinessProjection = kurangKarakter(businessProjection, MIN_BUSINESS_PROJECTION);
  const namaUsahaKurangPanjang = businessName.trim().length < MIN_BUSINESS_NAME;
  const namaUsahaTerlaluPanjang = businessName.trim().length > MAX_BUSINESS_NAME;
  const jumlahDimintaTerlaluKecil = requestedAmountValue < MIN_REQUESTED_AMOUNT;
  const jumlahDimintaMelebihiTarget =
    maxAmount !== undefined && requestedAmountValue > maxAmount;

  const formValid =
    !namaUsahaKurangPanjang &&
    !namaUsahaTerlaluPanjang &&
    kurangBusinessProfile === 0 &&
    !jumlahDimintaTerlaluKecil &&
    !jumlahDimintaMelebihiTarget &&
    kurangFundUsagePlan === 0 &&
    kurangBusinessProjection === 0 &&
    milestoneCocok;

  const tidakBisaDikirim = Boolean(disabledReason) || !formValid || submitting;

  // Pesan di bawah muncul begitu pengguna sudah mengisi sesuatu tapi belum
  // cukup, bukan menunggu klik tombol kirim yang sudah nonaktif: validasi
  // ini ada supaya jawabannya terlihat sebelum request dikirim, jadi ia
  // tidak boleh bergantung pada tombol yang justru dinonaktifkan olehnya.
  const errorNamaUsaha =
    businessName.length > 0 && namaUsahaKurangPanjang
      ? `Nama usaha minimal ${MIN_BUSINESS_NAME} karakter.`
      : namaUsahaTerlaluPanjang
        ? `Nama usaha maksimal ${MAX_BUSINESS_NAME} karakter.`
        : undefined;
  const errorProfilUsaha =
    businessProfile.length > 0 && kurangBusinessProfile > 0
      ? `Profil usaha masih kurang ${kurangBusinessProfile} karakter dari minimum ${MIN_BUSINESS_PROFILE}.`
      : undefined;
  const errorJumlahDiminta =
    requestedAmountInput.length > 0 && jumlahDimintaTerlaluKecil
      ? "Dana yang diminta minimal Rp500.000."
      : requestedAmountInput.length > 0 && jumlahDimintaMelebihiTarget
        ? "Dana yang diminta tidak boleh melebihi target campaign."
        : undefined;
  const errorRencanaDana =
    fundUsagePlan.length > 0 && kurangFundUsagePlan > 0
      ? `Rencana penggunaan dana masih kurang ${kurangFundUsagePlan} karakter dari minimum ${MIN_FUND_USAGE_PLAN}.`
      : undefined;
  const errorProyeksi =
    businessProjection.length > 0 && kurangBusinessProjection > 0
      ? `Proyeksi usaha masih kurang ${kurangBusinessProjection} karakter dari minimum ${MIN_BUSINESS_PROJECTION}.`
      : undefined;

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (tidakBisaDikirim) return;
    onSubmit?.({
      business_name: businessName,
      business_profile: businessProfile,
      requested_amount: requestedAmountValue,
      fund_usage_plan: fundUsagePlan,
      business_projection: businessProjection,
      // seq (1-indeks urutan tahap) wajib diisi: backend/app/schemas/
      // proposal.py MilestoneIn tidak punya default untuk field ini. Tanpa
      // ini, POST /campaigns/{id}/proposals selalu gagal 422 "Field
      // required" untuk setiap milestone -- dibuktikan lewat e2e Fase 11
      // Task 12 terhadap backend asli, bukan diasumsikan: tidak ada test
      // unit yang pernah membangun body permintaan sungguhan untuk
      // membuktikan bentuknya benar, hanya memverifikasi onSubmit dipanggil.
      milestones: milestones.map((m, index) => ({
        seq: index + 1,
        title: m.title,
        description: m.description,
        amount: Number(m.amount) || 0,
      })),
    });
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex max-w-none flex-col gap-space-5">
      {disabledReason && (
        <p
          role="alert"
          className="rounded-sm border border-warn bg-panel px-space-3 py-space-2 text-body text-warn"
        >
          {disabledReason}
        </p>
      )}

      <Field
        label="Nama usaha"
        value={businessName}
        onChange={setBusinessName}
        error={errorNamaUsaha}
        required
      />

      <TextAreaField
        label="Profil usaha"
        hint="Jenis usaha, lama berjalan, lokasi, jumlah pekerja."
        value={businessProfile}
        onChange={setBusinessProfile}
        error={errorProfilUsaha}
        required
      />

      <MoneyField
        label="Jumlah dana yang diminta"
        value={requestedAmountInput}
        onChange={(value) => setRequestedAmountInput(value.replace(/[^0-9]/g, ""))}
        error={errorJumlahDiminta}
        required
      />

      <TextAreaField
        label="Rencana penggunaan dana"
        hint="Rincian penggunaan dana per pos."
        value={fundUsagePlan}
        onChange={setFundUsagePlan}
        error={errorRencanaDana}
        required
      />

      <TextAreaField
        label="Proyeksi usaha"
        hint="Proyeksi omzet atau dampak."
        value={businessProjection}
        onChange={setBusinessProjection}
        error={errorProyeksi}
        required
      />

      <div>
        <h2 className="text-card-title font-semibold text-ink">Rencana milestone</h2>
        <p className="mt-space-1 text-label text-muted">
          Jumlah seluruh tahap harus sama persis dengan dana yang diminta.
        </p>
        <div className="mt-space-3">
          <MilestonePlan
            requestedAmount={requestedAmountValue}
            milestones={milestones}
            onChange={setMilestones}
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={tidakBisaDikirim}
        aria-busy={submitting}
        className="min-h-[44px] self-start rounded-sm bg-accent px-space-4 py-space-2 text-body font-semibold text-on-accent disabled:border disabled:border-line disabled:bg-panel disabled:text-muted"
      >
        Kirim proposal
      </button>
    </form>
  );
}

type MoneyFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  required?: boolean;
};

// Field (fase 10) tidak boleh diubah di sini (lihat catatan TextAreaField di
// bawah), dan type="number" bawaannya tidak cocok untuk rupiah: ia
// mengizinkan "e", "+", "-", "." lalu membulatkan diam-diam, sementara filter
// digit yang dipakai di formulir ini butuh <input> bertipe teks sungguhan.
// inputMode="numeric" tetap memunculkan keypad angka di ponsel tanpa
// kehilangan filter itu (laporan review: field ini dan nominal milestone
// dulu tidak punya inputMode sama sekali, jadi ponsel menampilkan keyboard
// huruf untuk nominal rupiah, padahal CampaignForm sudah type="number" untuk
// nominal sejenis).
function MoneyField({ label, value, onChange, error, required }: MoneyFieldProps) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className="flex flex-col gap-space-1">
      <label htmlFor={id} className="text-label font-medium text-muted">
        {label}
        {required && <span aria-hidden="true"> *</span>}
      </label>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        className="control"
      />
      {error && (
        <p id={errorId} role="alert" className="text-label text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

type TextAreaFieldProps = {
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  required?: boolean;
};

// Field (fase 10) hanya merender <input>, tidak <textarea>, dan field ini
// bukan bagian dari file-file yang boleh disentuh stream ini. TextAreaField
// mengulang kontrak aksesibilitas yang sama (htmlFor, aria-describedby,
// aria-invalid) khusus untuk area teks panjang di formulir proposal.
function TextAreaField({ label, hint, value, onChange, error, required }: TextAreaFieldProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className="flex flex-col gap-space-1">
      <label htmlFor={id} className="text-label font-medium text-muted">
        {label}
        {required && <span aria-hidden="true"> *</span>}
      </label>
      {hint && (
        <p id={hintId} className="text-label text-muted">
          {hint}
        </p>
      )}
      <textarea
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        rows={4}
        className="control"
      />
      {error && (
        <p id={errorId} role="alert" className="text-label text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
