"use client";

import { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState, Nominal } from "@/components/ui";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ApiError, api } from "@/lib/api";
import { CampaignForm, type CampaignOut } from "@/components/CampaignForm";
import { ProposalCard, type Proposal } from "@/components/ProposalCard";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });
}

type PanelState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; campaign: CampaignOut; isOwner: boolean; proposals: Proposal[] };

// Keputusan di layar ini: proposal mana yang layak saya baca lebih dalam.
// Tutup campaign dan ubah detail adalah kontrol sekunder di halaman yang
// sama, bukan keputusan utamanya, jadi ditempatkan sebelum daftar proposal
// tapi tidak mendominasi layar (tanpa kartu statistik, tanpa grafik).
export function CampaignManagePanel({ campaignId }: { campaignId: string }) {
  const [state, setState] = useState<PanelState>({ status: "loading" });
  const [editing, setEditing] = useState(false);
  const [confirmingClose, setConfirmingClose] = useState(false);
  const [closing, setClosing] = useState(false);
  const [closeError, setCloseError] = useState<string | null>(null);

  async function load() {
    setState({ status: "loading" });
    try {
      const [campaign, me, proposalList] = await Promise.all([
        api.get<CampaignOut>(`/campaigns/${campaignId}`),
        api.get<{ id: string }>("/auth/me").catch(() => null),
        api.get<{ items: Proposal[] }>(`/campaigns/${campaignId}/proposals`),
      ]);
      setState({
        status: "ready",
        campaign,
        isOwner: me !== null && me.id === campaign.investor_id,
        proposals: proposalList.items,
      });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.",
      });
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaignId]);

  if (state.status === "loading") {
    return <LoadingState label="Memuat campaign" minHeight={240} />;
  }
  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={load} />;
  }

  const { campaign, isOwner, proposals } = state;

  async function handleClose() {
    setClosing(true);
    setCloseError(null);
    try {
      const updated = await api.post<CampaignOut>(`/campaigns/${campaignId}/close`);
      setState({ status: "ready", campaign: updated, isOwner, proposals });
      setConfirmingClose(false);
    } catch (error) {
      setCloseError(error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.");
    } finally {
      setClosing(false);
    }
  }

  return (
    <div className="flex flex-col gap-space-5">
      <div className="flex flex-col gap-space-2">
        <div className="flex flex-wrap items-start justify-between gap-space-3">
          <h1 className="text-[clamp(2.5rem,5vw,4rem)] font-semibold leading-tight text-ink">{campaign.title}</h1>
          <StatusBadge status={campaign.status} />
        </div>
        <p className="max-w-measure text-base leading-[1.6] text-muted">{campaign.description}</p>
        <Nominal label="Dana target" nominal={campaign.target_amount} />

        {/* D-16: dua tenggat, label berbeda, tidak pernah hanya satu. */}
        <dl className="mt-space-2 grid grid-cols-1 gap-space-2 text-[0.8125rem] text-muted sm:grid-cols-2">
          <div>
            <dt className="font-medium text-ink">Tenggat pengajuan proposal</dt>
            <dd>{formatDate(campaign.apply_deadline)}</dd>
          </div>
          <div>
            <dt className="font-medium text-ink">Tenggat funding</dt>
            <dd>{formatDate(campaign.funding_deadline)}</dd>
          </div>
        </dl>

        {isOwner && campaign.status === "open" && (
          <div className="mt-space-3 flex flex-col gap-space-2">
            {!confirmingClose ? (
              <button
                type="button"
                onClick={() => setConfirmingClose(true)}
                className="min-h-[44px] self-start rounded-sm border border-ink px-space-3 py-space-2 text-base font-semibold text-ink"
              >
                Tutup campaign
              </button>
            ) : (
              // Konfirmasi dibangun sebagai elemen di halaman, bukan
              // window.confirm: dialog bawaan browser memblokir seluruh
              // event dan tidak bisa diuji otomatis.
              <div className="flex flex-col gap-space-2 rounded-card border border-line bg-surface px-space-3 py-space-3">
                <p className="text-base leading-[1.6] text-ink">
                  Yakin ingin menutup campaign ini? Proposal baru tidak bisa masuk lagi setelah
                  ditutup, tapi proposal yang sudah masuk tetap berjalan sampai selesai.
                </p>
                {closeError && <p role="alert" className="text-[0.8125rem] text-danger">{closeError}</p>}
                <div className="flex flex-wrap gap-space-2">
                  <button
                    type="button"
                    onClick={handleClose}
                    disabled={closing}
                    aria-busy={closing}
                    className="min-h-[44px] rounded-sm border border-ink px-space-3 py-space-2 text-base font-semibold text-ink"
                  >
                    Ya, tutup campaign
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmingClose(false)}
                    disabled={closing}
                    className="min-h-[44px] rounded-sm px-space-3 py-space-2 text-base text-muted"
                  >
                    Batal
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {campaign.status === "closed" && (
          <p className="mt-space-2 text-[0.8125rem] text-muted">
            Campaign ini sudah ditutup. Proposal baru tidak bisa masuk lagi, tapi proposal yang
            sudah masuk tetap berjalan sampai selesai.
          </p>
        )}

        {isOwner && (
          <div className="mt-space-3">
            {!editing ? (
              <button type="button" onClick={() => setEditing(true)} className="text-base font-medium text-ink underline">
                Ubah judul, deskripsi, atau ambang skor
              </button>
            ) : (
              <div className="mt-space-3 max-w-measure">
                <CampaignForm
                  mode="edit"
                  campaignId={campaign.id}
                  initialValues={{
                    title: campaign.title,
                    description: campaign.description,
                    scoreThreshold: String(campaign.score_threshold),
                  }}
                  onSaved={(updated) => {
                    setState({ status: "ready", campaign: updated, isOwner, proposals });
                    setEditing(false);
                  }}
                />
              </div>
            )}
          </div>
        )}
      </div>

      <div>
        <h2 className="text-[1.75rem] font-semibold text-ink">Proposal yang masuk</h2>
        {proposals.length === 0 ? (
          <div className="mt-space-3">
            <EmptyState reason="Belum ada proposal masuk ke campaign ini." />
          </div>
        ) : (
          <div className="mt-space-3 flex flex-col gap-space-3">
            {proposals.map((proposal, index) => (
              <ProposalCard
                key={proposal.id}
                proposal={proposal}
                index={index}
                featured={["listed", "partially_funded", "funded"].includes(proposal.status)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
