"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
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
// di atas ringkasan apa pun, bukan terkubur di tabel status. H1 dirender
// sebelum cabang status data mana pun, dan loading/error/kosong dirender di
// DALAM pembungkus lebar yang sama dengan isi sungguhan, bukan sebelumnya:
// versi sebelumnya mengembalikan ketiga keadaan itu sebelum pembungkus,
// jadi kotaknya rapat ke tepi layar di 375px dan judul halaman baru muncul
// (lalu memindahkan seluruh layout) begitu data datang.
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

  const perluTindakan = muatan.status === "siap" ? muatan.proposals.filter((p) => p.scoring_status === "failed") : [];
  const lainnya = muatan.status === "siap" ? muatan.proposals.filter((p) => p.scoring_status !== "failed") : [];

  return (
    <div className="mx-auto flex max-w-[72rem] flex-col gap-space-6 px-space-3 py-space-6">
      <div className="max-w-measure">
        <h1 className="font-display text-page text-ink">Proposal Anda</h1>
      </div>

      {muatan.status === "loading" && <LoadingState label="Memuat proposal Anda" minHeight={240} />}
      {muatan.status === "error" && <ErrorState message={muatan.message} onRetry={muat} />}
      {muatan.status === "siap" && muatan.proposals.length === 0 && (
        <EmptyState
          reason="Anda belum pernah mengajukan proposal. Ajukan proposal pertama Anda untuk mulai dinilai AI dan dibuka untuk pendanaan."
          action={{
            label: "Ajukan proposal baru",
            onClick: () => router.push("/umkm/proposal/baru"),
          }}
        />
      )}

      {muatan.status === "siap" && muatan.proposals.length > 0 && (
        <>
          {perluTindakan.length > 0 && (
            // Daftar BERNOMOR sungguhan: label pola ini pernah identik dengan
            // "tabel-padat" di bawah, dua kartu polos tanpa nomor maupun
            // tabel (audit RHYTHM 3). Penomoran di sini bukan dekorasi: ia
            // menunjukkan urutan proposal mana yang paling dulu butuh
            // tindakan Anda.
            <section data-pola="daftar-bernomor">
              <h2 className="font-display text-section text-ink">Perlu tindakan Anda sekarang</h2>
              <ol className="mt-space-3 flex flex-col gap-space-3">
                {perluTindakan.map((p, i) => (
                  <li
                    key={p.id}
                    data-testid="kartu-proposal"
                    className="flex gap-space-3 rounded-card border border-warn bg-panel p-space-4"
                  >
                    <span
                      aria-hidden="true"
                      className="tabular text-label font-medium text-muted"
                    >
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center justify-between gap-space-3">
                        <p className="min-w-0 text-card-title font-semibold text-ink">{p.business_name}</p>
                        <StatusBadge status={p.status} />
                      </div>
                      {/* D-09: kegagalan mesin skor bukan keputusan atas usaha ini.
                          Kalimat di bawah sengaja tidak memuat kata yang berarti
                          "ditolak" atau "tidak lolos". */}
                      <p className="mt-space-2 text-body text-ink">
                        Penilaian otomatis belum berhasil dilakukan karena gangguan teknis pada mesin
                        penilai. Ini bukan keputusan atas usaha Anda. Coba nilai ulang.
                      </p>
                      {rescoreError[p.id] && (
                        <p role="alert" className="mt-space-2 text-label text-danger">
                          {rescoreError[p.id]}
                        </p>
                      )}
                      <button
                        type="button"
                        onClick={() => nilaiUlang(p.id)}
                        disabled={rescoring[p.id]}
                        aria-busy={rescoring[p.id]}
                        className="mt-space-3 min-h-[44px] rounded-sm border border-line-strong px-space-3 py-space-2 text-body font-semibold text-ink disabled:text-muted"
                      >
                        Nilai ulang
                      </button>
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          )}

          {lainnya.length > 0 && (
            // Tabel PADAT sungguhan, bukan kartu bertumpuk berlabel "tabel":
            // satu baris per proposal, skor (bila sudah dinilai) dibuka di
            // baris detail di bawahnya, bukan dikartukan ulang.
            <section data-pola="tabel-padat" className="min-w-0">
              <h2 className="font-display text-section text-ink">Semua proposal</h2>
              {/*
                min-w-0 di sini dan di <section> di atas, bukan dekorasi:
                tanpanya, anak flex (section ini di dalam wrapper flex-col
                halaman) memakai lebar konten maksimum sebagai min-width
                otomatisnya (CSS flexbox default), dan tabel 640px di bawah
                mendorong SELURUH halaman melebar sampai scroll horizontal
                di level dokumen muncul di 500px, meski div ini sendiri
                sudah overflow-x-auto. Ditemukan lewat pengukuran browser
                sungguhan (window.scrollTo membuktikan halaman bisa
                scroll 54px secara horizontal), bukan ditaksir dari kode.
              */}
              <div className="mt-space-3 overflow-x-auto">
                <table className="w-full min-w-[640px] border-collapse text-left">
                  <thead>
                    <tr className="border-b border-line-strong text-label text-muted">
                      <th scope="col" className="px-space-2 py-space-2 font-medium">Usaha</th>
                      <th scope="col" className="px-space-2 py-space-2 font-medium">Status</th>
                      <th scope="col" className="px-space-2 py-space-2 font-medium">Dana diminta</th>
                      <th scope="col" className="px-space-2 py-space-2 font-medium">
                        <span className="sr-only">Tautan proposal</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {lainnya.map((p) => (
                      <Fragment key={p.id}>
                        <tr data-testid="kartu-proposal" className="border-b border-line align-top">
                          <td className="px-space-2 py-space-3 text-card-title font-semibold text-ink">
                            {p.business_name}
                          </td>
                          <td className="px-space-2 py-space-3">
                            <StatusBadge status={p.status} />
                          </td>
                          <td className="px-space-2 py-space-3">
                            <Amount label="Dana diminta" amount={p.requested_amount} size="medium" />
                          </td>
                          <td className="px-space-2 py-space-3">
                            {/* Tanpa tautan ini, dashboard UMKM tidak punya jalan sama
                                sekali ke /proposal/[id] -- satu-satunya halaman tempat
                                pledge, milestone, dan "Lapor progres" berada (laporan
                                Fase 11 Task 12). */}
                            <Link
                              href={`/proposal/${p.id}`}
                              className="text-base font-medium text-ink underline"
                            >
                              Baca proposal
                            </Link>
                          </td>
                        </tr>
                        {p.scoring_status === "done" && (
                          <tr>
                            <td colSpan={4} className="px-space-2 pb-space-4">
                              <ScoreSummary proposalId={p.id} />
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}
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
    <div className="border-t border-line pt-space-3">
      <ScorePanel score={state.data} />
    </div>
  );
}
