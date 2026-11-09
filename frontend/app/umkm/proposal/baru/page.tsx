"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { EmptyState, ErrorState, Field, LoadingState } from "@/components/ui";
import { ProposalForm, type ProposalSubmission } from "@/components/ProposalForm";
import { ApiError, api } from "@/lib/api";

type Campaign = {
  id: string;
  title: string;
  target_amount: number;
  apply_deadline: string;
};

type Muatan =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "siap"; campaigns: Campaign[] };

// Satu keputusan di layar ini: apakah pengajuan saya sudah cukup untuk
// dinilai (DESIGN.md). Validasi tenggat dan panjang minimum field berjalan
// di klien dulu, supaya jawabannya tidak perlu menunggu bolak-balik server.
export default function ProposalBaru() {
  const router = useRouter();
  const [muatan, setMuatan] = useState<Muatan>({ status: "loading" });
  const [campaignId, setCampaignId] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const muat = useCallback(async () => {
    setMuatan({ status: "loading" });
    try {
      const campaigns = await api.get<Campaign[]>("/campaigns");
      setMuatan({ status: "siap", campaigns });
      const pertama = campaigns[0];
      if (pertama) setCampaignId((current) => current || pertama.id);
    } catch (error) {
      setMuatan({
        status: "error",
        message: error instanceof ApiError ? error.message : "Gagal memuat daftar campaign.",
      });
    }
  }, []);

  useEffect(() => {
    muat();
  }, [muat]);

  if (muatan.status === "loading") {
    return <LoadingState label="Memuat daftar campaign" minHeight={240} />;
  }
  if (muatan.status === "error") {
    return <ErrorState message={muatan.message} onRetry={muat} />;
  }

  const campaign =
    muatan.campaigns.find((c) => c.id === campaignId) ?? muatan.campaigns[0];

  if (!campaign) {
    return (
      <EmptyState reason="Belum ada campaign yang terbuka untuk menerima proposal saat ini." />
    );
  }

  const tenggatLewat = new Date(campaign.apply_deadline).getTime() < Date.now();
  const disabledReason = tenggatLewat
    ? `Tenggat pengajuan proposal untuk campaign ini sudah lewat (${new Date(campaign.apply_deadline).toLocaleDateString("id-ID")}). Pilih campaign lain atau tunggu campaign berikutnya.`
    : undefined;

  const activeCampaignId = campaign.id;

  async function handleSubmit(payload: ProposalSubmission) {
    setSubmitError(null);
    setSubmitting(true);
    try {
      await api.post(`/campaigns/${activeCampaignId}/proposals`, payload);
      router.push("/umkm/beranda");
    } catch (error) {
      setSubmitError(
        error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.",
      );
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex flex-col gap-space-5 px-space-3 py-space-6">
      <div className="max-w-measure">
        <h1 className="text-[clamp(2.5rem,5vw,4rem)] font-semibold text-ink">Ajukan proposal</h1>
        <p className="mt-space-2 text-base leading-[1.6] text-muted">
          Isi selengkap dan sespesifik mungkin. AI menilai berdasarkan isian field-field ini.
        </p>
      </div>

      {muatan.campaigns.length > 1 && (
        <Field
          label="Campaign"
          value={campaignId}
          onChange={setCampaignId}
          options={muatan.campaigns.map((c) => ({ value: c.id, label: c.title }))}
        />
      )}

      {submitError && (
        <p
          role="alert"
          className="rounded-sm border border-danger bg-surface px-space-3 py-space-2 text-base leading-[1.6] text-danger"
        >
          {submitError}
        </p>
      )}

      <ProposalForm
        key={campaign.id}
        maxAmount={campaign.target_amount}
        disabledReason={disabledReason}
        submitting={submitting}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
