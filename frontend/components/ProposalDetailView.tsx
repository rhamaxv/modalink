"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { CommentForm } from "@/components/CommentForm";
import { CommentList } from "@/components/CommentList";
import { FundingBar } from "@/components/FundingBar";
import { PledgeForm } from "@/components/PledgeForm";
import { ScorePanel, type ProposalScore, type ScoringStatus } from "@/components/ScorePanel";
import type { CurrentUser } from "@/lib/auth";
import { CoverImage } from "@/components/ui/CoverImage";
import { CoverUpload } from "@/components/CoverUpload";
import { SECTOR_ICON } from "@/components/CampaignBrowseCard";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Amount } from "@/components/ui/Amount";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ApiError, api, daftarDariRespons } from "@/lib/api";
import { getToken } from "@/lib/auth";

type ProposalStatus =
  | "submitted"
  | "listed"
  | "partially_funded"
  | "rejected"
  | "funded"
  | "failed"
  | "completed";

type ProposalOut = {
  id: string;
  campaign_id: string;
  umkm_id: string;
  business_name: string;
  business_profile: string;
  fund_usage_plan: string;
  business_projection: string;
  requested_amount: number;
  // GET /proposals/{id} (10-api-contract.md) sudah menghitung ini di server
  // dan mengirimkannya publik, untuk proposal listed ke atas, tanpa token.
  // Dikonfirmasi lewat permintaan sungguhan ke backend saat verifikasi
  // browser: menjumlahkan ulang dari daftar pledge di klien (cara lama)
  // hanya berhasil untuk investor/pemilik yang bisa melihat daftar itu, dan
  // membuat bilah funding ikut tersembunyi di balik gerbang login untuk
  // SETIAP pengunjung tanpa akun -- padahal kartu proposal di /jelajah
  // sudah menampilkan progres funding ke publik (05-feature-komunitas.md).
  collected_amount: number;
  // null berarti belum ada foto sampul; nilainya sekaligus kunci cache URL
  // gambarnya (lihat lib/cover.ts).
  cover_updated_at: string | null;
  // Sektor campaign yang menaungi proposal ini, dipakai sebagai lambang
  // sampul cadangan saat fotonya belum ada.
  sector: string | null;
  status: ProposalStatus;
  scoring_status: ScoringStatus;
  lead_investor_id: string | null;
  funded_at: string | null;
  created_at: string;
};

type PledgeOut = {
  id: string;
  proposal_id: string;
  // null, bukan string: dikonfirmasi lewat permintaan sungguhan ke backend
  // saat verifikasi browser (GET .../pledges yang sebenarnya, bukan
  // ditaksir dari dokumen). Backend menganonimkan investor_id pemberi dana
  // lain demi privasi dan mengirim is_lead_investor sebagai gantinya.
  // Sebelumnya tipe ini memakai `string` tanpa null dan kode di bawah
  // memanggil investor_id.slice(-4) langsung, yang meledak dengan
  // "Cannot read properties of null (reading 'slice')" persis di
  // permintaan pertama investor sungguhan membuka proposal berpendana.
  investor_id: string | null;
  amount: number;
  status: string;
  created_at: string;
  is_lead_investor: boolean;
};

type MilestoneOut = {
  id: string;
  seq: number;
  title: string;
  description: string;
  amount: number;
  status: "pending" | "reported" | "disbursed";
};

// Tipe kanonik dari lib/auth.ts, bukan salinan lokal. Salinan yang dulu ada
// di sini mengetik role sebagai `string` biasa, sehingga perbandingan seperti
// currentUser.role !== "investor" tidak pernah diperiksa terhadap daftar peran
// yang sungguh ada, dan salah ketik satu huruf akan lolos tsc diam-diam.

// Proposal dianggap bisa menerima pledge begitu AI meloloskannya (BR-71) dan
// belum penuh. "submitted" (masih dinilai) dan "rejected" tidak termasuk,
// begitu juga "funded"/"completed"/"failed" yang sudah lewat tahap itu.
const STATUS_BISA_DIDANAI: ProposalStatus[] = ["listed", "partially_funded"];

type Keadaan<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "done"; data: T };

