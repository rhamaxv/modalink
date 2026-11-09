"use client";

import { useState } from "react";
import Link from "next/link";
import { Amount, EmptyState, Field } from "@/components/ui";
import { StatusBadge } from "@/components/ui/StatusBadge";

const CATATAN_MINIMAL = 10;

export type MilestoneReport = {
  review_status: "pending" | "approved" | "rejected";
  narrative: string;
  reviewer_note?: string | null;
};

export type Milestone = {
  id?: string;
  seq: number;
  title: string;
  description?: string;
  amount: number;
  status: "pending" | "reported" | "disbursed";
  /** Seluruh riwayat laporan tahap ini, terbaru maupun yang sudah direvisi
   * (BR-46): laporan tidak pernah ditimpa, jadi riwayatnya wajib tetap
   * terlihat, bukan hanya laporan terakhir. */
  reports?: MilestoneReport[];
};

export type MilestoneTimelineProps = {
  milestones: Milestone[];
  /** Hanya lead investor yang melihat tombol approve/reject (BR-44). */
  isLeadInvestor?: boolean;
  onApprove?: (milestoneId: string) => void;
  onReject?: (milestoneId: string, note: string) => void;
};

function reviewLabel(status: MilestoneReport["review_status"]): string {
  if (status === "rejected") return "Laporan ditolak";
  if (status === "approved") return "Laporan disetujui";
  return "Laporan menunggu review";
}

type StageActionsProps = {
  milestone: Milestone;
  onApprove?: (milestoneId: string) => void;
  onReject?: (milestoneId: string, note: string) => void;
};

// Komponen aksi dipisah dari <li> tahap supaya state kolom catatan reject
// (rejecting, note) tidak bercampur dengan state tahap lain: hanya satu
// tahap yang pernah aktif dalam satu waktu (BR-43), tapi memisahkannya
// membuat itu eksplisit, bukan kebetulan.
function StageActions({ milestone, onApprove, onReject }: StageActionsProps) {
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState("");
  const milestoneId = milestone.id ?? "";

  if (!rejecting) {
    return (
      <div className="flex flex-wrap gap-space-2">
        <button
          type="button"
          onClick={() => onApprove?.(milestoneId)}
          aria-label={`Setujui pencairan tahap ${milestone.seq}: ${milestone.title}`}
          className="min-h-[44px] rounded-sm bg-accent px-space-4 py-space-2 text-base font-semibold text-on-accent"
        >
          Setujui
        </button>
        <button
          type="button"
          onClick={() => setRejecting(true)}
          aria-label={`Tolak laporan tahap ${milestone.seq}: ${milestone.title}`}
          className="min-h-[44px] rounded-sm border border-ink px-space-3 py-space-2 text-base font-semibold text-ink"
        >
          Tolak
        </button>
      </div>
    );
  }

  const catatanCukup = note.trim().length >= CATATAN_MINIMAL;

  return (
    <div className="flex flex-col gap-space-2 rounded-card border border-line bg-surface px-space-3 py-space-3">
      <Field label="Catatan untuk UMKM" value={note} onChange={setNote} multiline required />
      <p className="text-[0.8125rem] text-muted">
        Minimal {CATATAN_MINIMAL} karakter. Catatan ini yang dibaca UMKM untuk merevisi laporannya
        (BR-45).
      </p>
      <div className="flex flex-wrap gap-space-2">
        <button
          type="button"
          disabled={!catatanCukup}
          onClick={() => {
            onReject?.(milestoneId, note.trim());
            setRejecting(false);
            setNote("");
          }}
          aria-label={`Kirim penolakan tahap ${milestone.seq}`}
          className="min-h-[44px] rounded-sm border border-ink px-space-3 py-space-2 text-base font-semibold text-ink disabled:border-line disabled:text-muted"
        >
          Kirim penolakan
        </button>
        <button
          type="button"
          onClick={() => {
            setRejecting(false);
            setNote("");
          }}
          className="min-h-[44px] rounded-sm px-space-3 py-space-2 text-base text-muted"
        >
          Batal
        </button>
      </div>
    </div>
  );
}

