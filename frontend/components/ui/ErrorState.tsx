type ErrorStateProps = {
  /** Penyebab galat, dalam kalimat yang bisa dipahami pengguna, bukan kode internal. */
  message: string;
  onRetry: () => void;
};

// R-27 + R-32: galat wajib menyebut penyebab, menyediakan satu jalan keluar
// (coba lagi), dan mengumumkan dirinya ke pembaca layar lewat role="alert".
export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-space-3 rounded-card border border-danger bg-surface px-space-4 py-space-5 text-left"
    >
      <p className="max-w-measure text-base leading-[1.6] text-danger">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        // border-ink, bukan border-line: border-line hanya 1.27:1 terhadap
        // bg-surface, gagal ambang 3:1 untuk batas elemen interaktif.
        className="min-h-[44px] rounded-sm border border-ink px-space-3 py-space-2 text-base leading-[1.6] font-semibold text-ink"
      >
        Coba lagi
      </button>
    </div>
  );
}
