type KeadaanGalatProps = {
  /** Penyebab galat, dalam kalimat yang bisa dipahami pengguna, bukan kode internal. */
  pesan: string;
  onCobaLagi: () => void;
};

// R-27 + R-32: galat wajib menyebut penyebab, menyediakan satu jalan keluar
// (coba lagi), dan mengumumkan dirinya ke pembaca layar lewat role="alert".
export function KeadaanGalat({ pesan, onCobaLagi }: KeadaanGalatProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-ruang-3 rounded-kartu border border-danger bg-surface px-ruang-4 py-ruang-5 text-left"
    >
      <p className="max-w-baca text-sm text-danger">{pesan}</p>
      <button
        type="button"
        onClick={onCobaLagi}
        // border-ink, bukan border-line: border-line hanya 1.27:1 terhadap
        // bg-surface, gagal ambang 3:1 untuk batas elemen interaktif.
        className="min-h-[44px] rounded-kecil border border-ink px-ruang-3 py-ruang-2 text-sm font-semibold text-ink"
      >
        Coba lagi
      </button>
    </div>
  );
}
