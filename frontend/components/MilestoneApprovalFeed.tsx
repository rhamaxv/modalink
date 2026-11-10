"use client";

import { useCallback, useEffect, useState } from "react";
import { Amount, ErrorState, LoadingState } from "@/components/ui";
import { ApprovalQueue, type ApprovalQueueEntry, type Milestone } from "@/components/MilestoneTimeline";
import { ApiError, api } from "@/lib/api";
import { fetchCurrentUser } from "@/lib/auth";

type ProposalRingkas = {
  id: string;
  business_name: string;
  status: string;
  lead_investor_id: string | null;
};

type FeedState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; entries: ApprovalQueueEntry[] };

// Milestone aktif tahap ini yang perlu keputusan lead investor: tahap
// pertama (urut seq) yang belum cair, dan baru dianggap "perlu keputusan"
// bila sudah ada laporan (reported) atau tidak memerlukan laporan sama
// sekali (seq = 1, BR-41).
function tahapMenungguKeputusan(milestones: Milestone[]): Milestone | null {
  const diurutkan = [...milestones].sort((a, b) => a.seq - b.seq);
  const aktif = diurutkan.find((m) => m.status !== "disbursed");
  if (!aktif) return null;
  if (aktif.status === "reported") return aktif;
  if (aktif.status === "pending" && aktif.seq === 1) return aktif;
  return null;
}

// Tidak ada endpoint yang mengembalikan "seluruh proposal tempat saya lead
// investor" (lihat .claude/prd/10-api-contract.md): GET /proposals adalah
// daftar publik, bukan daftar bersaring per investor. Jalan yang tersedia
// dari endpoint yang memang ada: ambil daftar publik, saring di klien ke
// proposal funded/completed yang lead_investor_id-nya cocok dengan akun
// saat ini, lalu ambil milestone tiap proposal yang cocok satu per satu.
// Pola ini sama dengan yang dipakai CampaignList (fase 11, stream B) untuk
// menyaring "campaign saya" dari GET /campaigns yang juga tidak punya
// filter pemilik di query-nya.
export function MilestoneApprovalFeed() {
  const [state, setState] = useState<FeedState>({ status: "loading" });

  const muat = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const me = await fetchCurrentUser();
      if (!me) {
        setState({ status: "ready", entries: [] });
        return;
      }
      const daftar = await api.get<{ items: ProposalRingkas[] }>("/proposals");
      const milikSaya = daftar.items.filter(
        (p) => p.lead_investor_id === me.id && (p.status === "funded" || p.status === "completed"),
      );

      const entries: ApprovalQueueEntry[] = [];
      for (const proposal of milikSaya) {
        const milestoneList = await api.get<{ items: Milestone[] }>(`/proposals/${proposal.id}/milestones`);
        const perlu = tahapMenungguKeputusan(milestoneList.items);
        if (perlu) {
          entries.push({ ...perlu, proposalId: proposal.id, businessName: proposal.business_name });
        }
      }
      setState({ status: "ready", entries });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.",
      });
    }
  }, []);

  useEffect(() => {
    muat();
  }, [muat]);

  async function approve(_proposalId: string, milestoneId: string) {
    try {
      await api.post(`/milestones/${milestoneId}/approve`);
      muat();
    } catch {
      // Permintaan gagal tidak mengubah tampilan yang sudah ada; pengguna
      // masih melihat tombol yang sama untuk mencoba lagi.
    }
  }

  async function reject(_proposalId: string, milestoneId: string, note: string) {
    try {
      await api.post(`/milestones/${milestoneId}/reject`, { note });
      muat();
    } catch {
      // Sama seperti approve: kegagalan tidak menghapus antrian yang tampil.
    }
  }

  if (state.status === "loading") {
    return <LoadingState label="Memuat laporan yang menunggu persetujuan" minHeight={240} />;
  }
  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={muat} />;
  }

  // Satu-satunya kemunculan --accent di layar ini (DESIGN.md: "uang" mengisi
  // ruang tempat foto bekerja di referensi). Angka ini penjumlahan nominal
  // tahap yang sungguh tampil di antrian, bukan dikarang (R-17): nol entri
  // berarti nol rupiah, bukan disembunyikan.
  const totalMenunggu = state.entries.reduce((total, entry) => total + entry.amount, 0);

  return (
    <div className="flex flex-col gap-space-6">
      {state.entries.length > 0 && (
        <Amount label="Total menunggu pencairan Anda" amount={totalMenunggu} size="hero" tone="accent" />
      )}
      <ApprovalQueue milestones={state.entries} onApprove={approve} onReject={reject} />
    </div>
  );
}
