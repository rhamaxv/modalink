"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Amount, EmptyState, ErrorState, LoadingState } from "@/components/ui";
// StatusBadge belum ada di barrel components/ui/index.ts (fase 10), jadi
// diimpor langsung dari filenya tanpa mengubah barrel itu sendiri.
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ApiError, api } from "@/lib/api";
import { ScorePanel, type ProposalScore } from "@/components/ScorePanel";

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
                <div className="flex flex-wrap items-center justify-between gap-space-3">
                  <p className="min-w-0 text-[1.125rem] font-semibold text-ink">{p.business_name}</p>
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
      <div className="flex flex-wrap items-center justify-between gap-space-3">
        <p className="min-w-0 text-[1.125rem] font-semibold text-ink">{proposal.business_name}</p>
        <StatusBadge status={proposal.status} />
      </div>
      <div className="mt-space-2">
        <Amount label="Dana yang diminta" amount={proposal.requested_amount} size="medium" />
      </div>
      {proposal.scoring_status === "done" && <ScoreSummary proposalId={proposal.id} />}
      {/* Tanpa tautan ini, dashboard UMKM tidak punya jalan sama sekali ke
          /proposal/[id] -- satu-satunya halaman tempat pledge, milestone,
          dan tautan "Lapor progres" berada. Ditemukan lewat e2e Fase 11
          Task 12: card ini dulu hanya menampilkan ringkasan, tidak pernah
          mengarahkan ke mana pun (laporan Fase 11 Task 12). */}
      <Link
        href={`/proposal/${proposal.id}`}
        className="mt-space-3 inline-block text-base font-medium text-ink underline"
      >
        Baca proposal
      </Link>
    </div>
  );
}

// Fetch per proposal tinggal di sini, tampilannya diserahkan ke ScorePanel:
// panel skor kedua akan menyimpang dari yang pertama begitu salah satunya diubah.
function ScoreSummary({ proposalId }: { proposalId: string }) {
  const [percobaan, setPercobaan] = useState(0);
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "siap"; data: ProposalScore }
  >({ status: "loading" });

  useEffect(() => {
    let batal = false;
    setState({ status: "loading" });
    (async () => {
      try {
        const data = await api.get<ProposalScore>(`/proposals/${proposalId}/scoring`);
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

  return (
    <div className="mt-space-3 border-t border-line pt-space-3">
      <ScorePanel score={state.data} />
    </div>
  );
}
