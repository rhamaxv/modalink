"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { EmptyState, ErrorState, LoadingState, Nominal } from "@/components/ui";
// StatusBadge belum ada di barrel components/ui/index.ts (fase 10), jadi
// diimpor langsung dari filenya tanpa mengubah barrel itu sendiri.
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ApiError, api } from "@/lib/api";

type ProposalMine = {
  id: string;
  business_name: string;
  requested_amount: number;
  status: string;
  scoring_status: "pending" | "processing" | "done" | "failed";
};

type Muatan =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "siap"; proposals: ProposalMine[] };

// Satu keputusan di layar ini: apa yang harus dikerjakan sekarang (DESIGN.md).
// Karena itu, proposal yang penilaiannya gagal secara teknis tampil duluan,
// di atas ringkasan apa pun, bukan terkubur di tabel status.
export default function UmkmBeranda() {
  const router = useRouter();
  const [muatan, setMuatan] = useState<Muatan>({ status: "loading" });
  const [rescoring, setRescoring] = useState<Record<string, boolean>>({});
  const [rescoreError, setRescoreError] = useState<Record<string, string>>({});

  const muat = useCallback(async () => {
    setMuatan({ status: "loading" });
    try {
      const proposals = await api.get<ProposalMine[]>("/proposals/mine");
      setMuatan({ status: "siap", proposals });
    } catch (error) {
      setMuatan({
        status: "error",
        message: error instanceof ApiError ? error.message : "Gagal memuat proposal Anda.",
      });
    }
  }, []);

  useEffect(() => {
    muat();
  }, [muat]);

  async function nilaiUlang(id: string) {
    setRescoring((s) => ({ ...s, [id]: true }));
    setRescoreError((s) => ({ ...s, [id]: "" }));
    try {
      await api.post(`/proposals/${id}/rescore`);
      await muat();
    } catch (error) {
      setRescoreError((s) => ({
        ...s,
        [id]: error instanceof ApiError ? error.message : "Gagal meminta nilai ulang. Coba lagi sebentar lagi.",
      }));
    } finally {
      setRescoring((s) => ({ ...s, [id]: false }));
    }
  }

  if (muatan.status === "loading") {
    return <LoadingState label="Memuat proposal Anda" minHeight={240} />;
  }
  if (muatan.status === "error") {
    return <ErrorState message={muatan.message} onRetry={muat} />;
  }
  if (muatan.proposals.length === 0) {
    return (
      <EmptyState
        reason="Anda belum pernah mengajukan proposal. Ajukan proposal pertama Anda untuk mulai dinilai AI dan dibuka untuk pendanaan."
        action={{
          label: "Ajukan proposal baru",
          onClick: () => router.push("/umkm/proposal/baru"),
        }}
      />
    );
  }

  const perluTindakan = muatan.proposals.filter((p) => p.scoring_status === "failed");
  const lainnya = muatan.proposals.filter((p) => p.scoring_status !== "failed");

  return (
    <div className="mx-auto flex flex-col gap-space-6 px-space-3 py-space-6">
      <div className="max-w-measure">
        <h1 className="text-[clamp(2.5rem,5vw,4rem)] font-semibold text-ink">Proposal Anda</h1>
      </div>

      {perluTindakan.length > 0 && (
        <section data-pola="daftar-bernomor">
          <h2 className="text-[1.125rem] font-semibold text-ink">Perlu tindakan Anda sekarang</h2>
          <div className="mt-space-3 flex flex-col gap-space-3">
            {perluTindakan.map((p) => (
              <div
                key={p.id}
                data-testid="kartu-proposal"
                className="rounded-card border border-warn bg-surface p-space-4"
              >
                <div className="flex items-center justify-between gap-space-3">
                  <p className="text-[1.125rem] font-semibold text-ink">{p.business_name}</p>
                  <StatusBadge status={p.status} />
                </div>
                {/* D-09: kegagalan mesin skor bukan keputusan atas usaha ini.
                    Kalimat di bawah sengaja tidak memuat kata yang berarti
                    "ditolak" atau "tidak lolos". */}
                <p className="mt-space-2 text-base leading-[1.6] text-ink">
                  Penilaian otomatis belum berhasil dilakukan karena gangguan teknis pada mesin
                  penilai. Ini bukan keputusan atas usaha Anda. Coba nilai ulang.
                </p>
                {rescoreError[p.id] && (
                  <p role="alert" className="mt-space-2 text-[0.8125rem] text-danger">
                    {rescoreError[p.id]}
                  </p>
                )}
                <button
                  type="button"
                  onClick={() => nilaiUlang(p.id)}
                  disabled={rescoring[p.id]}
                  aria-busy={rescoring[p.id]}
                  className="mt-space-3 min-h-[44px] rounded-sm border border-ink px-space-3 py-space-2 text-base leading-[1.6] font-semibold text-ink disabled:border-line disabled:text-muted"
                >
                  Nilai ulang
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      <section data-pola="tabel-padat">
        <h2 className="text-[1.125rem] font-semibold text-ink">Semua proposal</h2>
        <div className="mt-space-3 flex flex-col gap-space-3">
          {lainnya.map((p) => (
            <ProposalCard key={p.id} proposal={p} />
          ))}
        </div>
      </section>
    </div>
  );
}

function ProposalCard({ proposal }: { proposal: ProposalMine }) {
  return (
    <div data-testid="kartu-proposal" className="rounded-card border border-line bg-surface p-space-4">
      <div className="flex items-center justify-between gap-space-3">
        <p className="text-[1.125rem] font-semibold text-ink">{proposal.business_name}</p>
        <StatusBadge status={proposal.status} />
      </div>
      <div className="mt-space-2">
        <Nominal label="Dana yang diminta" nominal={proposal.requested_amount} ukuran="sedang" />
      </div>
      {proposal.scoring_status === "done" && <ScoreSummary proposalId={proposal.id} />}
    </div>
  );
}

type RedFlag = { code: string; severity: "info" | "warning" | "critical"; message: string; evidence: string };
type ScoreResult = {
  fit_score: number;
  data_quality_score: number;
  impact_score: number;
  red_flags: RedFlag[];
  brief: { strengths: string[]; risks: string[]; recommendation: string };
};

const SEVERITAS: Record<RedFlag["severity"], { label: string; kelas: string }> = {
  critical: { label: "Kritis", kelas: "text-danger" },
  warning: { label: "Peringatan", kelas: "text-warn" },
  info: { label: "Info", kelas: "text-muted" },
};

// Pengganti sementara panel skor: PanelSkor (Task 1, stream A) belum ada di
// worktree ini karena dikerjakan paralel. Tampilan ini memenuhi kontrak yang
// sama (skor terurai, red flag berikut kutipannya, brief) dan sebaiknya
// ditukar ke PanelSkor sungguhan saat digabung kembali ke main.
function ScoreSummary({ proposalId }: { proposalId: string }) {
  const [percobaan, setPercobaan] = useState(0);
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "siap"; data: ScoreResult }
  >({ status: "loading" });

  useEffect(() => {
    let batal = false;
    setState({ status: "loading" });
    (async () => {
      try {
        const data = await api.get<ScoreResult>(`/proposals/${proposalId}/scoring`);
        if (!batal) setState({ status: "siap", data });
      } catch (error) {
        if (!batal) {
          setState({
            status: "error",
            message: error instanceof ApiError ? error.message : "Gagal memuat skor.",
          });
        }
      }
    })();
    return () => {
      batal = true;
    };
  }, [proposalId, percobaan]);

  if (state.status === "loading") {
    return <LoadingState label="Memuat skor" minHeight={60} />;
  }
  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={() => setPercobaan((n) => n + 1)} />;
  }

  const { fit_score, data_quality_score, impact_score, red_flags, brief } = state.data;
  const total = fit_score + data_quality_score + impact_score;

  return (
    <div className="mt-space-3 border-t border-line pt-space-3">
      <p className="text-[0.8125rem] font-medium text-muted">Skor penilaian AI</p>
      <p className="tabular text-[1.75rem] font-semibold text-ink">{total}</p>
      <dl className="mt-space-2 grid grid-cols-3 gap-space-3 text-[0.8125rem]">
        <div>
          <dt className="text-muted">Kecocokan</dt>
          <dd className="tabular font-medium text-ink">{fit_score}/40</dd>
        </div>
        <div>
          <dt className="text-muted">Kualitas data</dt>
          <dd className="tabular font-medium text-ink">{data_quality_score}/30</dd>
        </div>
        <div>
          <dt className="text-muted">Potensi dampak</dt>
          <dd className="tabular font-medium text-ink">{impact_score}/30</dd>
        </div>
      </dl>

      {red_flags.length > 0 && (
        <div className="mt-space-3">
          <p className="text-[0.8125rem] font-medium text-muted">Red flag</p>
          <ul className="mt-space-1 flex flex-col gap-space-2">
            {red_flags.map((flag) => (
              <li key={flag.code} className="text-base leading-[1.6] text-ink">
                <span className={`font-medium ${SEVERITAS[flag.severity].kelas}`}>
                  {SEVERITAS[flag.severity].label}:
                </span>{" "}
                {flag.message}
                <span className="block text-[0.8125rem] text-muted">&quot;{flag.evidence}&quot;</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-space-3">
        <p className="text-[0.8125rem] font-medium text-muted">Rekomendasi</p>
        <p className="text-base leading-[1.6] text-ink">{brief.recommendation}</p>
      </div>
    </div>
  );
}
