type KeadaanMuatProps = {
  /** Apa yang sedang dimuat, misal "Memuat daftar proposal". */
  label: string;
  /**
   * Tinggi ruang yang dipesan, dalam piksel. Harus mendekati tinggi konten
   * sungguhan yang akan menggantikannya, supaya layout tidak melompat saat
   * data datang.
   */
  tinggiMinimum?: number;
};

// Loading state yang hanya menampilkan spinner tanpa teks tidak memberi tahu
// pembaca layar apa pun yang sedang terjadi. aria-live mengumumkan label ini
// begitu komponen muncul.
export function KeadaanMuat({ label, tinggiMinimum }: KeadaanMuatProps) {
  return (
    <div
      data-testid="keadaan-muat"
      role="status"
      aria-live="polite"
      style={tinggiMinimum ? { minHeight: `${tinggiMinimum}px` } : undefined}
      className="flex items-center gap-ruang-2 rounded-kartu border border-line bg-surface px-ruang-4 py-ruang-3 text-sm text-muted"
    >
      <span
        aria-hidden="true"
        className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-ink"
      />
      <span>{label}</span>
    </div>
  );
}
