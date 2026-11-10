"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Amount,
  EmptyState,
  ErrorState,
  LoadingState,
  Pagination,
  ResultCount,
} from "@/components/ui";
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
  | { status: "ready"; items: Campaign[]; total: number };

const PAGE_SIZE = 20;

// Keputusan di layar ini: campaign mana yang perlu saya urus sekarang. GET
// /campaigns mengembalikan campaign MILIK SEMUA investor (lihat
// backend/app/services/campaign.py: daftar_campaign tidak memfilter
// investor_id), jadi penyaringan "milik saya" dilakukan di sini lewat
// GET /auth/me, bukan dianggap sudah dijamin backend.
export function CampaignList() {
  const router = useRouter();
  const [state, setState] = useState<ListState>({ status: "loading" });
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setState({ status: "loading" });
    try {
      // ?mine=true, bukan mengunduh seluruh tabel lalu menyaring di browser.
      // Cara lama membuat setiap investor menerima judul, target, tenggat, dan
      // investor_id milik investor lain hanya untuk membuangnya di klien, dan
      // ia juga kehilangan campaign sendiri yang sudah ditutup begitu daftar
      // publik disaring ke status open sesuai 10-api-contract.md:44.
      //
      // page dan page_size ikut dikirim sejak GET /campaigns diberi paginasi:
      // tanpa ini, investor dengan lebih dari dua puluh campaign hanya akan
      // melihat dua puluh pertama dan tidak diberi tahu apa pun tentang
      // sisanya, kelas kegagalan yang persis sama dengan yang baru saja
      // diperbaiki di halaman jelajah.
      const milik = await api.get<{ items: Campaign[]; total: number }>(
        `/campaigns?mine=true&page=${page}&page_size=${PAGE_SIZE}`,
      );
      setState({ status: "ready", items: milik.items, total: milik.total ?? milik.items.length });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.",
      });
    }
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

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
  // Dihitung dari baris di HALAMAN INI saja, jadi penandanya hanya dipasang
  // di halaman pertama: "paling dekat di antara dua puluh yang kebetulan
  // tampil" bukan klaim yang sama dengan "paling dekat di antara semuanya",
  // dan menuliskannya seolah-olah sama adalah angka yang menyesatkan.
  const openCampaigns =
    page === 1 ? state.items.filter((campaign) => campaign.status === "open") : [];
  const urgentId =
    openCampaigns.length > 0
      ? openCampaigns.reduce((a, b) => (new Date(a.apply_deadline) < new Date(b.apply_deadline) ? a : b)).id
      : null;

  return (
    <div className="flex flex-col gap-space-4">
      {/* Satu-satunya tempat tombol ini dirender saat daftar tidak kosong:
          lihat komentar di app/investor/campaign/page.tsx untuk alasan
          header halaman sengaja tidak punya salinannya sendiri lagi. */}
      <Link
        href="/investor/campaign/baru"
        className="inline-flex min-h-[44px] items-center self-start rounded-sm bg-accent px-space-4 py-space-2 text-base font-semibold text-on-accent"
      >
        Buat campaign baru
      </Link>
      <ResultCount page={page} pageSize={PAGE_SIZE} total={state.total} noun="campaign" />
      <ul className="flex flex-col gap-space-3">
        {state.items.map((campaign) => {
          const featured = campaign.id === urgentId;
          return (
            <li key={campaign.id}>
              <Link
                href={`/investor/campaign/${campaign.id}`}
                className={`block rounded-card border px-space-4 py-space-4 ${
                  featured ? "border-ink bg-paper" : "border-line bg-panel"
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-space-2">
                  <h3 className={`font-semibold text-ink ${featured ? "text-card-title" : "text-body"}`}>
                    {campaign.title}
                  </h3>
                  <StatusBadge status={campaign.status} />
                </div>
                <Amount label="Dana target" amount={campaign.target_amount} size={featured ? "large" : "medium"} />
                <p className="mt-space-2 text-label text-muted">
                  Tenggat pengajuan {formatDate(campaign.apply_deadline)}, tenggat funding{" "}
                  {formatDate(campaign.funding_deadline)}
                </p>
              </Link>
            </li>
          );
        })}
      </ul>
      <Pagination
        page={page}
        pageSize={PAGE_SIZE}
        total={state.total}
        onPageChange={setPage}
        label="Halaman daftar campaign saya"
      />
    </div>
  );
}
