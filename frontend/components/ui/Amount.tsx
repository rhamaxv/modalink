import { formatRupiah } from "@/lib/money";

type AmountProps = {
  /** Keterangan singkat di atas angka, misal "Terkumpul" atau "Target". */
  label: string;
  amount: number;
  /** "large" untuk tokoh utama kartu, "medium" untuk nominal pendukung di tabel. */
  size?: "large" | "medium";
};

// Motif identitas produk (DESIGN.md): nominal rupiah selalu rata kiri, tabular,
// dan lebih besar dari teks biasa, dengan label kecil di atasnya, bukan
// diselipkan sebagai teks di tengah paragraf.
export function Amount({ label, amount, size = "large" }: AmountProps) {
  return (
    <div className="text-left">
      <p className="text-[0.8125rem] font-medium text-muted">{label}</p>
      <p
        className={`tabular font-semibold text-ink ${
          size === "large" ? "text-[1.75rem]" : "text-[1.125rem]"
        }`}
      >
        {formatRupiah(amount)}
      </p>
    </div>
  );
}
