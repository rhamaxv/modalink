"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { CommentForm } from "@/components/CommentForm";
import { CommentList } from "@/components/CommentList";
import { FundingBar } from "@/components/FundingBar";
import { PledgeForm } from "@/components/PledgeForm";
import { ScorePanel, type ProposalScore, type ScoringStatus } from "@/components/ScorePanel";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Nominal } from "@/components/ui/Nominal";
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
  status: ProposalStatus;
  scoring_status: ScoringStatus;
  lead_investor_id: string | null;
  funded_at: string | null;
  created_at: string;
};

type PledgeOut = {
  id: string;
  proposal_id: string;
  investor_id: string;
  amount: number;
  status: string;
  created_at: string;
};

type MilestoneOut = {
  id: string;
  seq: number;
  title: string;
  description: string;
  amount: number;
  status: "pending" | "reported" | "disbursed";
};

type CurrentUser = {
  id: string;
  name: string;
  role: string;
};

// Proposal dianggap bisa menerima pledge begitu AI meloloskannya (BR-71) dan
// belum penuh. "submitted" (masih dinilai) dan "rejected" tidak termasuk,
// begitu juga "funded"/"completed"/"failed" yang sudah lewat tahap itu.
const STATUS_BISA_DIDANAI: ProposalStatus[] = ["listed", "partially_funded"];