// Lini milestone satu proposal, disusun vertikal dengan nominal besar di
// tiap tahap (motif identitas DESIGN.md). Tahap aktif (tahap pertama yang
// belum cair, berjalan dari urutan seq) mendapat Amount berukuran besar
// dan satu lencana aksen "Tahap berjalan"; tahap lain memakai ukuran sedang
// dan tanpa aksen, supaya aksen tetap bermakna satu per layar (DESIGN.md).
export function MilestoneTimeline({
  milestones,
  isLeadInvestor = false,
  onApprove,
  onReject,
}: MilestoneTimelineProps) {
  const diurutkan = [...milestones].sort((a, b) => a.seq - b.seq);
  const indeksAktif = diurutkan.findIndex((m) => m.status !== "disbursed");

  return (
    <ol className="flex flex-col">
      {diurutkan.map((milestone, index) => {
        const aktif = index === indeksAktif;

        let teksTahap: string;
        if (milestone.status === "disbursed") {
          teksTahap = "Dana untuk tahap ini sudah cair.";
        } else if (milestone.status === "reported") {
          teksTahap = aktif
            ? "Laporan sudah masuk dan menunggu persetujuan Anda."
            : "Laporan sudah masuk, menunggu persetujuan lead investor.";
        } else if (milestone.seq === 1) {
          teksTahap = aktif
            ? "Tahap pertama tidak memerlukan laporan (BR-41), tetapi tetap menunggu persetujuan Anda."
            : "Tahap pertama menunggu persetujuan lead investor.";
        } else if (aktif) {
          teksTahap = "Menunggu laporan dari UMKM untuk tahap ini.";
        } else {
          teksTahap = "Menunggu tahap sebelumnya selesai.";
        }

        const bisaDiputuskan =
          aktif && (milestone.status === "reported" || (milestone.status === "pending" && milestone.seq === 1));

        return (
          <li
            key={milestone.id ?? milestone.seq}
            className="flex flex-col gap-space-2 border-t border-line py-space-4 first:border-t-0 first:pt-0"
          >
            <div className="flex flex-wrap items-start justify-between gap-space-2">
              <Amount
                label={`Tahap ${milestone.seq}`}
                amount={milestone.amount}
                size={aktif ? "large" : "medium"}
              />
              <StatusBadge status={milestone.status} />
            </div>
            <div className="flex flex-wrap items-center gap-space-2">
              <p className="text-[1.125rem] font-semibold text-ink">{milestone.title}</p>
              {aktif && (
                <span className="inline-flex w-fit items-center rounded-sm bg-accent px-space-2 py-space-1 text-[0.8125rem] font-semibold text-on-accent">
                  Tahap berjalan
                </span>
              )}
            </div>
            {milestone.description && (
              <p className="max-w-measure text-base leading-[1.6] text-muted">{milestone.description}</p>
            )}
            <p className="text-base leading-[1.6] text-ink">{teksTahap}</p>

            {milestone.reports && milestone.reports.length > 0 && (
              <ol className="flex flex-col gap-space-2 border-t border-line pt-space-2">
                {[...milestone.reports].reverse().map((report, i) => (
                  <li key={i} className="text-base leading-[1.6] text-ink">
                    <p className={report.review_status === "rejected" ? "text-danger" : "text-ink"}>
                      {reviewLabel(report.review_status)}: {report.narrative}
                    </p>
                    {report.review_status === "rejected" && report.reviewer_note && (
                      <p className="mt-space-1 text-[0.8125rem] text-muted">
                        Catatan revisi: {report.reviewer_note}
                      </p>
                    )}
                  </li>
                ))}
              </ol>
            )}

            {isLeadInvestor && bisaDiputuskan && (
              <StageActions milestone={milestone} onApprove={onApprove} onReject={onReject} />
            )}
          </li>
        );
      })}
    </ol>
  );
}

export type ApprovalQueueEntry = Milestone & {
  proposalId: string;
  businessName: string;
};

export type ApprovalQueueProps = {
  milestones: ApprovalQueueEntry[];
  onApprove?: (proposalId: string, milestoneId: string) => void;
  onReject?: (proposalId: string, milestoneId: string, note: string) => void;
};

// Keputusan di layar ini: laporan ini cukup atau perlu direvisi. Satu
// entri per proposal yang punya tahap menunggu keputusan lead investor,
// bukan dashboard berisi seluruh proposal yang pernah didanai: proposal
// yang sudah selesai atau belum butuh tindakan tidak muncul di sini sama
// sekali, supaya layar ini tetap fokus pada satu keputusan itu.
export function ApprovalQueue({ milestones, onApprove, onReject }: ApprovalQueueProps) {
  if (milestones.length === 0) {
    return (
      <EmptyState reason="Belum ada laporan yang menunggu persetujuan Anda. Laporan baru akan muncul di sini begitu UMKM mengirimkannya." />
    );
  }

  return (
    <div className="flex flex-col gap-space-6">
      {milestones.map((item) => (
        <div key={`${item.proposalId}-${item.seq}`} className="flex flex-col gap-space-2">
          <Link href={`/proposal/${item.proposalId}`} className="text-[1.125rem] font-semibold text-ink underline">
            {item.businessName}
          </Link>
          <MilestoneTimeline
            milestones={[item]}
            isLeadInvestor
            onApprove={(milestoneId) => onApprove?.(item.proposalId, milestoneId)}
            onReject={(milestoneId, note) => onReject?.(item.proposalId, milestoneId, note)}
          />
        </div>
      ))}
    </div>
  );
}
