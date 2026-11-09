"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Field } from "@/components/ui/Field";
import { ApiError, api } from "@/lib/api";
import { formatRupiah } from "@/lib/money";

// Enam sektor tetap dari backend/app/models/campaign.py (Sector StrEnum).
// Labelnya sudah kata Indonesia yang lazim dipakai, jadi tidak diterjemahkan lagi.
export const SECTOR_OPTIONS = [
  { value: "kuliner", label: "Kuliner" },
  { value: "kerajinan", label: "Kerajinan" },
  { value: "pertanian", label: "Pertanian" },
  { value: "jasa", label: "Jasa" },
  { value: "ritel", label: "Ritel" },
  { value: "teknologi", label: "Teknologi" },
];

// 03-feature-investor.md: dana target minimal Rp1.000.000.
const MINIMAL_TARGET_AMOUNT = 1_000_000;

export type CampaignOut = {
  id: string;
  investor_id: string;
  title: string;
  description: string;
  sector: string;
  target_amount: number;
  apply_deadline: string;
  funding_deadline: string;
  score_threshold: number;
  status: string;
  created_at: string;
};

type CampaignFormProps = {
  mode: "create" | "edit";
  /** Wajib saat mode "edit": campaign mana yang di-PATCH. */
  campaignId?: string;
  initialValues?: {
    title?: string;
    description?: string;
    sector?: string;
    targetAmount?: string;
    applyDeadline?: string;
    fundingDeadline?: string;
    scoreThreshold?: string;
  };
  submitLabel?: string;
  /** Dipanggil setelah PATCH berhasil di mode "edit", supaya pemanggil bisa menutup form. */
  onSaved?: (campaign: CampaignOut) => void;
};

// Tenggat dibaca sampai akhir hari yang dipilih, bukan jam 00:00, supaya
// pengguna yang memilih "hari ini" tidak langsung dianggap sudah lewat tenggat.
function toIsoDeadline(date: string): string {
  return new Date(`${date}T23:59:59`).toISOString();
}

function startOfTomorrow(): Date {
  const date = new Date();
  date.setHours(0, 0, 0, 0);
  date.setDate(date.getDate() + 1);
  return date;
}

// Form campaign: dipakai di /investor/campaign/baru (mode "create", seluruh
// field) dan di CampaignManagePanel (mode "edit", hanya title, description,
// score_threshold karena PATCH /campaigns/{id} cuma menerima tiga itu,
// 10-api-contract.md). Validasi di sini berjalan sebelum request dikirim,
// supaya kesalahan yang sudah bisa diketahui di klien tidak menunggu
// bolak-balik ke server.
export function CampaignForm({ mode, campaignId, initialValues, submitLabel, onSaved }: CampaignFormProps) {
  const router = useRouter();
  const [title, setTitle] = useState(initialValues?.title ?? "");
  const [description, setDescription] = useState(initialValues?.description ?? "");
  const [sector, setSector] = useState(initialValues?.sector ?? SECTOR_OPTIONS[0]!.value);
  const [targetAmount, setTargetAmount] = useState(initialValues?.targetAmount ?? "");
  const [applyDeadline, setApplyDeadline] = useState(initialValues?.applyDeadline ?? "");
  const [fundingDeadline, setFundingDeadline] = useState(initialValues?.fundingDeadline ?? "");
  const [scoreThreshold, setScoreThreshold] = useState(initialValues?.scoreThreshold ?? "60");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (title.trim().length < 5 || title.trim().length > 120) {
      next.title = "Judul campaign 5 sampai 120 karakter.";
    }
    if (description.trim().length < 50) {
      next.description = "Deskripsi minimal 50 karakter.";
    }
    const thresholdValue = Number(scoreThreshold);
    if (!Number.isInteger(thresholdValue) || thresholdValue < 0 || thresholdValue > 100) {
      next.scoreThreshold = "Ambang skor harus bilangan bulat 0 sampai 100.";
    }
    if (mode === "create") {
      const targetValue = Number(targetAmount);
      if (!Number.isInteger(targetValue) || targetValue < MINIMAL_TARGET_AMOUNT) {
        next.targetAmount = `Dana target minimal ${formatRupiah(MINIMAL_TARGET_AMOUNT)}.`;
      }
      if (!applyDeadline) {
        next.applyDeadline = "Tenggat pengajuan wajib diisi.";
      } else if (new Date(applyDeadline) < startOfTomorrow()) {
        next.applyDeadline = "Tenggat pengajuan minimal 1 hari ke depan.";
      }
      if (!fundingDeadline) {
        next.fundingDeadline = "Tenggat funding wajib diisi.";
      } else if (applyDeadline && new Date(fundingDeadline) <= new Date(applyDeadline)) {
        next.fundingDeadline = "Tenggat funding harus setelah tenggat pengajuan.";
      }
    }
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    if (!validate()) return;

    setSubmitting(true);
    try {
      if (mode === "create") {
        const created = await api.post<CampaignOut>("/campaigns", {
          title: title.trim(),
          description: description.trim(),
          sector,
          target_amount: Number(targetAmount),
          apply_deadline: toIsoDeadline(applyDeadline),
          funding_deadline: toIsoDeadline(fundingDeadline),
          score_threshold: Number(scoreThreshold),
        });
        router.push(`/investor/campaign/${created.id}`);
      } else {
        const updated = await api.patch<CampaignOut>(`/campaigns/${campaignId}`, {
          title: title.trim(),
          description: description.trim(),
          score_threshold: Number(scoreThreshold),
        });
        onSaved?.(updated);
      }
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-space-4">
      {formError && (
        <p
          role="alert"
          className="rounded-sm border border-danger bg-surface px-space-3 py-space-2 text-base leading-[1.6] text-danger"
        >
          {formError}
        </p>
      )}
      <Field label="Judul campaign" value={title} onChange={setTitle} error={fieldErrors.title} required />
      <Field
        label="Deskripsi"
        value={description}
        onChange={setDescription}
        error={fieldErrors.description}
        required
        multiline
      />
      {mode === "create" && (
        <>
          <Field label="Sektor" value={sector} onChange={setSector} options={SECTOR_OPTIONS} required />
          <Field
            label="Dana target (Rp)"
            type="number"
            value={targetAmount}
            onChange={setTargetAmount}
            error={fieldErrors.targetAmount}
            required
          />
          <Field
            label="Tenggat pengajuan proposal"
            type="date"
            value={applyDeadline}
            onChange={setApplyDeadline}
            error={fieldErrors.applyDeadline}
            min={startOfTomorrow().toISOString().slice(0, 10)}
            required
          />
          <Field
            label="Tenggat funding"
            type="date"
            value={fundingDeadline}
            onChange={setFundingDeadline}
            error={fieldErrors.fundingDeadline}
            min={applyDeadline || startOfTomorrow().toISOString().slice(0, 10)}
            required
          />
        </>
      )}
      <Field
        label="Ambang skor minimum (0-100)"
        type="number"
        value={scoreThreshold}
        onChange={setScoreThreshold}
        error={fieldErrors.scoreThreshold}
        required
      />
      <button
        type="submit"
        disabled={submitting}
        aria-busy={submitting}
        className="min-h-[44px] self-start rounded-sm bg-accent px-space-4 py-space-2 text-base font-semibold text-on-accent disabled:border disabled:border-line disabled:bg-surface disabled:text-muted"
      >
        {submitLabel ?? (mode === "create" ? "Buat campaign" : "Simpan perubahan")}
      </button>
    </form>
  );
}
