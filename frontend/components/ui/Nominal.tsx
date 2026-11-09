import { formatRupiah } from "@/lib/money";

type NominalProps = {
  /** Keterangan singkat di atas angka, misal "Terkumpul" atau "Target". */
  label: string;
  nominal: number;
  /** "besar" untuk tokoh utama kartu, "sedang" untuk nominal pendukung di tabel. */
  ukuran?: "besar" | "sedang";
};

// Motif identitas produk (DESIGN.md): nominal rupiah selalu rata kiri, tabular,
// dan lebih besar dari teks biasa, dengan label kecil di atasnya, bukan
// diselipkan sebagai teks di tengah paragraf.
export function Nominal({ label, nominal, ukuran = "besar" }: NominalProps) {
  return (
    <div className="text-left">
      <p className="text-[0.8125rem] font-medium text-muted">{label}</p>
      <p
        className={`tabular font-semibold text-ink ${
          ukuran === "besar" ? "text-[1.75rem]" : "text-[1.125rem]"
        }`}
      >
        {formatRupiah(nominal)}
      </p>
    </div>
  );
}
