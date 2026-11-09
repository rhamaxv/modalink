type LoadingStateProps = {
  /** Apa yang sedang dimuat, misal "Memuat daftar proposal". */
  label: string;
  /**
   * Tinggi ruang yang dipesan, dalam piksel. Sebaiknya mendekati tinggi
   * konten sungguhan yang akan menggantikannya, supaya layout tidak melompat
   * saat data datang. Defaultnya DEFAULT_MIN_HEIGHT, bukan tanpa batas:
   * kalau pemanggil lupa mengisinya, pilihan amannya tetap memesan ruang,
   * bukan runtuh ke tinggi nol lalu melompat saat data datang.
   */
  minHeight?: number;
};

// --ruang-7 dari DESIGN.md (96px): ruang cadangan default yang aman, bukan
// angka sembarang, saat pemanggil tidak tahu atau tidak peduli tinggi
// konten sungguhannya.
const DEFAULT_MIN_HEIGHT = 96;

// Loading state yang hanya menampilkan spinner tanpa teks tidak memberi tahu
// pembaca layar apa pun yang sedang terjadi. aria-live mengumumkan label ini
// begitu komponen muncul.
export function LoadingState({ label, minHeight = DEFAULT_MIN_HEIGHT }: LoadingStateProps) {
  return (
    <div
      data-testid="loading-state"
      role="status"
      aria-live="polite"
      style={{ minHeight: `${minHeight}px` }}
      className="flex items-center gap-ruang-2 rounded-kartu border border-line bg-surface px-ruang-4 py-ruang-3 text-base leading-[1.6] text-muted"
    >
      <span
        aria-hidden="true"
        // motion-reduce:animate-none: MOTION 2 di DESIGN.md tidak berarti
        // mengabaikan preferensi pengguna yang meminta gerak dikurangi.
        className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-ink motion-reduce:animate-none"
      />
      <span>{label}</span>
    </div>
  );
}
