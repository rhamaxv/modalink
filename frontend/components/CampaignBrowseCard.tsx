"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Amount,
  EmptyState,
  ErrorState,
  LoadingState,
  Pagination,
  ResultCount,
  Select,
} from "@/components/ui";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Icon, type IconName } from "@/components/icons/Icon";
import { ApiError, api } from "@/lib/api";
import { formatRupiah } from "@/lib/money";

// Bentuk ini mengikuti CampaignOut persis (backend/app/schemas/campaign.py):
// dua deadline terpisah (BR-64/D-16), bukan satu, dan tidak ada field
// "collected_amount" atau progres funding karena campaign itu sendiri tidak
// menyimpan dana, proposal di dalamnya yang menyimpannya. Menampilkan bilah
// progres di sini berarti mengarang angka (R-17).
export type PublicCampaign = {
  id: string;
  investor_id: string;
  title: string;
  description: string;
  sector: string;
  target_amount: number;
  apply_deadline: string;
  funding_deadline: string;
  score_threshold: number;
  status: string;
  created_at: string;
};

// Enam sektor tetap dari backend/app/models/campaign.py (Sector StrEnum).
// Diekspor supaya CampaignDetailPanel memakai pemetaan yang sama, bukan
// menyalin ulang enum ini di dua tempat yang bisa diam-diam menyimpang.
// Kunci yang sama dengan SECTOR_LABEL, dan pagar di tests/icons.test.tsx
// menolak kalau keduanya pernah berbeda isi. Sektor yang ditambahkan di
// backend tanpa ikonnya akan tertangkap di sana, bukan muncul sebagai kotak
// kosong di layar.
export const SECTOR_ICON: Record<string, IconName> = {
  kuliner: "kuliner",
  kerajinan: "kerajinan",
  pertanian: "pertanian",
  jasa: "jasa",
  ritel: "ritel",
  teknologi: "teknologi",
};

export const SECTOR_LABEL: Record<string, string> = {
  kuliner: "Kuliner",
  kerajinan: "Kerajinan",
  pertanian: "Pertanian",
  jasa: "Jasa",
  ritel: "Ritel",
  teknologi: "Teknologi",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });
}

// Bentuk pendek khusus baris daftar: "15 Nov 2026". Dua tenggat berdampingan
// di satu kolom sempit tidak muat dalam bentuk panjang, dan memotongnya di
// tengah lebih buruk daripada menyingkat bulannya.
function formatDateShort(iso: string): string {
  return new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}

type CampaignBrowseCardProps = {
  campaign: PublicCampaign;
  /** Campaign dengan tenggat pengajuan paling dekat mendapat nominal lebih besar. */
  featured?: boolean;
  /** Urutan tampil, dipakai untuk penanda angka pada daftar bernomor. */
  index?: number;
};

export function CampaignBrowseCard({ campaign, featured = false, index }: CampaignBrowseCardProps) {
  return (
    // Satu set kelas untuk kartu biasa maupun unggulan, sama seperti
    // ProposalCard: hierarkinya datang dari ukuran nominal, bukan dari
    // border atau latar yang berbeda.
    <article className="flex flex-col gap-space-3 rounded-card border border-line bg-panel-raised px-space-4 py-space-4">
      <div className="flex flex-wrap items-start justify-between gap-space-2">
        <div className="flex items-baseline gap-space-2">
          {index !== undefined && (
            <span aria-hidden="true" className="tabular text-label font-medium text-muted">
              {String(index + 1).padStart(2, "0")}
            </span>
          )}
          <h3 className="text-card-title font-semibold text-ink">{campaign.title}</h3>
        </div>
        <StatusBadge status={campaign.status} />
      </div>
      <div className="flex flex-wrap items-center gap-space-2">
        {/* Chip accent-2 sebagai LATAR berpasangan dengan on-accent: kombinasi
            ini terukur aman di kedua tema (DESIGN.md). accent-2 sebagai warna
            TEKS polos gagal kontras di tema terang (lihat
            tests/accent-contrast.test.ts), jadi label kategori tidak pernah
            ditulis sebagai teks berwarna lepas. */}
        <span className="inline-flex w-fit items-center gap-space-1 rounded-pill bg-accent-2 px-space-3 py-space-1 text-label font-medium text-on-accent">
          {SECTOR_ICON[campaign.sector] && (
            <Icon name={SECTOR_ICON[campaign.sector]!} size={14} />
          )}
          {SECTOR_LABEL[campaign.sector] ?? campaign.sector}
        </span>
        {featured && (
          // Penanda kedua, bukan dekorasi acak: campaign ini sungguh punya
          // tenggat pengajuan paling dekat di antara yang terbuka (dihitung
          // di CampaignBrowseList), bukan kartu pertama yang dipilih sembarang.
          <span className="inline-flex w-fit items-center rounded-pill bg-accent-2 px-space-3 py-space-1 text-label font-medium text-on-accent">
            Tenggat pengajuan paling dekat
          </span>
        )}
      </div>
      <Amount label="Dana target" amount={campaign.target_amount} size={featured ? "large" : "medium"} />
      {/* D-16: dua tenggat, label berbeda, tidak pernah hanya satu. Satu
          mengikat pengajuan proposal, satu mengikat pendanaannya. Tenggat
          pengajuan kartu unggulan ditulis dengan accent-text: --accent
          sebagai PENANDA (bukan latar tombol) untuk angka yang sedang jadi
          subjek keputusan, persis kategori yang DESIGN.md jatah sampai tiga
          kemunculan per layar, dan --accent-text yang ikut berbalik tema
          dipakai karena ini teks di atas --paper/--panel, bukan di atas
          latar aksen. */}
      <dl className="grid grid-cols-1 gap-space-2 text-label text-muted sm:grid-cols-2">
        <div>
          <dt className="font-medium text-ink">Tenggat pengajuan proposal</dt>
          <dd className={featured ? "font-semibold text-accent-text" : undefined}>
            {formatDate(campaign.apply_deadline)}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-ink">Tenggat pendanaan</dt>
          <dd>{formatDate(campaign.funding_deadline)}</dd>
        </div>
      </dl>
      <Link
        href={`/jelajah/campaign/${campaign.id}`}
        className="inline-flex min-h-[44px] items-center text-body font-medium text-ink underline underline-offset-2"
      >
        Lihat campaign ini
      </Link>
    </article>
  );
}

type CampaignBrowseListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: PublicCampaign[]; total: number };

const SEMUA_SEKTOR = "";

const SECTOR_OPTIONS = [
  { value: SEMUA_SEKTOR, label: "Semua sektor" },
  ...Object.entries(SECTOR_LABEL).map(([value, label]) => ({ value, label })),
];

const PAGE_SIZE = 20;

function sisaHari(iso: string, sekarang: Date): number {
  const selisih = new Date(iso).getTime() - sekarang.getTime();
  return Math.ceil(selisih / (1000 * 60 * 60 * 24));
}

// Satu baris daftar, sepadan dengan ProposalRow di sisi investor.
// CampaignBrowseCard di atas tetap dipakai di tempat lain yang memang
// menampilkan sedikit campaign sekaligus.
//
// Kolom yang dipilih adalah kolom yang dipakai UMKM memutuskan: sektornya
// cocok atau tidak, dananya sepadan atau tidak, dan masih sempat diajukan
// atau tidak. Tenggat pendanaan tidak ikut ke baris ini karena ia tidak
// mengikat keputusan mengajukan; ia ada di halaman detail campaign.
function CampaignBrowseRow({
  campaign,
  index,
  sekarang,
}: {
  campaign: PublicCampaign;
  index: number;
  sekarang: Date;
}) {
  const hari = sisaHari(campaign.apply_deadline, sekarang);
  // Tujuh hari, bukan angka yang dipilih supaya ada yang berwarna: itu
  // kira-kira batas di mana UMKM masih sempat menyusun proposal lengkap
  // dengan rencana milestone sebelum tenggatnya lewat.
  const mendesak = hari <= 7;
  return (
    <Link
      href={`/jelajah/campaign/${campaign.id}`}
      className="group flex flex-col gap-space-2 border-b border-line px-space-2 py-space-3 transition-colors hover:bg-panel-raised md:grid md:grid-cols-[2.5rem_minmax(0,1fr)_9rem_12rem_11rem] md:items-center md:gap-space-4"
    >
      <span aria-hidden="true" className="tabular text-label font-medium text-muted">
        {String(index + 1).padStart(2, "0")}
      </span>

      <span className="flex min-w-0 flex-col gap-space-1">
        <span className="truncate text-card-title font-semibold text-ink group-hover:underline">
          {campaign.title}
        </span>
        <span className="line-clamp-1 text-label text-muted">{campaign.description}</span>
      </span>

      {/* Ikon mendahului namanya, bukan menggantikannya: enam sektor terlalu
          sedikit bedanya untuk dikenali dari lambang saja, tapi cukup untuk
          membuat kolom ini bisa dipindai sekilas saat namanya sudah hafal. */}
      <span className="flex items-center gap-space-2 text-label text-muted">
        {SECTOR_ICON[campaign.sector] && (
          <Icon name={SECTOR_ICON[campaign.sector]!} size={16} />
        )}
        {SECTOR_LABEL[campaign.sector] ?? campaign.sector}
      </span>

      <span className="flex flex-col gap-space-1 md:items-end">
        <span className="tabular text-amount-sm text-ink">
          {formatRupiah(campaign.target_amount)}
        </span>
        <span className="text-label text-muted">dana target</span>
      </span>

      {/* D-16: dua tenggat, label berbeda, tidak pernah hanya satu. Satu
          mengikat pengajuan proposal, satu mengikat pendanaannya, dan
          menampilkan salah satunya saja mengundang UMKM menyangka ia masih
          punya waktu sampai tanggal yang sebenarnya milik tenggat yang lain.
          Tetap berlaku di baris daftar yang sempit, bukan cuma di kartu. */}
      <dl className="flex flex-col gap-space-1 text-label">
        <div className="flex flex-wrap items-baseline gap-space-2">
          <dt className="text-muted">Tenggat pengajuan</dt>
          {/* --accent-text (berbalik ikut tema, duduk di atas --paper/--panel),
              bukan --accent yang tidak pernah berbalik: ini teks, bukan latar.
              Warnanya menandai tenggat yang sungguh tinggal sedikit, bukan
              baris pertama yang kebetulan di atas. */}
          <dd
            className={`tabular ${mendesak ? "font-semibold text-accent-text" : "text-ink"}`}
          >
            {formatDateShort(campaign.apply_deadline)}
            {mendesak && hari >= 0 ? ` (${hari} hari lagi)` : ""}
          </dd>
        </div>
        <div className="flex flex-wrap items-baseline gap-space-2">
          <dt className="text-muted">Tenggat pendanaan</dt>
          <dd className="tabular text-muted">{formatDateShort(campaign.funding_deadline)}</dd>
        </div>
      </dl>
    </Link>
  );
}

