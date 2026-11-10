"use client";

import { useEffect, useState } from "react";
import { Amount, ButtonLink, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ProposalCard, type Proposal } from "@/components/ProposalCard";
import { SECTOR_LABEL, type PublicCampaign } from "@/components/CampaignBrowseCard";
import { ApiError, api } from "@/lib/api";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });
}

// GET /campaigns/{id}/proposals mengembalikan ProposalWithSignalsOut
// (backend/app/schemas/proposal.py): ProposalOut lengkap, business_profile
// PENUH, ditambah total_score dan vote_count. Bukan ProposalListItemOut
// yang dipakai GET /proposals (sudah dipotong server jadi
// business_profile_excerpt). Dua kontrak berbeda untuk dua endpoint berbeda,
// dan field inilah sumber mismatch itu: dipetakan ke bentuk Proposal lewat
// petakeProposal di bawah, bukan dipaksa cocok lewat cast.
type ProposalMasuk = {
  id: string;
  business_name: string;
  business_profile: string;
  requested_amount: number;
  // ProposalWithSignalsOut mewarisi ProposalOut, jadi field ini memang ikut
  // terkirim oleh GET /campaigns/{id}/proposals; sebelumnya cuma tidak
  // pernah dideklarasikan di sini.
  collected_amount: number;
  status: string;
  scoring_status: string;
  created_at: string;
};

const PANJANG_CUPLIKAN = 160;

// Memotong business_profile PENUH jadi cuplikan di klien, meniru persis apa
// yang backend lakukan untuk GET /proposals (lihat komentar
// ProposalListItemOut di backend/app/schemas/proposal.py). Ini bukan
// mengarang data (R-17/R-38): isinya tetap kalimat nyata dari proposal,
// cuma dipotong supaya ProposalCard (yang mengharapkan bentuk ringkas)
// tetap bisa dipakai apa adanya tanpa diubah.
function petakeProposal(p: ProposalMasuk): Proposal {
  const cuplikan =
    p.business_profile.length > PANJANG_CUPLIKAN
      ? `${p.business_profile.slice(0, PANJANG_CUPLIKAN)}...`
      : p.business_profile;
  return {
    id: p.id,
    business_name: p.business_name,
    business_profile_excerpt: cuplikan,
    requested_amount: p.requested_amount,
    collected_amount: p.collected_amount,
    status: p.status,
    scoring_status: p.scoring_status,
    created_at: p.created_at,
  };
}

type PanelState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; campaign: PublicCampaign; proposals: ProposalMasuk[] };

// Halaman detail campaign PUBLIK: siapa pun bisa membukanya tanpa masuk,
// termasuk juri lomba lewat tautan yang dibagikan. Beda dari
// CampaignManagePanel (dashboard investor): tidak ada tombol tutup campaign
// atau ubah detail di sini, cuma informasi untuk memutuskan apakah layak
// diajukan proposal, dan satu tautan ke /umkm/proposal/baru (rute milik
// alur UMKM, dibangun di worktree lain, bukan dibuat di sini).
export function CampaignDetailPanel({ campaignId }: { campaignId: string }) {
  const [state, setState] = useState<PanelState>({ status: "loading" });

  async function load() {
    setState({ status: "loading" });
    try {
      const [campaign, proposalList] = await Promise.all([
        api.get<PublicCampaign>(`/campaigns/${campaignId}`),
        api.get<{ items: ProposalMasuk[] }>(`/campaigns/${campaignId}/proposals`),
      ]);
      setState({ status: "ready", campaign, proposals: proposalList.items });
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
    return <LoadingState label="Memuat campaign" minHeight={320} />;
  }
  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={load} />;
  }

  const { campaign, proposals } = state;
  const tenggatLewat = new Date(campaign.apply_deadline).getTime() < Date.now();
  const bisaDiajukan = campaign.status === "open" && !tenggatLewat;

  return (
    <div className="flex flex-col gap-space-5">
      <div className="flex flex-col gap-space-3">
        <div className="flex flex-wrap items-start justify-between gap-space-3">
          <h1 className="text-page font-display text-ink">{campaign.title}</h1>
          <StatusBadge status={campaign.status} />
        </div>
        <span className="inline-flex w-fit items-center rounded-pill bg-accent-2 px-space-3 py-space-1 text-label font-medium text-on-accent">
          {SECTOR_LABEL[campaign.sector] ?? campaign.sector}
        </span>
        <p className="max-w-measure text-body text-muted">{campaign.description}</p>
        <Amount label="Dana target" amount={campaign.target_amount} size="large" />

        {/* D-16: dua tenggat, label berbeda, tidak pernah hanya satu. */}
        <dl className="mt-space-2 grid grid-cols-1 gap-space-2 text-label text-muted sm:grid-cols-2">
          <div>
            <dt className="font-medium text-ink">Tenggat pengajuan proposal</dt>
            {/* accent-text, bukan bg-accent: ini angka yang sedang jadi
                subjek keputusan UMKM (apakah sempat mengajukan sebelum
                tanggal ini), persis kategori "penanda" yang DESIGN.md jatah
                sampai tiga kemunculan, bukan aksi berlatar aksen. */}
            <dd className={bisaDiajukan ? "font-semibold text-accent-text" : undefined}>
              {formatDate(campaign.apply_deadline)}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-ink">Tenggat pendanaan</dt>
            <dd>{formatDate(campaign.funding_deadline)}</dd>
          </div>
        </dl>

        {bisaDiajukan ? (
          <ButtonLink href="/umkm/proposal/baru" className="mt-space-2 self-start">
            Ajukan proposal ke campaign ini
          </ButtonLink>
        ) : (
          <p className="mt-space-2 text-label text-muted">
            {campaign.status === "closed"
              ? "Campaign ini sudah ditutup. Proposal baru tidak bisa masuk lagi, tapi proposal yang sudah masuk tetap berjalan sampai selesai."
              : `Tenggat pengajuan proposal untuk campaign ini sudah lewat (${formatDate(campaign.apply_deadline)}).`}
          </p>
        )}
      </div>

      <div>
        <h2 className="text-section font-display text-ink">Proposal yang sudah diajukan</h2>
        {proposals.length === 0 ? (
          <div className="mt-space-3">
            <EmptyState reason="Belum ada proposal yang diajukan ke campaign ini." />
          </div>
        ) : (
          <ol className="mt-space-3 flex flex-col gap-space-3">
            {proposals.map((proposal, index) => (
              <li key={proposal.id} className="list-none">
                {/* Sama seperti CampaignManagePanel: proposal yang sudah
                    publik (listed ke atas) mendapat cuplikan cerita usaha,
                    bukan proposal pertama yang dipilih sembarang. */}
                <ProposalCard
                  proposal={petakeProposal(proposal)}
                  index={index}
                  featured={["listed", "partially_funded", "funded"].includes(proposal.status)}
                />
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
