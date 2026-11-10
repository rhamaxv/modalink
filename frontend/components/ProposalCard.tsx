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
import { SECTOR_LABEL } from "@/components/CampaignBrowseCard";
import { ApiError, api } from "@/lib/api";
import { formatRupiah, persenProgres } from "@/lib/money";

// Bentuk ini mengikuti ProposalOut persis (backend/app/schemas/proposal.py):
// tidak ada score_total, vote_count, atau progres funding di sini karena
// endpoint yang dipakai (GET /proposals dan GET /campaigns/{id}/proposals)
// memang tidak mengembalikannya. Menampilkan angka yang tidak datang dari
// field ini adalah R-17: angka karangan.
export type Proposal = {
  id: string;
  business_name: string;
  // Cuplikan, bukan profil penuh: GET /proposals sengaja tidak lagi
  // mengirim rencana bisnis lengkap, dan pemotongannya dilakukan server.
  business_profile_excerpt: string;
  requested_amount: number;
  // BR-51/D-03: selalu dijumlahkan dari ledger, tidak pernah kolom tersimpan.
  // Sudah ada di ProposalOut sejak Task 1 tapi belum pernah dibaca daftar
  // ini, jadi tiap baris menampilkan nominal yang diminta tanpa satu pun
  // petunjuk berapa yang sudah terkumpul.
  collected_amount: number;
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
    // Satu set kelas dasar untuk kartu biasa maupun unggulan, bukan dua:
    // DESIGN.md membatasi batas kartu pada --line, bukan penekanan warna,
    // jadi hierarkinya datang dari ukuran nominal dan cuplikan cerita (di
    // bawah), bukan dari border atau latar yang berbeda. bg-panel-raised,
    // bukan bg-panel: kartu ini dipakai di atas section berlatar bg-panel
    // (halaman jelajah) maupun di atas bg-paper (panel manajemen campaign),
    // dan panel-raised tetap terlihat sebagai permukaan terangkat di kedua
    // latar.
    //
    // Kartu unggulan mendapat satu tambahan jujur: tepi kiri beraksen-2 dan
    // radius feature, bukan radius card biasa. Bukan label teks yang
    // mengklaim arti ("unggulan", "pilihan"), karena arti "featured" berbeda
    // di tiap pemanggil (proposal pertama di daftar publik di sini, proposal
    // live/funded di CampaignManagePanel): sinyal visual murni, menandai
    // kartu mana yang berbeda tanpa menulis klaim yang bisa salah di salah
    // satu konteks itu.
    <article
      className={`flex flex-col gap-space-3 border border-line bg-panel-raised px-space-4 py-space-4 ${
        featured ? "rounded-feature border-l-4 border-l-accent-2 md:px-space-5" : "rounded-card"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-space-2">
        <div className="flex items-baseline gap-space-2">
          {index !== undefined && (
            <span aria-hidden="true" className="tabular text-label font-medium text-muted">
              {String(index + 1).padStart(2, "0")}
            </span>
          )}
          <h3 className="text-card-title font-semibold text-ink">{proposal.business_name}</h3>
        </div>
        <StatusBadge status={proposal.status} />
      </div>
      <Amount
        label="Dana diminta"
        amount={proposal.requested_amount}
        size={featured ? "large" : "medium"}
      />
      {featured && (
        <p className="max-w-measure text-body text-muted">
          {proposal.business_profile_excerpt}
        </p>
      )}
      {proposal.scoring_status === "failed" && (
        // D-09: scoring_status terpisah dari status proposal. Gagal di sini
        // berarti job penilaiannya error secara teknis, bukan proposalnya
        // ditolak; proposal tetap "submitted" dan bisa dinilai ulang.
        <p className="text-label text-warn">
          Penilaian AI gagal dijalankan karena kendala teknis. Proposal ini belum ditolak dan
          bisa dinilai ulang dari halaman proposal.
        </p>
      )}
      <Link
        href={`/proposal/${proposal.id}`}
        className="inline-flex min-h-[44px] items-center text-body font-medium text-ink underline underline-offset-2"
      >
        Baca proposal
      </Link>
    </article>
  );
}

type FeaturedState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "empty" }
  | { status: "ready"; proposal: Proposal };

// Jawaban DESIGN.md atas "apa yang mengisi ruang tempat foto bekerja di
// referensi": satu proposal nyata yang sudah terbuka untuk didanai, dengan
// nominalnya di ukuran "hero", persis posisi yang di the5ers.com ditempati
// foto manusia. Dipakai sekali di hero halaman landing (app/page.tsx), bukan
// di halaman jelajah: ProposalCard di sana sudah punya kartu unggulannya
// sendiri di ukuran "large" (tokoh utama KARTU, lihat komentar Amount.tsx),
// "hero" sengaja hanya untuk angka yang memimpin HALAMAN.
export function FeaturedProposalHighlight() {
  const [state, setState] = useState<FeaturedState>({ status: "loading" });

  async function load() {
    setState({ status: "loading" });
    try {
      const result = await api.get<{ items: Proposal[] }>("/proposals");
      const utama = result.items[0];
      setState(utama ? { status: "ready", proposal: utama } : { status: "empty" });
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

  // Tinggi minimum dipesan di ketiga keadaan supaya hero tidak melompat
  // begitu data datang: perkiraan tinggi kotak "ready" di bawah.
  if (state.status === "loading") {
    return <LoadingState label="Memuat proposal unggulan" minHeight={220} />;
  }
  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={load} />;
  }
  if (state.status === "empty") {
    // Bukan EmptyState biasa: aksinya adalah NAVIGASI ke rute yang sudah
    // ada, bukan mutasi, jadi ia memakai <Link> sungguhan (Fungsional
    // Pattern "anchor ke rute nyata"), bukan tombol yang berpura-pura
    // berpindah halaman lewat useRouter(). Tautan teks, bukan tombol
    // bg-accent: section CTA di bagian bawah halaman ini sudah memegang
    // satu-satunya aksi utama berwarna aksen di layar, dan kekosongan di
    // sini hanyalah jalan pintas sekunder ke rute yang sama, bukan aksi
    // kedua yang bersaing memperebutkan perhatian.
    return (
      <div className="flex flex-col items-start gap-space-3 rounded-card border border-line bg-panel px-space-4 py-space-5 text-left">
        <p className="max-w-measure text-body text-muted">
          Belum ada proposal yang terbuka untuk didanai saat ini.
        </p>
        <Link
          href="/daftar"
          className="inline-flex min-h-[44px] items-center text-body font-medium text-ink underline underline-offset-2"
        >
          Daftar sebagai UMKM
        </Link>
      </div>
    );
  }

  const { proposal } = state;
  return (
    <div className="flex flex-col gap-space-3 rounded-feature border border-line bg-panel-raised px-space-5 py-space-6">
      {/*
        "Terbuka untuk pendanaan" bukan klaim dikarang: GET /proposals hanya
        pernah mengirim proposal berstatus listed ke atas (lihat komentar
        ProposalList di bawah), jadi baris ini benar untuk setiap proposal
        yang bisa muncul di sini. bg-accent-2 + text-on-accent: pasangan yang
        sama persis dengan yang DESIGN.md ukur lolos 9,59:1 dan tidak
        berbalik warna di kedua tema.
      */}
      <p className="inline-block w-fit rounded-sm bg-accent-2 px-space-2 py-space-1 text-label font-medium uppercase tracking-wide text-on-accent">
        Terbuka untuk pendanaan
      </p>
      <p className="text-label font-medium uppercase tracking-wide text-muted">
        {proposal.business_name}
      </p>
      <Amount label="Dana diminta" amount={proposal.requested_amount} size="hero" />
      <Link
        href={`/proposal/${proposal.id}`}
        className="inline-flex min-h-[44px] items-center text-body font-medium text-ink underline underline-offset-2"
      >
        Baca proposal ini
      </Link>
    </div>
  );
}

type ProposalListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: Proposal[]; total: number };

const SORT_OPTIONS = [
  { value: "newest", label: "Terbaru" },
  { value: "amount_desc", label: "Dana diminta terbesar" },
  { value: "amount_asc", label: "Dana diminta terkecil" },
  { value: "most_funded", label: "Paling banyak terkumpul" },
];

const SEMUA_SEKTOR = "";

const SECTOR_OPTIONS = [
  { value: SEMUA_SEKTOR, label: "Semua sektor" },
  ...Object.entries(SECTOR_LABEL).map(([value, label]) => ({ value, label })),
];

const PAGE_SIZE = 20;

// Satu baris daftar, bukan kartu.
//
// ProposalCard di atas tetap dipakai di layar KEPUTUSAN (panel campaign
// publik dan panel kelola campaign) tempat jumlah barisnya sedikit dan tiap
// proposal memang layak satu kotak sendiri. Di halaman indeks, kotak setinggi
// 120px dikalikan dua puluh baris berarti pengunjung harus menggulir enam
// layar penuh hanya untuk tahu apa saja yang ada, dan tidak ada satu pun
// kolom yang sejajar untuk dibandingkan. Baris ini memasang nama, nominal,
// dan progres di posisi tetap supaya dua puluh baris bisa dipindai, bukan
// dibaca satu per satu.
function ProposalRow({ proposal, index }: { proposal: Proposal; index: number }) {
  const persen = persenProgres(proposal.collected_amount, proposal.requested_amount);
  return (
    <Link
      href={`/proposal/${proposal.id}`}
      className="group flex flex-col gap-space-2 border-b border-line px-space-2 py-space-3 transition-colors hover:bg-panel-raised md:grid md:grid-cols-[1.75rem_minmax(0,1fr)_13rem_13rem] md:items-center md:gap-space-3"
    >
      <span aria-hidden="true" className="tabular text-label font-medium text-muted">
        {String(index + 1).padStart(2, "0")}
      </span>

      <span className="flex min-w-0 flex-col gap-space-1">
        <span className="truncate text-card-title font-semibold text-ink group-hover:underline">
          {proposal.business_name}
        </span>
        <span className="line-clamp-1 text-label text-muted">
          {proposal.business_profile_excerpt}
        </span>
      </span>

      {/* Kolom uang: nominal, jumlah terkumpul, dan bilahnya dalam satu kolom.
          Versi pertama menaruh bilah di bawah badge status, satu kolom jauh
          dari angka yang dijelaskannya, sehingga pembaca harus menyeberangi
          baris untuk menghubungkan keduanya.

          Rata kanan dengan angka tabular: dua nominal di baris berbeda hanya
          bisa dibandingkan sekilas kalau digitnya berbaris lurus ke bawah. */}
      <span className="flex flex-col gap-space-1 md:items-end">
        <span className="tabular text-amount-sm text-ink">
          {formatRupiah(proposal.requested_amount)}
        </span>
        <span className="tabular text-label text-muted">
          {formatRupiah(proposal.collected_amount)} terkumpul
        </span>
        {/* Bilah tipis, bukan bilah 24px seperti di halaman proposal: di sana
            ia jawaban pertanyaan utama satu layar, di sini ia satu kolom dari
            dua puluh baris. Lebarnya datang dari collected_amount sungguhan,
            bukan nilai hias. */}
        <span
          aria-hidden="true"
          className="h-1 w-full max-w-[13rem] overflow-hidden rounded-pill bg-line"
        >
          <span className="block h-full bg-accent" style={{ width: `${persen}%` }} />
        </span>
        <span className="sr-only">{persen} persen dari dana yang diminta sudah terkumpul.</span>
      </span>

      {/* Kolom status dilebarkan ke 13rem supaya label terpanjang yang ada
          ("Terbuka untuk pendanaan") muat satu baris: dibungkus dua baris, ia
          membuat tinggi tiap baris daftar berbeda-beda dan kolom di kiri
          ikut bergoyang. */}
      <span className="flex md:justify-end">
        <StatusBadge status={proposal.status} className="whitespace-nowrap" />
      </span>
    </Link>
  );
}

// Daftar proposal publik di halaman jelajah (GET /proposals: hanya listed ke
// atas, lihat 10-api-contract.md). "use client" di berkas ini, bukan di
// app/jelajah/page.tsx, supaya hanya bagian yang benar-benar butuh fetch dan
// retry yang ditarik ke klien.
//
// Penyaring sektor, pengurutan, dan paginasi semuanya dikerjakan SERVER lewat
// query string. Menyaring dua puluh baris yang sudah terlanjur diunduh di
// browser akan terlihat bekerja selama data contoh masih sedikit, lalu
// berbohong begitu datanya lewat satu halaman: yang disaring cuma halaman
// yang sedang dibuka, bukan seluruh daftar.
export function ProposalList({ onTotalChange }: { onTotalChange?: (total: number) => void }) {
  const [state, setState] = useState<ProposalListState>({ status: "loading" });
  const [sector, setSector] = useState(SEMUA_SEKTOR);
  const [sort, setSort] = useState("newest");
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setState({ status: "loading" });
    const query = new URLSearchParams({
      page: String(page),
      page_size: String(PAGE_SIZE),
      sort,
    });
    if (sector !== SEMUA_SEKTOR) query.set("sector", sector);
    try {
      const result = await api.get<{ items: Proposal[]; total: number }>(
        `/proposals?${query.toString()}`,
      );
      setState({ status: "ready", items: result.items, total: result.total });
      onTotalChange?.(result.total);
    } catch (error) {
      setState({
        status: "error",
        message:
          error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.",
      });
    }
  }, [page, sector, sort, onTotalChange]);

  useEffect(() => {
    load();
  }, [load]);

  // Mengganti penyaring harus mengembalikan ke halaman satu: tanpa ini,
  // menyaring dari halaman 3 memberi daftar kosong yang terlihat seperti
  // "tidak ada hasil" padahal hasilnya ada, cuma di halaman 1.
  function gantiSektor(nilai: string) {
    setSector(nilai);
    setPage(1);
  }

  function gantiUrutan(nilai: string) {
    setSort(nilai);
    setPage(1);
  }

  const total = state.status === "ready" ? state.total : 0;

  return (
    <div className="flex flex-col gap-space-4">
      <div className="flex flex-wrap items-center justify-between gap-space-3">
        <div className="flex flex-wrap items-center gap-space-3">
          <Select
            label="Sektor"
            value={sector}
            options={SECTOR_OPTIONS}
            onChange={gantiSektor}
          />
          <Select label="Urutkan" value={sort} options={SORT_OPTIONS} onChange={gantiUrutan} />
        </div>
        <ResultCount page={page} pageSize={PAGE_SIZE} total={total} noun="proposal" />
      </div>

      {state.status === "loading" && (
        <LoadingState label="Memuat daftar proposal" minHeight={240} />
      )}
      {state.status === "error" && <ErrorState message={state.message} onRetry={load} />}
      {state.status === "ready" && state.items.length === 0 && (
        <EmptyState
          reason={
            sector === SEMUA_SEKTOR
              ? "Belum ada proposal yang terbuka untuk didanai saat ini."
              : "Tidak ada proposal terbuka di sektor itu. Coba sektor lain, atau pilih semua sektor."
          }
        />
      )}
      {state.status === "ready" && state.items.length > 0 && (
        <>
          {/* <ol>, bukan <div>: tiap baris menampilkan nomor urutnya secara
              visual, jadi daftar ini memang bernomor dan semantiknya harus
              mengatakan itu juga ke pembaca layar. */}
          <ol className="flex flex-col">
            {state.items.map((proposal, index) => (
              <li key={proposal.id} className="list-none">
                <ProposalRow proposal={proposal} index={(page - 1) * PAGE_SIZE + index} />
              </li>
            ))}
          </ol>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={state.total}
            onPageChange={setPage}
            label="Halaman daftar proposal"
          />
        </>
      )}
    </div>
  );
}
