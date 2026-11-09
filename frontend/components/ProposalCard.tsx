"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { EmptyState, ErrorState, LoadingState, Nominal } from "@/components/ui";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ApiError, api } from "@/lib/api";

// Bentuk ini mengikuti ProposalOut persis (backend/app/schemas/proposal.py):
// tidak ada score_total, vote_count, atau progres funding di sini karena
// endpoint yang dipakai (GET /proposals dan GET /campaigns/{id}/proposals)
// memang tidak mengembalikannya. Menampilkan angka yang tidak datang dari
// field ini adalah R-17: angka karangan.
export type Proposal = {
  id: string;
  business_name: string;
  business_profile: string;
  requested_amount: number;
  status: string;
  scoring_status: string;
  created_at: string;
};

type ProposalCardProps = {
  proposal: Proposal;
  /**
   * Kartu unggulan mendapat nominal lebih besar dan cuplikan cerita usaha.
   * DESIGN.md meminta variasi kartu yang mencerminkan hierarki isi, bukan
   * grid kartu yang seragam; di sini hierarkinya nyata (bukan dipilih
   * sembarang): proposal terbaru di daftar publik, atau proposal yang
   * sudah lolos penilaian di kotak masuk investor.
   */
  featured?: boolean;
  /** Urutan tampil, dipakai untuk penanda angka pada daftar bernomor. */
  index?: number;
};

export function ProposalCard({ proposal, featured = false, index }: ProposalCardProps) {
  return (
    <article
      className={`flex flex-col gap-space-3 rounded-card border px-space-4 py-space-4 ${
        featured ? "border-ink bg-paper" : "border-line bg-surface"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-space-2">
        <div className="flex items-baseline gap-space-2">
          {index !== undefined && (
            <span aria-hidden="true" className="tabular text-[0.8125rem] font-medium text-muted">
              {String(index + 1).padStart(2, "0")}
            </span>
          )}
          <h3 className="text-[1.125rem] font-semibold text-ink">{proposal.business_name}</h3>
        </div>
        <StatusBadge status={proposal.status} />
      </div>
      <Nominal
        label="Dana diminta"
        nominal={proposal.requested_amount}
        ukuran={featured ? "besar" : "sedang"}
      />
      {featured && (
        <p className="max-w-measure text-base leading-[1.6] text-muted">
          {proposal.business_profile.length > 160
            ? `${proposal.business_profile.slice(0, 160)}...`
            : proposal.business_profile}
        </p>
      )}
      {proposal.scoring_status === "failed" && (
        // D-09: scoring_status terpisah dari status proposal. Gagal di sini
        // berarti job penilaiannya error secara teknis, bukan proposalnya
        // ditolak; proposal tetap "submitted" dan bisa dinilai ulang.
        <p className="text-[0.8125rem] text-warn">
          Penilaian AI gagal dijalankan karena kendala teknis. Proposal ini belum ditolak dan
          bisa dinilai ulang dari halaman proposal.
        </p>
      )}
      <Link href={`/proposal/${proposal.id}`} className="text-base font-medium text-ink underline">
        Baca proposal
      </Link>
    </article>
  );
}

type ProposalListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: Proposal[] };

// Daftar proposal publik di halaman jelajah (GET /proposals: hanya listed ke
// atas, lihat 10-api-contract.md). "use client" di sini, bukan di
// app/jelajah/page.tsx, supaya hanya bagian yang benar-benar butuh fetch dan
// retry yang ditarik ke klien.
export function ProposalList() {
  const [state, setState] = useState<ProposalListState>({ status: "loading" });

  async function load() {
    setState({ status: "loading" });
    try {
      const result = await api.get<{ items: Proposal[] }>("/proposals");
      setState({ status: "ready", items: result.items });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.",
      });
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (state.status === "loading") {
    return <LoadingState label="Memuat daftar proposal" minHeight={240} />;
  }
  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={load} />;
  }
  if (state.items.length === 0) {
    return <EmptyState reason="Belum ada proposal yang terbuka untuk didanai saat ini." />;
  }

  return (
    <div className="flex flex-col gap-space-3">
      {state.items.map((proposal, index) => (
        <ProposalCard key={proposal.id} proposal={proposal} featured={index === 0} index={index} />
      ))}
    </div>
  );
}
