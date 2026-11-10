import { Icon } from "@/components/icons/Icon";

type RedFlagSeverity = "info" | "warning" | "critical";

type RedFlag = {
  code: string;
  severity: RedFlagSeverity;
  message: string;
  evidence: string;
};

type ScoreBrief = {
  strengths: string[];
  risks: string[];
  recommendation: string;
};

export type ProposalScore = {
  fit_score: number;
  data_quality_score: number;
  impact_score: number;
  total_score: number;
  threshold_used: number;
  model_name: string;
  created_at: string;
  red_flags: RedFlag[];
  brief: ScoreBrief;
};

export type ScoringStatus = "pending" | "processing" | "done" | "failed";

type ScorePanelProps = {
  score: ProposalScore | null;
  /** Hanya relevan saat score masih null: pending/processing/failed. */
  scoringStatus?: ScoringStatus;
  /** Dipanggil saat tombol "Nilai ulang" diklik. Kosong di test terisolasi;
   * diisi sungguhan oleh halaman detail proposal yang memanggil endpoint rescore. */
  onRescore?: () => void;
};

// Label severity ditulis sebagai teks, bukan hanya warna, supaya pembaca
// layar dan pengguna buta warna tetap tahu tingkatnya (lihat test
// "red flag severity is not conveyed by colour alone").
const SEVERITY_LABEL: Record<RedFlagSeverity, string> = {
  info: "Info",
  warning: "Peringatan",
  critical: "Kritis",
};

// Warna severity dipilih dari token status yang sudah terukur kontrasnya di
// DESIGN.md (--ok/--warn/--danger terhadap --panel), bukan pasangan baru.
const SEVERITY_CLASS: Record<RedFlagSeverity, string> = {
  info: "text-muted",
  warning: "text-warn",
  critical: "text-danger",
};

const KOMPONEN = [
  { key: "fit_score" as const, label: "Kecocokan kriteria", maksimum: 40 },
  { key: "data_quality_score" as const, label: "Kualitas data", maksimum: 30 },
  { key: "impact_score" as const, label: "Potensi dampak", maksimum: 30 },
];