// Daftar campaign publik di halaman jelajah, sisi UMKM dari layar yang sama
// tempat ProposalList (ProposalCard.tsx) melayani sisi investor.
//
// Penyaring sektor dan paginasi dikerjakan server lewat query string
// (10-api-contract.md:44). Sebelum ini endpoint-nya tidak punya paginasi sama
// sekali, jadi setiap pengunjung mengunduh seluruh campaign terbuka yang ada.
//
// Penyaring status "open" di bawah tetap dipertahankan walau daftar publik di
// backend sudah menyaringnya: ia murah, dan ia yang menjamin campaign
// tertutup tidak pernah sampai ke layar seandainya jalur publik dan jalur
// "mine" tertukar di kemudian hari. Testnya di tests/campaign-browse.test.tsx
// memverifikasi layar, bukan endpoint.
export function CampaignBrowseList({
  onTotalChange,
}: {
  onTotalChange?: (total: number) => void;
}) {
  const [state, setState] = useState<CampaignBrowseListState>({ status: "loading" });
  const [sector, setSector] = useState(SEMUA_SEKTOR);
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setState({ status: "loading" });
    const query = new URLSearchParams({
      page: String(page),
      page_size: String(PAGE_SIZE),
    });
    if (sector !== SEMUA_SEKTOR) query.set("sector", sector);
    try {
      const result = await api.get<{ items: PublicCampaign[]; total: number }>(
        `/campaigns?${query.toString()}`,
      );
      const open = result.items.filter((campaign) => campaign.status === "open");
      setState({ status: "ready", items: open, total: result.total ?? open.length });
      onTotalChange?.(result.total ?? open.length);
    } catch (error) {
      setState({
        status: "error",
        message:
          error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.",
      });
    }
  }, [page, sector, onTotalChange]);

  useEffect(() => {
    load();
  }, [load]);

  function gantiSektor(nilai: string) {
    setSector(nilai);
    setPage(1);
  }

  const total = state.status === "ready" ? state.total : 0;
  // Dihitung sekali per render, bukan di dalam tiap baris: dua puluh baris
  // yang masing-masing memanggil new Date() bisa jatuh di sisi berbeda dari
  // pergantian hari.
  const sekarang = new Date();

  return (
    <div className="flex flex-col gap-space-4">
      <div className="flex flex-wrap items-center justify-between gap-space-3">
        <Select label="Sektor" value={sector} options={SECTOR_OPTIONS} onChange={gantiSektor} />
        <ResultCount page={page} pageSize={PAGE_SIZE} total={total} noun="campaign" />
      </div>

      {state.status === "loading" && (
        <LoadingState label="Memuat daftar campaign" minHeight={240} />
      )}
      {state.status === "error" && <ErrorState message={state.message} onRetry={load} />}
      {state.status === "ready" && state.items.length === 0 && (
        <EmptyState
          reason={
            sector === SEMUA_SEKTOR
              ? "Belum ada campaign yang terbuka untuk menerima proposal saat ini."
              : "Tidak ada campaign terbuka di sektor itu. Coba sektor lain, atau pilih semua sektor."
          }
        />
      )}
      {state.status === "ready" && state.items.length > 0 && (
        <>
          <ol className="flex flex-col">
            {state.items.map((campaign, index) => (
              <li key={campaign.id} className="list-none">
                <CampaignBrowseRow
                  campaign={campaign}
                  index={(page - 1) * PAGE_SIZE + index}
                  sekarang={sekarang}
                />
              </li>
            ))}
          </ol>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={state.total}
            onPageChange={setPage}
            label="Halaman daftar campaign"
          />
        </>
      )}
    </div>
  );
}