type Keadaan<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "done"; data: T };

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
  const [score, setScore] = useState<Keadaan<ProposalScore> | { status: "forbidden" } | null>(null);
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
      setScore(null);
      return;
    }
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
  const terkumpul =
    pledges.status === "done" ? pledges.data.reduce((total, p) => total + p.amount, 0) : 0;
  const pendana = pledges.status === "done" ? pledges.data.length : 0;
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

  return (
    <div className="mx-auto flex max-w-[76rem] flex-col gap-space-6 px-space-3 py-space-5">
      <header className="flex flex-wrap items-center justify-between gap-space-2 border-b border-line pb-space-3">
        <h1 className="text-[clamp(1.75rem,4vw,2.5rem)] font-semibold leading-tight text-ink">
          {data.business_name}
        </h1>
        <StatusBadge status={data.status} />
      </header>

      {/* 1. Nominal diminta: motif identitas DESIGN.md. Lebar penuh, rata kiri,
          satu kolom, tanpa rule. Ini yang dibaca lebih dulu: produk ini
          tentang uang yang berpindah. */}
      <section data-pola="sorotan-nominal" className="flex flex-col gap-space-1">
        <Nominal label="Dana yang diminta" nominal={data.requested_amount} ukuran="besar" />
      </section>

      {/* 2. Bilah funding dan daftar pemberi dana. Lebar penuh, rata kiri,
          satu kolom, DENGAN rule horizontal memisahkan bilah dari daftar
          pendana. Beda dari section 1 lewat kehadiran rule dan isi yang
          lebih padat (bilah + daftar), bukan hanya label berbeda. */}
      <section data-pola="bilah-lebar-penuh" className="flex flex-col gap-space-4 border-t border-line pt-space-4">
        {pledges.status === "loading" && <LoadingState label="Memuat progres funding" minHeight={120} />}
        {pledges.status === "forbidden" && (
          <p className="max-w-measure text-base leading-[1.6] text-muted">
            Masuk sebagai investor, atau sebagai UMKM pemilik proposal ini, untuk melihat progres
            pendanaan dan daftar pendana.
          </p>
        )}
        {pledges.status === "error" && <ErrorState message={pledges.message} onRetry={muatPledges} />}
        {pledges.status === "done" && (
          <>
            <FundingBar terkumpul={terkumpul} target={data.requested_amount} pendana={pendana} />
            {pledges.data.length > 0 && (
              <ul className="flex flex-col gap-space-2 border-t border-line pt-space-3">
                {pledges.data.map((pledge) => (
                  <li key={pledge.id} className="flex items-center justify-between gap-space-3 text-base leading-[1.6] text-ink">
                    <span>
                      Investor &hellip;{pledge.investor_id.slice(-4)}
                      {pledge.investor_id === data.lead_investor_id && (
                        <span className="ml-space-2 text-[0.8125rem] font-medium text-muted">(investor utama)</span>
                      )}
                    </span>
                    <Nominal label="" nominal={pledge.amount} ukuran="sedang" />
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>

      {/* 3. Cerita usaha dan rencana dana: teks naratif, lebar dibatasi
          max-w-measure, rata kiri, satu kolom, tanpa rule. Beda dari
          section 2 lewat lebar (terbatas, bukan penuh). */}
      <section data-pola="naratif-kiri" className="flex max-w-measure flex-col gap-space-4">
        <div className="flex flex-col gap-space-1">
          <h2 className="text-[1.75rem] font-semibold text-ink">Profil usaha</h2>
          <p className="text-base leading-[1.6] text-ink">{data.business_profile}</p>
        </div>
        <div className="flex flex-col gap-space-1">
          <h2 className="text-[1.75rem] font-semibold text-ink">Rencana pemakaian dana</h2>
          <p className="text-base leading-[1.6] text-ink">{data.fund_usage_plan}</p>
        </div>
        <div className="flex flex-col gap-space-1">
          <h2 className="text-[1.75rem] font-semibold text-ink">Proyeksi usaha</h2>
          <p className="text-base leading-[1.6] text-ink">{data.business_projection}</p>
        </div>
      </section>

      {/* 4. Panel skor AI: lebar penuh, dua kolom asimetris (panel skor di
          kiri lebih lebar, keterangan singkat di kanan tidak ada di sini
          karena ScorePanel sendiri sudah menata brief di dalamnya; variasi
          nyata dari section 3 datang dari lebar penuh vs terbatas, dan dari
          grid 3 kolom komponen skor vs satu kolom paragraf). */}
      <section data-pola="dua-kolom-asimetris" className="flex flex-col gap-space-3">
        <h2 className="text-[1.75rem] font-semibold text-ink">Penilaian AI</h2>
        {score === null && <LoadingState label="Memuat hasil penilaian" minHeight={160} />}
        {score?.status === "forbidden" && (
          <p className="max-w-measure text-base leading-[1.6] text-muted">
            Panel skor hanya terlihat oleh investor dan pemilik proposal.
          </p>
        )}
        {score?.status === "error" && <ErrorState message={score.message} onRetry={muatProposal} />}
        {score?.status === "done" && <ScorePanel score={score.data} />}
        {score === null && proposal.status === "done" && data.scoring_status !== "done" && (
          <ScorePanel score={null} scoringStatus={data.scoring_status} onRescore={nilaiUlang} />
        )}
      </section>

      {/* 5. Form pledge: lebar dibatasi, rata TENGAH, satu kolom, tanpa
          rule, dibungkus kartu. Beda dari section 4 lewat lebar (terbatas)
          dan rata tengah (section 4 rata kiri). */}
      <section data-pola="kartu-tengah" className="flex flex-col items-center">
        <div className="w-full max-w-[28rem] rounded-panel border border-line bg-surface px-space-4 py-space-5 text-center">
          <h2 className="text-[1.125rem] font-semibold text-ink">Danai proposal ini</h2>
          {tampilkanFormPledge ? (
            <div className="mt-space-3 text-left">
              <PledgeForm proposalId={proposalId} sisa={sisa} onSukses={() => { muatPledges(); muatProposal(); }} />
            </div>
          ) : (
            <p className="mt-space-2 text-base leading-[1.6] text-muted">{alasanPledgeDisembunyikan}</p>
          )}
        </div>
      </section>

      {/* 6. Milestone yang direncanakan: lebar penuh, rata kiri, satu kolom,
          daftar bernomor DENGAN rule horizontal antar tahap. Beda dari
          section 5 lewat lebar (penuh) dan rata kiri (section 5 tengah). */}
      <section data-pola="daftar-bernomor" className="flex flex-col gap-space-3">
        <h2 className="text-[1.75rem] font-semibold text-ink">Milestone yang direncanakan</h2>
        {milestones.status === "loading" && <LoadingState label="Memuat milestone" minHeight={160} />}
        {milestones.status === "error" && <ErrorState message={milestones.message} onRetry={muatMilestones} />}
        {milestones.status === "done" && (
          <ol className="flex flex-col">
            {[...milestones.data]
              .sort((a, b) => a.seq - b.seq)
              .map((milestone, index) => (
                <li
                  key={milestone.id}
                  className={`flex flex-wrap items-baseline justify-between gap-space-2 border-t border-line py-space-3 first:border-t-0 first:pt-0 ${
                    milestone.id === milestoneAktifId ? "border-l-4 border-l-accent pl-space-3" : ""
                  }`}
                >
                  <div className="flex items-baseline gap-space-2">
                    <span className="tabular text-[0.8125rem] font-medium text-muted">
                      Tahap {index + 1}
                    </span>
                    <p className="text-base font-semibold leading-[1.6] text-ink">{milestone.title}</p>
                    {milestone.id === milestoneAktifId && (
                      <span className="rounded-sm bg-accent px-space-2 py-space-1 text-[0.8125rem] font-semibold text-on-accent">
                        Tahap aktif
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-space-3">
                    <Nominal label="" nominal={milestone.amount} ukuran="sedang" />
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
          (terbatas vs penuh) dan tanpa rule (section 6 pakai rule). */}
      <section data-pola="utas-komentar" className="flex max-w-measure flex-col gap-space-4">
        <h2 className="text-[1.75rem] font-semibold text-ink">Komentar</h2>
        {/* key berubah memaksa CommentList remount lalu memuat ulang
            dirinya sendiri setelah komentar baru terkirim. CommentForm dan
            CommentList sengaja tetap dua komponen independen (masing-masing
            mengambil datanya sendiri), jadi ini satu-satunya titik
            penghubung di antara keduanya, dan letaknya di sini, bukan di
            dalam salah satu komponen itu. */}
        <CommentList
          key={jumlahKomentarBaru}
          proposalId={proposalId}
          currentUserId={currentUser?.id ?? null}
        />
        <div id="form-komentar">
          <CommentForm proposalId={proposalId} onKirim={() => setJumlahKomentarBaru((n) => n + 1)} />
        </div>
      </section>

      <p className="text-[0.8125rem] text-muted">
        Diajukan pada {formatTanggalSingkat(data.created_at)}.
      </p>
    </div>
  );
}
