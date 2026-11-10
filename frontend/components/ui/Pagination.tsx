"use client";

import { Icon } from "@/components/icons/Icon";

type PaginationProps = {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  /** Dibaca pembaca layar untuk membedakan dua paginasi di satu halaman. */
  label: string;
};

// Kontrol halaman sungguhan, bukan hitungan yang cuma dipajang.
//
// Sebelum ini halaman jelajah tidak punya satu pun kontrol halaman padahal
// backend sudah memaksa page_size maksimum 50 dan default 20. Dengan lima
// puluh proposal, halaman itu diam-diam hanya menampilkan dua puluh pertama
// dan tidak memberi jalan apa pun ke sisanya; tidak ada pesan, tidak ada
// tombol, tidak ada tanda bahwa ada yang disembunyikan.
export function Pagination({ page, pageSize, total, onPageChange, label }: PaginationProps) {
  const totalHalaman = Math.max(1, Math.ceil(total / pageSize));
  // Satu halaman berarti tidak ada ke mana-mana untuk pergi. Tombol mati di
  // kedua sisi lebih membingungkan daripada tidak ada tombol sama sekali.
  if (totalHalaman <= 1) return null;

  const kelas =
    "inline-flex min-h-[44px] items-center gap-space-2 rounded-pill border border-line-strong px-space-3 text-body font-medium text-ink transition-colors hover:bg-panel disabled:cursor-not-allowed disabled:border-line disabled:text-muted disabled:hover:bg-transparent";

  return (
    <nav
      aria-label={label}
      className="flex flex-wrap items-center justify-between gap-space-3 border-t border-line pt-space-4"
    >
      <button
        type="button"
        className={kelas}
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
      >
        <Icon name="arrow-left" size={18} />
        Sebelumnya
      </button>
      {/* aria-live: pindah halaman tidak memindahkan fokus dan tidak memuat
          dokumen baru, jadi tanpa ini pengguna pembaca layar menekan
          "Berikutnya" dan tidak diberi tahu apa pun bahwa isinya berganti. */}
      <p aria-live="polite" className="tabular text-body text-muted">
        Halaman {page} dari {totalHalaman}
      </p>
      <button
        type="button"
        className={kelas}
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalHalaman}
      >
        Berikutnya
        <Icon name="arrow-right" size={18} />
      </button>
    </nav>
  );
}

type ResultCountProps = {
  page: number;
  pageSize: number;
  total: number;
  /** Kata benda jamak yang dihitung, misalnya "proposal" atau "campaign". */
  noun: string;
};

// "Menampilkan 1-20 dari 57", bukan cuma "57 proposal": begitu paginasi ada,
// jumlah total saja justru menyesatkan, karena yang terlihat di layar bukan
// jumlah itu. Totalnya ditulis dengan --accent-text: satu-satunya angka di
// layar ini yang menjawab "sebenarnya ada berapa", dan DESIGN.md memang
// menjatah aksen untuk penanda semacam itu (bukan sebagai latar, jadi token
// yang berbalik tema dipakai, bukan --accent).
export function ResultCount({ page, pageSize, total, noun }: ResultCountProps) {
  if (total === 0) {
    return (
      <p className="tabular text-label text-muted">
        <span className="font-semibold text-accent-text">0</span> {noun}
      </p>
    );
  }
  const dari = (page - 1) * pageSize + 1;
  const sampai = Math.min(page * pageSize, total);
  return (
    <p className="tabular text-label text-muted">
      Menampilkan {dari}-{sampai} dari{" "}
      <span className="font-semibold text-accent-text">{total}</span> {noun}
    </p>
  );
}
