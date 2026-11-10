"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Amount } from "@/components/ui/Amount";
import { ApiError, api, daftarDariRespons } from "@/lib/api";

// Panjang minimum narasi laporan sesuai .claude/prd/04-feature-umkm.md.
const MIN_NARRATIVE = 50;

type MilestoneReport = {
  id: string;
  narrative: string;
  status: "pending_review" | "rejected" | "approved";
  rejection_note?: string | null;
};

type Milestone = {
  id: string;
  seq: number;
  title: string;
  amount: number;
  status: "pending" | "reported" | "approved" | "disbursed";
  last_report?: MilestoneReport | null;
};

type Muatan =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "siap"; milestones: Milestone[] };

// GET /proposals/{id}/milestones (.claude/prd/10-api-contract.md) hanya
// menerima id PROPOSAL, sedangkan rute ini dikunci oleh id MILESTONE. Tidak
// ada endpoint GET satu milestone lewat idnya sendiri di kontrak API, jadi
// halaman ini mengandalkan query string ?proposal= untuk tahu proposal mana
// yang harus diambil, lalu mencari milestone yang cocok di daftarnya.
export default function MilestoneLapor() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const milestoneId = params.id;
  const proposalId = searchParams.get("proposal") ?? "";

  const [muatan, setMuatan] = useState<Muatan>({ status: "loading" });
  const [narrative, setNarrative] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const muat = useCallback(async () => {
    if (!proposalId) {
      setMuatan({ status: "error", message: "Proposal untuk milestone ini tidak diketahui." });
      return;
    }
    setMuatan({ status: "loading" });
    try {
      // GET /proposals/{id}/milestones membungkus daftarnya dalam
      // { items: [...] } (backend/app/schemas/proposal.py: MilestoneListOut),
      // bukan array mentah. Sebelumnya field ini dibaca seolah array
      // langsung, yang di browser sungguhan melempar TypeError saat .find
      // dipanggil pada objek di bawah (lihat laporan Fase 11 Task 12:
      // ditemukan lewat e2e terhadap backend asli). daftarDariRespons
      // melempar ApiError yang jelas kalau bentuknya menyimpang lagi.
      const milestones = daftarDariRespons<Milestone>(
        await api.get(`/proposals/${proposalId}/milestones`),
        `/proposals/${proposalId}/milestones`,
      );
      setMuatan({ status: "siap", milestones });
    } catch (error) {
      setMuatan({
        status: "error",
        message: error instanceof ApiError ? error.message : "Gagal memuat milestone.",
      });
    }
  }, [proposalId]);

  useEffect(() => {
    muat();
  }, [muat]);

  if (muatan.status === "loading") {
    return <LoadingState label="Memuat milestone" minHeight={200} />;
  }
  if (muatan.status === "error") {
    return <ErrorState message={muatan.message} onRetry={muat} />;
  }

  const milestone = muatan.milestones.find((m) => m.id === milestoneId);
  if (!milestone) {
    return <EmptyState reason="Milestone ini tidak ditemukan atau bukan milik proposal yang ditentukan." />;
  }

  const sebelumnya = muatan.milestones.find((m) => m.seq === milestone.seq - 1);
  const prasyaratTerpenuhi = milestone.seq === 1 || sebelumnya?.status === "disbursed";
  const activeMilestoneId = milestone.id;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (narrative.trim().length < MIN_NARRATIVE) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await api.post(`/milestones/${activeMilestoneId}/reports`, { narrative });
      setNarrative("");
      await muat();
    } catch (error) {
      setSubmitError(
        error instanceof ApiError ? error.message : "Gagal mengirim laporan. Coba lagi sebentar lagi.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const kurangNarasi = Math.max(0, MIN_NARRATIVE - narrative.trim().length);

  return (
    <div className="mx-auto flex max-w-measure flex-col gap-space-5 px-space-3 py-space-6">
      <div>
        <h1 className="text-[clamp(2.5rem,5vw,4rem)] font-semibold text-ink">{milestone.title}</h1>
        <div className="mt-space-3 flex flex-wrap items-center gap-space-3">
          <StatusBadge status={milestone.status} />
          <Amount label="Nominal tahap ini" amount={milestone.amount} size="medium" />
        </div>
      </div>

      {milestone.seq === 1 && (
        // D-13: tahap pertama cair tanpa laporan, tapi tetap butuh approve
        // lead investor. Halaman ini tidak boleh menyiratkan pencairan
        // otomatis, jadi kalimatnya menyebut persetujuan secara eksplisit.
        <p className="rounded-card border border-line bg-panel px-space-4 py-space-4 text-body text-ink">
          Tahap pertama tidak memerlukan laporan progres. Tahap ini menunggu persetujuan lead
          investor sebelum dana cair, bukan cair secara otomatis.
        </p>
      )}

      {milestone.seq > 1 && !prasyaratTerpenuhi && (
        <p
          role="alert"
          className="rounded-card border border-warn bg-panel px-space-4 py-space-4 text-body text-ink"
        >
          Tahap {milestone.seq - 1} belum cair. Laporan untuk tahap ini baru bisa dikirim setelah
          tahap {milestone.seq - 1} disetujui lead investor dan dananya cair.
        </p>
      )}

      {milestone.seq > 1 && prasyaratTerpenuhi && milestone.status === "reported" && (
        <div className="rounded-card border border-warn bg-panel px-space-4 py-space-4">
          <StatusBadge status="reported" />
          <p className="mt-space-2 text-body text-ink">
            Laporan sudah dikirim dan sedang menunggu review lead investor. Laporan baru hanya
            bisa dikirim lagi setelah laporan ini disetujui atau ditolak.
          </p>
        </div>
      )}

      {milestone.last_report?.status === "rejected" && milestone.last_report.rejection_note && (
        <p className="rounded-card border border-danger bg-panel px-space-4 py-space-4 text-body text-ink">
          Laporan sebelumnya ditolak dengan catatan: &quot;{milestone.last_report.rejection_note}&quot;
        </p>
      )}

      {milestone.seq > 1 && prasyaratTerpenuhi && milestone.status !== "reported" && (
        <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-space-3">
          <NarrativeField
            value={narrative}
            onChange={setNarrative}
            error={narrative.length > 0 && kurangNarasi > 0 ? `Laporan progres masih kurang ${kurangNarasi} karakter dari minimum ${MIN_NARRATIVE}.` : undefined}
          />
          {submitError && (
            <p role="alert" className="text-label text-danger">
              {submitError}
            </p>
          )}
          <button
            type="submit"
            disabled={submitting || narrative.trim().length < MIN_NARRATIVE}
            aria-busy={submitting}
            className="min-h-[44px] self-start rounded-sm bg-accent px-space-4 py-space-2 text-body font-semibold text-on-accent disabled:border disabled:border-line disabled:bg-panel disabled:text-muted"
          >
            Kirim laporan
          </button>
        </form>
      )}
    </div>
  );
}

type NarrativeFieldProps = {
  value: string;
  onChange: (value: string) => void;
  error?: string;
};

function NarrativeField({ value, onChange, error }: NarrativeFieldProps) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className="flex flex-col gap-space-1">
      <label htmlFor={id} className="text-label font-medium text-muted">
        Laporan progres <span aria-hidden="true">*</span>
      </label>
      <textarea
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        rows={5}
        className="min-h-[112px] rounded-sm border border-ink bg-paper px-space-3 py-space-2 text-body text-ink"
      />
      {error && (
        <p id={errorId} role="alert" className="text-label text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
