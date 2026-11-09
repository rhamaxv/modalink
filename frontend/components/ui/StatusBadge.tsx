// Satu tempat untuk seluruh status di aplikasi ini, karena penandaan status yang
// berbeda-beda per halaman membuat pengguna harus belajar ulang arti warna di
// setiap layar. Dipakai halaman proposal, campaign, milestone, dan dashboard.
//
// Kuning (--accent) sengaja tidak ada di sini. DESIGN.md membatasi aksen pada tiga
// momen per layar: tombol aksi utama, bilah funding, dan tahap milestone yang sedang
// berjalan. Badge status bukan salah satunya, dan aksen yang muncul di badge biasa
// berhenti menjadi aksen.

type Tone = "netral" | "berjalan" | "perlu-tindakan" | "berhasil" | "gagal";

// Teks Indonesia karena ia dibaca pengguna; kuncinya nilai mentah dari API.
const STATUS: Record<string, { label: string; tone: Tone }> = {
  draft: { label: "Draf", tone: "netral" },
  submitted: { label: "Menunggu penilaian", tone: "berjalan" },
  listed: { label: "Terbuka untuk pendanaan", tone: "berjalan" },
  partially_funded: { label: "Sebagian terdanai", tone: "berjalan" },
  funded: { label: "Dana terpenuhi", tone: "berhasil" },
  completed: { label: "Selesai", tone: "berhasil" },
  rejected: { label: "Tidak lolos penilaian", tone: "gagal" },
  failed: { label: "Gagal terdanai", tone: "gagal" },

  open: { label: "Terbuka", tone: "berjalan" },
  closed: { label: "Ditutup", tone: "netral" },

  pending: { label: "Menunggu", tone: "berjalan" },
  reported: { label: "Laporan menunggu review", tone: "perlu-tindakan" },
  approved: { label: "Disetujui", tone: "berhasil" },
  disbursed: { label: "Dana cair", tone: "berhasil" },

  processing: { label: "Sedang dinilai", tone: "berjalan" },
  done: { label: "Selesai dinilai", tone: "berhasil" },

  active: { label: "Aktif", tone: "berhasil" },
  cancelled: { label: "Dibatalkan", tone: "netral" },
};

// Rasio kontras tiap pasangan di bawah sudah diukur dan tercatat di DESIGN.md.
// Latar memakai --surface, bukan warna status yang dimudakan, supaya tidak ada
// pasangan baru yang belum terukur masuk lewat pintu belakang.
const TONE_CLASS: Record<Tone, string> = {
  netral: "text-muted",
  berjalan: "text-ink",
  "perlu-tindakan": "text-warn",
  berhasil: "text-ok",
  gagal: "text-danger",
};

type StatusBadgeProps = {
  status: string;
  className?: string;
};

export function StatusBadge({ status, className = "" }: StatusBadgeProps) {
  const dikenal = STATUS[status];

  // Status yang tidak dikenal ditampilkan apa adanya, bukan disembunyikan dan
  // bukan dipaksa jadi "Tidak diketahui": backend yang menambah status baru harus
  // terlihat di UI, bukan hilang dari layar tanpa jejak.
  const label = dikenal?.label ?? status;
  const tone = dikenal?.tone ?? "netral";

  return (
    <span
      data-status={status}
      className={`inline-flex items-center rounded-kecil border border-line bg-surface px-ruang-2 py-ruang-1 text-[0.8125rem] font-medium ${TONE_CLASS[tone]} ${className}`}
    >
      {label}
    </span>
  );
}
