"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { EmptyState, ErrorState, LoadingState, Nominal } from "@/components/ui";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ApiError, api } from "@/lib/api";

type Campaign = {
  id: string;
  investor_id: string;
  title: string;
  sector: string;
  target_amount: number;
  apply_deadline: string;
  funding_deadline: string;
  status: string;
  created_at: string;
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });
}

type ListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: Campaign[] };

// Keputusan di layar ini: campaign mana yang perlu saya urus sekarang. GET
// /campaigns mengembalikan campaign MILIK SEMUA investor (lihat
// backend/app/services/campaign.py: daftar_campaign tidak memfilter
// investor_id), jadi penyaringan "milik saya" dilakukan di sini lewat
// GET /auth/me, bukan dianggap sudah dijamin backend.
export function CampaignList() {
  const router = useRouter();
  const [state, setState] = useState<ListState>({ status: "loading" });

  async function load() {
    setState({ status: "loading" });
    try {
      const [me, all] = await Promise.all([
        api.get<{ id: string }>("/auth/me"),
        api.get<{ items: Campaign[] }>("/campaigns"),
      ]);
      const mine = all.items.filter((campaign) => campaign.investor_id === me.id);
      setState({ status: "ready", items: mine });
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
    return <LoadingState label="Memuat campaign saya" minHeight={160} />;
  }
  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={load} />;
  }
  if (state.items.length === 0) {
    return (
      <EmptyState
        reason="Anda belum punya campaign."
        action={{ label: "Buat campaign baru", onClick: () => router.push("/investor/campaign/baru") }}
      />
    );
  }

  // Campaign open dengan tenggat pengajuan paling dekat adalah yang paling
  // perlu diurus sekarang; itulah yang mendapat perlakuan menonjol, bukan
  // urutan acak atau urutan dari server (DESIGN.md: variasi kartu harus
  // mencerminkan hierarki isi yang nyata).
  const openCampaigns = state.items.filter((campaign) => campaign.status === "open");
  const urgentId =
    openCampaigns.length > 0
      ? openCampaigns.reduce((a, b) => (new Date(a.apply_deadline) < new Date(b.apply_deadline) ? a : b)).id
      : null;

  return (
    <ul className="flex flex-col gap-space-3">
      {state.items.map((campaign) => {
        const featured = campaign.id === urgentId;
        return (
          <li key={campaign.id}>
            <Link
              href={`/investor/campaign/${campaign.id}`}
              className={`block rounded-card border px-space-4 py-space-4 ${
                featured ? "border-ink bg-paper" : "border-line bg-surface"
              }`}
            >
              <div className="flex flex-wrap items-start justify-between gap-space-2">
                <h3 className={`font-semibold text-ink ${featured ? "text-[1.25rem]" : "text-[1.125rem]"}`}>
                  {campaign.title}
                </h3>
                <StatusBadge status={campaign.status} />
              </div>
              <Nominal label="Dana target" nominal={campaign.target_amount} ukuran={featured ? "besar" : "sedang"} />
              <p className="mt-space-2 text-[0.8125rem] text-muted">
                Tenggat pengajuan {formatDate(campaign.apply_deadline)}, tenggat funding{" "}
                {formatDate(campaign.funding_deadline)}
              </p>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