// Skor punya satu keadaan lagi di luar Keadaan<T> biasa: "idle", yaitu
// "tidak ada yang perlu diambil karena scoring_status belum done". Sebelum
// ini, keadaan itu disandikan sebagai literal `null` yang sama persis dengan
// "belum diketahui/baru mulai memuat", jadi dua guard yang sama-sama
// memeriksa `score === null` ikut benar bersamaan dan merender LoadingState
// DAN ScorePanel sekaligus, dua live region yang mengumumkan dua hal
// berlawanan di saat yang sama (laporan tinjauan minggu ini). Discriminated
// union ini membuat setiap keadaan punya satu cabang render, bukan dua
// kondisi independen yang bisa kebetulan sama-sama benar.
type ScoreState =
  | { status: "loading" }
  | { status: "idle" }
  | { status: "forbidden" }
  | { status: "error"; message: string }
  | { status: "done"; data: ProposalScore };

function pesanGalat(error: unknown): string {
  return error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.";
}

function formatTanggalSingkat(iso: string): string {
  return new Date(iso).toLocaleDateString("id-ID", { dateStyle: "medium" });
}

type ProposalDetailViewProps = {
  proposalId: string;
};

// Halaman terpenting di Modalink (Fase 11, Task 4): satu-satunya tempat uang
// berpindah dari sisi pengguna. Setiap bagian mengambil datanya sendiri dan
// punya tiga keadaannya sendiri (memuat, galat, isi) secara independen,
// supaya satu bagian gagal (misal komentar) tidak menjatuhkan bagian lain
// (misal bilah funding). Urutan dan pola komposisi tiap <section> mengikuti
// RHYTHM 3 di DESIGN.md: tidak ada dua section berurutan berpola sama.
export function ProposalDetailView({ proposalId }: ProposalDetailViewProps) {
  const [proposal, setProposal] = useState<Keadaan<ProposalOut>>({ status: "loading" });
  const [score, setScore] = useState<ScoreState>({ status: "loading" });
  const [pledges, setPledges] = useState<Keadaan<PledgeOut[]> | { status: "forbidden" }>({
    status: "loading",
  });
  const [milestones, setMilestones] = useState<Keadaan<MilestoneOut[]>>({ status: "loading" });
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [jumlahKomentarBaru, setJumlahKomentarBaru] = useState(0);

  const muatProposal = useCallback(async () => {
    setProposal({ status: "loading" });
    try {
      const data = await api.get<ProposalOut>(`/proposals/${proposalId}`);
      setProposal({ status: "done", data });
    } catch (error) {
      setProposal({ status: "error", message: pesanGalat(error) });
    }
  }, [proposalId]);

  const muatPledges = useCallback(async () => {
    setPledges({ status: "loading" });
    const jalur = `/proposals/${proposalId}/pledges`;
    try {
      const items = daftarDariRespons<PledgeOut>(await api.get(jalur), jalur);
      setPledges({ status: "done", data: items });
    } catch (error) {
      // GET .../pledges (10-api-contract.md:67) hanya untuk investor atau
      // pemilik proposal: pengunjung anonim (401, tidak ada token) dan
      // komunitas (403, peran tidak berhak) selalu ditolak di sini, bukan
      // kasus langka. Sebelumnya keduanya jatuh ke cabang "error" dan
      // menampilkan pesan mentah server ("Token tidak ada.") tepat di
      // tempat bilah funding seharusnya berada -- justru di halaman yang
      // pertama dilihat pengunjung tanpa akun lewat /jelajah (laporan Fase
      // 11 Task 12, ditemukan lewat e2e jalur anonim, bukan diasumsikan).
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        setPledges({ status: "forbidden" });
      } else {
        setPledges({ status: "error", message: pesanGalat(error) });
      }
    }
  }, [proposalId]);

  const muatMilestones = useCallback(async () => {
    setMilestones({ status: "loading" });
    const jalur = `/proposals/${proposalId}/milestones`;
    try {
      const items = daftarDariRespons<MilestoneOut>(await api.get(jalur), jalur);
      setMilestones({ status: "done", data: items });
    } catch (error) {
      setMilestones({ status: "error", message: pesanGalat(error) });
    }
  }, [proposalId]);

  useEffect(() => {
    muatProposal();
    muatPledges();
    muatMilestones();
  }, [muatProposal, muatPledges, muatMilestones]);

  // Identitas pengguna saat ini: dibaca sekali oleh halaman, bukan oleh
  // setiap bagian, karena ia menentukan visibilitas (form pledge, panel
  // skor), bukan konten satu bagian tertentu. Pengunjung anonim (tanpa
  // token) tidak memicu permintaan ini sama sekali: GET /proposals/{id}
  // publik untuk proposal listed ke atas (10-api-contract.md).
  useEffect(() => {
    // getToken() dari lib/auth.ts, bukan localStorage.getItem mentah: itu
    // menolak token kosong dan literal "undefined" (lihat lib/token.ts).
    // Sebelumnya baris ini membaca localStorage langsung, jadi token rusak
    // yang mestinya berarti "anggap belum masuk" malah memicu permintaan
    // /auth/me yang pasti gagal (laporan Fase 11 Task 12).
    if (!getToken()) return;
    api
      .get<CurrentUser>("/auth/me")
      .then((user) => setCurrentUser(user))
      .catch(() => setCurrentUser(null));
  }, []);

  // Skor hanya diminta ke server setelah scoring benar-benar selesai
  // (scoring_status "done"): ProposalOut sudah membawa scoring_status itu
  // sendiri, jadi keadaan menunggu/gagal tidak perlu permintaan tambahan
  // sama sekali, hanya diteruskan langsung ke ScorePanel.
  useEffect(() => {
    if (proposal.status !== "done") return;
    if (proposal.data.scoring_status !== "done") {
      // "idle": tidak ada skor untuk diminta, bukan "belum selesai memuat".
      // ScorePanel sendiri yang menampilkan keadaan menunggu/gagalnya lewat
      // prop scoringStatus di bawah, jadi cabang ini tidak ikut merender
      // LoadingState apa pun.
      setScore({ status: "idle" });
      return;
    }
    setScore({ status: "loading" });
    let dibatalkan = false;
    api
      .get<ProposalScore>(`/proposals/${proposalId}/scoring`)
      .then((data) => {
        if (!dibatalkan) setScore({ status: "done", data });
      })
      .catch((error) => {
        if (dibatalkan) return;
        // 401 (tidak ada token) diperlakukan sama dengan 403 (peran
        // komunitas): keduanya berarti "akun ini tidak berhak melihat skor"
        // (jaga_akses_scoring_milik_sendiri di backend), bukan galat server
        // yang perlu ditampilkan mentah (laporan Fase 11 Task 12).
        if (error instanceof ApiError && (error.status === 403 || error.status === 401)) {
          setScore({ status: "forbidden" });
        } else {
          setScore({ status: "error", message: pesanGalat(error) });
        }
      });
    return () => {
      dibatalkan = true;
    };
  }, [proposal, proposalId]);

  async function nilaiUlang() {
    try {
      await api.post(`/proposals/${proposalId}/rescore`);
      muatProposal();
    } catch {
      // Kegagalan memicu rescore tidak mengubah keadaan yang sudah tampil;
      // pengguna masih melihat tombol yang sama untuk mencoba lagi.
    }
  }

  if (proposal.status === "loading") {
    return <LoadingState label="Memuat proposal" minHeight={480} />;
  }
  if (proposal.status === "error") {
    return <ErrorState message={proposal.message} onRetry={muatProposal} />;
  }

  const data = proposal.data;
  // data.collected_amount, bukan menjumlahkan pledges.data sendiri: lihat
  // komentar pada tipe ProposalOut. pendana (jumlah pendana) tetap hanya
  // diketahui setelah daftar pledge per-investor berhasil dimuat, karena
  // endpoint itu sendiri yang butuh login; undefined (bukan 0) saat belum
  // diketahui, supaya FundingBar tahu membedakan "belum diketahui" dari
  // "diketahui nol".
  const terkumpul = data.collected_amount;
  const pendana = pledges.status === "done" ? pledges.data.length : undefined;
  const sisa = Math.max(data.requested_amount - terkumpul, 0);

  const bisaDidanai = STATUS_BISA_DIDANAI.includes(data.status);
  let alasanPledgeDisembunyikan: string | null = null;
  if (data.status === "funded" || data.status === "completed") {
    alasanPledgeDisembunyikan = "Pendanaan untuk proposal ini sudah tercapai.";
  } else if (data.status === "submitted") {
    alasanPledgeDisembunyikan = "Proposal ini belum terbuka untuk pendanaan karena masih menunggu penilaian AI.";
  } else if (data.status === "rejected" || data.status === "failed") {
    alasanPledgeDisembunyikan = "Proposal ini tidak dibuka untuk pendanaan.";
  } else if (!currentUser) {
    alasanPledgeDisembunyikan = "Masuk sebagai investor untuk memberi pledge.";
  } else if (currentUser.role !== "investor") {
    alasanPledgeDisembunyikan = "Hanya investor yang bisa memberi pledge.";
  }
  const tampilkanFormPledge = bisaDidanai && alasanPledgeDisembunyikan === null;

  const milestoneAktifId =
    milestones.status === "done"
      ? [...milestones.data].sort((a, b) => a.seq - b.seq).find((m) => m.status === "pending")?.id
      : undefined;

  // Begitu dana tercapai, tidak ada lagi keputusan untuk diambil di layar
  // ini: kerangka "dana yang diminta" (masih mengumpulkan) tidak jujur lagi
  // terhadap keadaan sungguhan. Nominal yang memimpin halaman berganti ke
  // total yang terkumpul, yang selalu tersedia begitu proposal sendiri
  // termuat (data.collected_amount publik), tidak perlu menunggu pledges.
  const sudahTuntas = data.status === "funded" || data.status === "completed";
  const tampilkanTotalTerkumpul = sudahTuntas;

  return (
    <div className="mx-auto flex max-w-[76rem] flex-col gap-space-6 px-space-3 py-space-5">
      {/* Banner sampul mendahului judul, bukan diselipkan di samping:
          halaman ini sebelumnya membuka dengan judul di atas ruang kosong
          selebar separuh layar. Rasio 3:1 dipilih supaya ia memberi halaman
          sebuah pembuka tanpa mendorong nominal dan progres pendanaan ke
          bawah lipatan. Usaha yang belum mengunggah foto tetap mendapat
          bentuk lewat lambang sektornya. */}
      <CoverImage
        owner="proposals"
        id={proposalId}
        coverUpdatedAt={data.cover_updated_at}
        nama={data.business_name}
        sectorIcon={data.sector ? SECTOR_ICON[data.sector] : undefined}
        ukuran="banner"
      />

      <header className="flex flex-wrap items-center justify-between gap-space-2 border-b border-line pb-space-3">
        <h1 className="text-page font-display text-ink">{data.business_name}</h1>
        <StatusBadge status={data.status} />
      </header>

      {/* Kontrol unggah hanya untuk pemilik proposalnya sendiri. Server juga
          menolak orang lain (404, lihat api/v1/covers.py); yang di sini
          supaya kontrolnya tidak ditawarkan kepada orang yang pasti ditolak,
          kesalahan yang sama yang baru diperbaiki pada tombol dukungan. */}
      {currentUser?.id === data.umkm_id && (
        <section
          data-pola="kelola-sampul"
          className="rounded-panel border border-line bg-panel px-space-4 py-space-4"
        >
          <h2 className="mb-space-3 text-card-title font-semibold text-ink">Foto sampul</h2>
          <CoverUpload
            owner="proposals"
            id={proposalId}
            nama={data.business_name}
            coverUpdatedAt={data.cover_updated_at}
            sectorIcon={data.sector ? SECTOR_ICON[data.sector] : undefined}
            onBerubah={muatProposal}
          />
        </section>
      )}

      {/* 1. Nominal utama: motif identitas DESIGN.md, satu-satunya pemakaian
          size="hero" di halaman ini. Lebar penuh, rata kiri, satu kolom,
          tanpa rule. Ini yang dibaca lebih dulu: produk ini tentang uang
          yang berpindah. Begitu dana tuntas, nominal yang memimpin berganti
          dari "diminta" menjadi "terkumpul" karena tidak ada lagi keputusan
          pendanaan yang bisa diambil di sini. */}
      <section data-pola="sorotan-nominal" className="flex flex-col gap-space-1 break-words">
        {/* break-words (overflow-wrap: break-word, diwariskan ke elemen
            Amount di dalamnya): di 320px, "Rp20.000.000" pada ukuran hero
            (clamp 3rem-5rem, dasarnya terkunci di 3rem/48px pada layar
            sesempit ini) adalah satu "kata" rupiah tanpa spasi yang lebih
            lebar daripada layarnya, dan tanpa ini meluber ke kanan (terbukti
            lewat pengukuran scrollWidth > clientWidth di browser). Ini
            properti yang diwariskan, bukan menyentuh Amount.tsx yang bukan
            milik berkas ini. */}
        {tampilkanTotalTerkumpul ? (
          <Amount label="Total terkumpul, pendanaan tercapai" amount={terkumpul} size="hero" />
        ) : (
          <Amount label="Dana yang diminta" amount={data.requested_amount} size="hero" />
        )}
      </section>

      {/* 2. Bilah funding dan daftar pemberi dana. Lebar penuh, rata kiri,
          satu kolom, DENGAN rule horizontal memisahkan bilah dari daftar
          pendana. Beda dari section 1 lewat kehadiran rule dan isi yang
          lebih padat (bilah + daftar), bukan hanya label berbeda.
          FundingBar sendiri dirender tanpa syarat: terkumpul dan target
          datang dari proposal yang publik. Yang tetap digerbang login hanya
          daftar pendana satu per satu, karena GET .../pledges itulah yang
          butuh token (bukti lewat verifikasi browser terhadap backend
          sungguhan, bukan ditaksir dari dokumen). */}
      <section data-pola="bilah-lebar-penuh" className="flex flex-col gap-space-4 border-t border-line pt-space-4">
        <h2 className="text-section font-display text-ink">Progres pendanaan</h2>
        <FundingBar terkumpul={terkumpul} target={data.requested_amount} pendana={pendana} />
        {pledges.status === "loading" && <LoadingState label="Memuat daftar pendana" minHeight={80} />}
        {pledges.status === "forbidden" && (
          <p className="max-w-measure border-t border-line pt-space-3 text-body text-muted">
            Masuk sebagai investor, atau sebagai UMKM pemilik proposal ini, untuk melihat daftar
            pendana satu per satu.
          </p>
        )}
        {pledges.status === "error" && <ErrorState message={pledges.message} onRetry={muatPledges} />}
        {pledges.status === "done" && pledges.data.length > 0 && (
          <ul className="flex flex-col gap-space-2 border-t border-line pt-space-3">
            {/* Pendana ke-N berdasarkan urutan waktu, bukan investor_id: GET
                .../pledges (dikonfirmasi lewat permintaan sungguhan ke
                backend) mengirim investor_id = null untuk menganonimkan
                pemberi dana lain, dan is_lead_investor sebagai gantinya
                untuk menandai investor utama. Tidak ada field lagi yang bisa
                dipakai membedakan satu pendana dari pendana lain selain
                urutan ini. */}
            {[...pledges.data]
              .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
              .map((pledge, index) => (
                <li key={pledge.id} className="flex items-center justify-between gap-space-3 text-body text-ink">
                  <span className="flex items-center gap-space-2">
                    Pendana ke-{index + 1}
                    {pledge.is_lead_investor && (
                      // accent-2 sebagai penanda (DESIGN.md: "label kategori,
                      // sorotan angka pendukung"), bukan aksi: investor utama
                      // adalah satu-satunya pemberi dana dengan hak menyetujui
                      // pencairan milestone (BR-44), jadi sorotan ini menandai
                      // keputusan nyata, bukan dekorasi.
                      <span className="rounded-sm bg-accent-2 px-space-2 py-space-1 text-label font-semibold text-on-accent">
                        investor utama
                      </span>
                    )}
                  </span>
                  <Amount label="" amount={pledge.amount} size="medium" />
                </li>
              ))}
          </ul>
        )}
      </section>

      {/* 3. Cerita usaha dan rencana dana: teks naratif, lebar dibatasi
          max-w-measure, rata kiri, satu kolom, tanpa rule. Beda dari
          section 2 lewat lebar (terbatas, bukan penuh). Satu judul section
          (text-section) membuka bagian ini; ketiga sub-bagian di dalamnya
          memakai ukuran judul kartu (text-card-title), bukan judul section
          lagi, supaya tiga judul raksasa tidak berbaris tanpa jeda. */}
      <section data-pola="naratif-kiri" className="flex max-w-measure flex-col gap-space-4">
        <h2 className="text-section font-display text-ink">Cerita usaha</h2>
        <div className="flex flex-col gap-space-1">
          <h3 className="text-card-title font-semibold text-ink">Profil usaha</h3>
          <p className="text-body text-ink">{data.business_profile}</p>
        </div>
        <div className="flex flex-col gap-space-1">
          <h3 className="text-card-title font-semibold text-ink">Rencana pemakaian dana</h3>
          <p className="text-body text-ink">{data.fund_usage_plan}</p>
        </div>
        <div className="flex flex-col gap-space-1">
          <h3 className="text-card-title font-semibold text-ink">Proyeksi usaha</h3>
          <p className="text-body text-ink">{data.business_projection}</p>
        </div>
      </section>

      {/* 4. Panel skor AI: lebar penuh, dua kolom asimetris SUNGGUHAN lewat
          grid (panel skor 2fr di kiri, catatan "yang dinilai AI" 1fr di
          kanan yang menyatu jadi satu kolom di mobile). Review browser
          sebelumnya menemukan label ini terpasang di atas flex-col satu
          kolom biasa, dengan class yang identik dengan section 6
          (daftar-bernomor): keduanya "flex flex-col gap-space-3". Grid di
          sini membuat labelnya jujur, dan membedakannya nyata dari section
          3 (lebar terbatas, satu kolom) maupun section 6 (flex, bukan
          grid). */}
      <section
        data-pola="dua-kolom-asimetris"
        className="grid grid-cols-1 gap-space-4 border-t border-line pt-space-4 lg:grid-cols-[2fr_1fr]"
      >
        <div className="flex flex-col gap-space-3">
          <h2 className="text-section font-display text-ink">Penilaian AI</h2>
          {score.status === "loading" && <LoadingState label="Memuat hasil penilaian" minHeight={160} />}
          {score.status === "forbidden" && (
            <p className="max-w-measure text-body text-muted">
              Panel skor hanya terlihat oleh investor dan pemilik proposal.
            </p>
          )}
          {score.status === "error" && <ErrorState message={score.message} onRetry={muatProposal} />}
          {score.status === "done" && <ScorePanel score={score.data} />}
          {score.status === "idle" && (
            <ScorePanel score={null} scoringStatus={data.scoring_status} onRescore={nilaiUlang} />
          )}
        </div>
        <aside className="flex flex-col gap-space-2 border-t border-line pt-space-4 lg:border-l lg:border-t-0 lg:pl-space-4 lg:pt-0">
          <p className="text-label font-medium text-muted">Yang dinilai AI</p>
          <ul className="flex flex-col gap-space-2 text-body text-ink">
            <li>Kecocokan sektor dan kebutuhan dana dengan kriteria campaign.</li>
            <li>Kelengkapan dan konsistensi isian proposal.</li>
            <li>Potensi dampak dibanding skala usaha yang diajukan.</li>
          </ul>
        </aside>
      </section>

      {/* 5. Form pledge: lebar dibatasi, rata TENGAH, satu kolom, tanpa
          rule, dibungkus kartu. Beda dari section 4 lewat lebar (terbatas)
          dan rata tengah (section 4 rata kiri). key={sisa} pada PledgeForm:
          tanpa key, form menyimpan sisa dana lewat useState(sisa) sekali di
          mount dan tidak pernah sinkron lagi, jadi setelah pledge sukses
          (sisa yang sungguhan mengecil) form tetap menunjukkan sisa lama dan
          membiarkan pengguna mengirim nominal yang pasti ditolak server;
          satu-satunya jalan form tahu sisa yang benar sebelumnya adalah lewat
          GAGAL dulu (409). key yang berubah memaksa PledgeForm remount
          dengan sisa terbaru begitu pledges/proposal selesai dimuat ulang. */}
      <section data-pola="kartu-tengah" className="flex flex-col items-center">
        <div className="w-full max-w-[28rem] rounded-panel border border-line bg-panel px-space-4 py-space-5 text-center">
          <h2 className="text-card-title font-semibold text-ink">Danai proposal ini</h2>
          {tampilkanFormPledge ? (
            <div className="mt-space-3 text-left">
              <PledgeForm
                key={sisa}
                proposalId={proposalId}
                sisa={sisa}
                onSukses={() => { muatPledges(); muatProposal(); }}
              />
            </div>
          ) : (
            <p className="mt-space-2 text-body text-muted">{alasanPledgeDisembunyikan}</p>
          )}
        </div>
      </section>

      {/* 6. Milestone yang direncanakan: lebar penuh, rata kiri, satu kolom,
          daftar bernomor DENGAN rule horizontal antar tahap. Beda dari
          section 5 lewat lebar (penuh) dan rata kiri (section 5 tengah). */}
      <section data-pola="daftar-bernomor" className="flex flex-col gap-space-3">
        <h2 className="text-section font-display text-ink">Milestone yang direncanakan</h2>
        {milestones.status === "loading" && <LoadingState label="Memuat milestone" minHeight={160} />}
        {milestones.status === "error" && <ErrorState message={milestones.message} onRetry={muatMilestones} />}
        {milestones.status === "done" && (
          <ol className="flex flex-col">
            {[...milestones.data]
              .sort((a, b) => a.seq - b.seq)
              .map((milestone, index) => (
                <li
                  key={milestone.id}
                  // Penanda tahap aktif cukup lewat badge "Tahap aktif" di
                  // bawah, bukan ditambah border kiri --accent juga. Versi
                  // sebelumnya memasang keduanya sekaligus (border-l-4
                  // border-l-accent DAN badge aksen), menghabiskan dua dari
                  // tiga jatah --accent di layar ini untuk satu ide yang
                  // sama, dan DESIGN.md sudah mengecualikan aksen dari
                  // border kartu secara eksplisit. Pilih satu: badge.
                  className="flex flex-wrap items-baseline justify-between gap-space-2 border-t border-line py-space-3 first:border-t-0 first:pt-0"
                >
                  <div className="flex items-baseline gap-space-2">
                    <span className="tabular text-label font-medium text-muted">
                      Tahap {index + 1}
                    </span>
                    <p className="text-base font-semibold leading-[1.6] text-ink">{milestone.title}</p>
                    {milestone.id === milestoneAktifId && (
                      <span className="rounded-sm bg-accent px-space-2 py-space-1 text-label font-semibold text-on-accent">
                        Tahap aktif
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-space-3">
                    <Amount label="" amount={milestone.amount} size="medium" />
                    <StatusBadge status={milestone.status} />
                    {/* Satu-satunya jalan masuk di produk ini ke
                        /umkm/milestone/[id]/lapor: halaman itu tidak punya
                        endpoint untuk mengambil satu milestone lewat idnya
                        sendiri, jadi ia bergantung pada query ?proposal=
                        (lihat app/umkm/milestone/[id]/lapor/page.tsx).
                        Sebelum tautan ini ada, halaman tersebut hanya bisa
                        dicapai dengan mengetik URL manual -- ditemukan lewat
                        e2e Fase 11 Task 12, bukan diasumsikan. Tahap 1 tidak
                        pernah tampil di sini (BR-41: tidak perlu laporan). */}
                    {currentUser?.id === data.umkm_id &&
                      milestone.id === milestoneAktifId &&
                      milestone.status === "pending" &&
                      milestone.seq > 1 && (
                        <Link
                          href={`/umkm/milestone/${milestone.id}/lapor?proposal=${proposalId}`}
                          className="text-base font-medium text-ink underline"
                        >
                          Lapor progres
                        </Link>
                      )}
                  </div>
                </li>
              ))}
          </ol>
        )}
      </section>

      {/* 7. Komentar dan vote: lebar dibatasi max-w-measure, rata kiri,
          satu kolom, tanpa rule. Beda dari section 6 lewat lebar
          (terbatas vs penuh) dan tanpa rule (section 6 pakai rule). gap-space-3,
          bukan gap-space-4 seperti section 3: CommentList dan CommentForm
          sudah membawa jarak internalnya sendiri, dan class wrapper yang
          identik dengan section 3 ("naratif-kiri") persis pola yang
          ditemukan audit browser minggu ini di dua label berbeda. */}
      <section data-pola="utas-komentar" className="flex max-w-measure flex-col gap-space-3">
        <h2 className="text-section font-display text-ink">Komentar</h2>
        {/* key berubah memaksa CommentList remount lalu memuat ulang
            dirinya sendiri setelah komentar baru terkirim. CommentForm dan
            CommentList sengaja tetap dua komponen independen (masing-masing
            mengambil datanya sendiri), jadi ini satu-satunya titik
            penghubung di antara keduanya, dan letaknya di sini, bukan di
            dalam salah satu komponen itu. */}
        <CommentList
          key={jumlahKomentarBaru}
          proposalId={proposalId}
          currentRole={currentUser?.role ?? null}
          currentUserId={currentUser?.id ?? null}
        />
        <div id="form-komentar">
          <CommentForm proposalId={proposalId} onKirim={() => setJumlahKomentarBaru((n) => n + 1)} />
        </div>
      </section>

      <p className="text-label text-muted">
        Diajukan pada {formatTanggalSingkat(data.created_at)}.
      </p>
    </div>
  );
}
