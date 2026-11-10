import { formatRupiah } from "@/lib/money";

type AmountProps = {
  /** Keterangan singkat di atas angka, misal "Terkumpul" atau "Target". */
  label: string;
  amount: number;
  /**
   * "hero" dipakai sekali per layar untuk angka yang memimpin halaman,
   * "large" untuk tokoh utama kartu, "medium" untuk nominal pendukung.
   */
  size?: "hero" | "large" | "medium";
  /** Lime untuk angka yang sedang jadi subjek keputusan, misal sisa dana. */
  tone?: "default" | "accent";
};

// Motif identitas produk, dan di arah visual sekarang ia memikul beban lebih
// besar daripada sebelumnya: referensi yang ditunjuk pemilik project memuat 341
// gambar, Modalink punya nol dan dilarang mengarangnya, jadi angka rupiah
// tabular inilah yang mengisi ruang tempat foto bekerja di sana. Karena itu
// ukuran "hero" sengaja sebesar judul halaman, bukan sekadar lebih besar dari
// teks biasa.
const UKURAN = {
  hero: "text-amount font-display",
  large: "text-amount-sm font-display",
  medium: "text-card-title font-semibold",
} as const;

export function Amount({ label, amount, size = "large", tone = "default" }: AmountProps) {
  return (
    <div className="text-left">
      <p className="text-label font-medium uppercase tracking-wide text-muted">{label}</p>
      <p
        className={`tabular ${UKURAN[size]} ${
          // text-accent-text, bukan text-accent polos: text-accent adalah
          // token LATAR, dan dipakai sebagai warna teks ia mengukur 1,09:1 di
          // atas --paper terang (DESIGN.md, "Never bare text-accent"). Bug ini
          // sungguh terkirim lewat MilestoneApprovalFeed (nominal "hero" di
          // tema terang nyaris tidak terbaca) sebelum diukur di sini.
          // text-accent-text berbalik ikut tema karena ia duduk di atas
          // --paper yang juga berbalik, dan sudah diukur lolos 6,21:1 gelap,
          // 6,21:1/5,70:1 terang.
          tone === "accent" ? "text-accent-text" : "text-ink"
        }`}
      >
        {formatRupiah(amount)}
      </p>
    </div>
  );
}