function formatTanggal(iso: string): string {
  return new Date(iso).toLocaleString("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

// Panel skor AI: fase 11 task 1. Menampilkan skor terurai per komponen,
// bukan satu angka gelap (US-I3), karena investor perlu tahu APA yang
// membuat sebuah proposal dinilai begitu, tidak hanya angkanya.
//
// Sengaja TIDAK memakai --accent sama sekali: panel ini informasi yang
// dibaca, bukan aksi yang diklik. DESIGN.md menyimpan aksen untuk bilah
// funding, tombol pledge, dan penanda milestone aktif di halaman yang sama.
export function ScorePanel({ score, scoringStatus, onRescore }: ScorePanelProps) {
  if (score === null) {
    if (scoringStatus === "failed") {
      // D-09 di lapisan UI: kegagalan teknis (timeout, API key kosong, output
      // tidak lolos validasi) tidak pernah berarti proposal ditolak. Tombol
      // di sini memberi jalan keluar nyata, bukan pesan "ditolak" yang
      // menyesatkan pemilik usaha.
      return (
        <div className="flex flex-col items-start gap-space-3 rounded-panel border border-line bg-panel px-space-4 py-space-5">
          <p className="max-w-measure text-body text-ink">
            Penilaian AI belum bisa diselesaikan karena gangguan teknis. Status proposal ini
            tidak berubah, dan Anda bisa memicu penilaian ulang kapan saja.
          </p>
          <button
            type="button"
            onClick={onRescore}
            className="inline-flex min-h-[44px] items-center gap-space-2 rounded-sm border border-line-strong px-space-3 py-space-2 text-body font-semibold text-ink transition-colors hover:bg-panel-raised"
          >
            <Icon name="score" size={18} />
            Nilai ulang
          </button>
        </div>
      );
    }

    // "pending" dan "processing" ditampilkan sama: keduanya berarti belum
    // ada skor untuk ditunjukkan. Nol adalah skor yang sah, jadi menampilkan
    // nol di sini akan berbohong ke pengguna tentang arti kekosongan ini.
    return (
      <div
        role="status"
        aria-live="polite"
        className="flex items-center gap-space-2 rounded-panel border border-line bg-panel px-space-4 py-space-5 text-body text-muted"
      >
        <span
          aria-hidden="true"
          className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-ink motion-reduce:animate-none"
        />
        <span>Sedang dinilai oleh AI. Hasilnya akan tampil di sini begitu selesai.</span>
      </div>
    );
  }

  // brief.strengths dan brief.risks sampai laporan Fase 11 Task 12 hanya
  // dideklarasikan di tipe ScoreBrief, tidak pernah dirender: hanya
  // recommendation yang mencapai layar, padahal halaman jelajah menjanjikan
  // investor bisa membaca brief AI (R-26, R-38). Keduanya ditaruh di balik
  // <details> native (bukan state React): tombol "Nilai ulang" dan verdict
  // sudah memberi keputusan cepat, strengths/risks adalah detail pendukung
  // yang layak dibuka sendiri, dan <details>/<summary> sudah bisa dibuka
  // lewat keyboard (Enter/Space) tanpa kode tambahan (R-32).
  const adaBrief = score.brief.strengths.length > 0 || score.brief.risks.length > 0;

  return (
    <div className="flex flex-col gap-space-4 rounded-panel border border-line bg-panel px-space-4 py-space-5">
      <div className="flex flex-wrap items-baseline justify-between gap-space-2">
        <p className="flex items-center gap-space-2 text-amount-sm font-display text-ink">
          {/* Menandai angka ini sebagai penilaian AI, bukan nominal rupiah:
              keduanya memakai skala tipografi yang sama di produk ini, dan
              "78" tanpa penanda apa pun terbaca ambigu. Bintang empat sudut,
              bukan otak atau robot: yang terjadi di sini adalah penilaian,
              bukan pertunjukan kecerdasan buatan. */}
          <Icon name="score" size={22} className="text-accent-text" />
          <span className="tabular">{score.total_score}</span>
          <span className="text-label font-medium text-muted"> dari 100</span>
        </p>
        <p className="tabular text-label font-medium text-muted">
          Ambang campaign: {score.threshold_used}
        </p>
      </div>

      <dl className="grid gap-space-3 sm:grid-cols-3">
        {KOMPONEN.map((komponen) => (
          <div key={komponen.key} className="flex flex-col gap-space-1">
            <dt className="text-label font-medium text-muted">{komponen.label}</dt>
            <dd className="tabular text-card-title font-semibold text-ink">
              {score[komponen.key]}
              <span className="text-label font-medium text-muted"> dari {komponen.maksimum}</span>
            </dd>
          </div>
        ))}
      </dl>

      {score.red_flags.length > 0 && (
        <div className="flex flex-col gap-space-3 border-t border-line pt-space-3">
          <p className="text-label font-medium text-muted">Red flag</p>
          <ul className="flex flex-col gap-space-3">
            {score.red_flags.map((flag) => (
              <li key={flag.code} className="flex flex-col gap-space-1">
                <p className={`text-base font-semibold leading-[1.6] ${SEVERITY_CLASS[flag.severity]}`}>
                  {SEVERITY_LABEL[flag.severity]}: {flag.message}
                </p>
                <p className="max-w-measure text-body text-muted">
                  Kutipan dari proposal: &ldquo;{flag.evidence}&rdquo;
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {adaBrief && (
        <details className="border-t border-line pt-space-3">
          <summary className="min-h-[44px] cursor-pointer py-space-1 text-body font-semibold text-ink">
            Lihat kekuatan dan risiko menurut AI
          </summary>
          <div className="mt-space-3 grid gap-space-4 sm:grid-cols-2">
            {score.brief.strengths.length > 0 && (
              <div className="flex flex-col gap-space-2">
                <p className="text-label font-medium text-muted">Kekuatan</p>
                <ul className="flex flex-col gap-space-1">
                  {score.brief.strengths.map((item) => (
                    <li key={item} className="text-body text-ink">
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {score.brief.risks.length > 0 && (
              <div className="flex flex-col gap-space-2">
                <p className="text-label font-medium text-muted">Risiko</p>
                <ul className="flex flex-col gap-space-1">
                  {score.brief.risks.map((item) => (
                    <li key={item} className="text-body text-ink">
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </details>
      )}

      <div className="flex flex-col gap-space-2 border-t border-line pt-space-3">
        <p className="max-w-measure text-body text-ink">{score.brief.recommendation}</p>
        <p className="text-label text-muted">
          Dinilai oleh model {score.model_name} pada {formatTanggal(score.created_at)}.
        </p>
        <p className="text-label font-medium text-muted">
          Skor ini sinyal pendukung. Keputusan akhir ada di investor.
        </p>
      </div>
    </div>
  );
}
