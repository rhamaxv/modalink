"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { EmptyState, ErrorState, Field, LoadingState } from "@/components/ui";
import { ProposalForm, type ProposalSubmission } from "@/components/ProposalForm";
import { ApiError, api, daftarDariRespons } from "@/lib/api";

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
      // GET /campaigns membungkus daftarnya dalam { items: [...] }
      // (backend/app/schemas/campaign.py: CampaignListOut), bukan array
      // mentah. Sebelumnya field ini dibaca seolah array langsung, yang di
      // browser sungguhan melempar TypeError saat .find dipanggil pada objek
      // di bawah (lihat laporan Fase 11 Task 12: ditemukan lewat e2e
      // terhadap backend asli, bukan test unit yang pernah memock bentuk
      // ini). daftarDariRespons melempar ApiError yang jelas kalau bentuknya
      // pernah menyimpang lagi, bukan membiarkan .find di bawah ini gagal
      // diam-diam beberapa baris kemudian.
      const campaigns = daftarDariRespons<Campaign>(await api.get("/campaigns"), "/campaigns");
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

  async function handleSubmit(
    activeCampaignId: string,
    payload: ProposalSubmission,
    dokumen: File,
  ) {
    setSubmitError(null);
    setSubmitting(true);
    try {
      await api.kirimProposal(`/campaigns/${activeCampaignId}/proposals`, payload, dokumen);
      router.push("/umkm/beranda");
    } catch (error) {
      setSubmitError(
        error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.",
      );
      setSubmitting(false);
    }
  }

  // H1 dirender sebelum cabang status data mana pun, dan loading/error/kosong
  // dirender DI DALAM pembungkus lebar yang sama dengan form sungguhan: versi
  // sebelumnya mengembalikan ketiga keadaan itu sebelum pembungkus dan
  // sebelum H1, jadi kotaknya rapat ke tepi layar di 375px dan judul halaman
  // baru muncul (memindahkan seluruh layout) begitu campaign datang.
  const campaign =
    muatan.status === "siap"
      ? muatan.campaigns.find((c) => c.id === campaignId) ?? muatan.campaigns[0]
      : undefined;
  const tenggatLewat = campaign ? new Date(campaign.apply_deadline).getTime() < Date.now() : false;
  const disabledReason = tenggatLewat
    ? `Tenggat pengajuan proposal untuk campaign ini sudah lewat (${new Date(campaign!.apply_deadline).toLocaleDateString("id-ID")}). Pilih campaign lain atau tunggu campaign berikutnya.`
    : undefined;

  return (
    <div className="mx-auto flex max-w-[72rem] flex-col gap-space-5 px-space-3 py-space-6">
      <div className="max-w-measure">
        <h1 className="font-display text-page text-ink">Ajukan proposal</h1>
        <p className="mt-space-3 text-body text-muted">
          Unggah dokumen proposal Anda sebagai PDF. AI membaca dokumen itu untuk menilai,
          dan investor membacanya sebelum memutuskan ikut mendanai.
        </p>
      </div>

      {muatan.status === "loading" && <LoadingState label="Memuat daftar campaign" minHeight={240} />}
      {muatan.status === "error" && <ErrorState message={muatan.message} onRetry={muat} />}

      {muatan.status === "siap" && !campaign && (
        <EmptyState reason="Belum ada campaign yang terbuka untuk menerima proposal saat ini." />
      )}

      {muatan.status === "siap" && campaign && (
        <>
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
              className="rounded-sm border border-danger bg-panel px-space-3 py-space-2 text-body text-danger"
            >
              {submitError}
            </p>
          )}

          <ProposalForm
            key={campaign.id}
            maxAmount={campaign.target_amount}
            disabledReason={disabledReason}
            submitting={submitting}
            onSubmit={(payload, dokumen) => handleSubmit(campaign.id, payload, dokumen)}
          />
        </>
      )}
    </div>
  );
}
