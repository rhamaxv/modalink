import type { SVGProps } from "react";

// Satu sistem ikon untuk seluruh aplikasi, bukan SVG yang ditempel per
// halaman. Aturannya tiga, dan ketiganya menentukan apakah ikon menambah
// kejelasan atau cuma menambah benda:
//
// 1. Semua digambar di kanvas 24x24 dengan GARIS, bukan isian, lebar garis
//    1,75. Angka itu sama dengan panah <select> di app/globals.css, jadi
//    ikon dan kontrol formulir terasa digambar oleh tangan yang sama.
// 2. Warnanya selalu currentColor. Ikon mewarisi warna teks di sebelahnya,
//    jadi ia ikut berbalik saat tema berganti tanpa satu pun token tambahan,
//    dan tidak pernah bisa memunculkan pasangan warna yang belum diukur.
// 3. Default-nya aria-hidden. Hampir setiap ikon di produk ini berdiri di
//    sebelah teks yang sudah mengatakan hal yang sama; dibacakan dua kali,
//    ia justru memperlambat pembaca layar. Yang berdiri sendiri tanpa teks
//    wajib mengoper `title`, dan barulah ia masuk ke pohon aksesibilitas.

export type IconName =
  // Enam sektor usaha, sama persis dengan Sector di
  // backend/app/models/campaign.py. Dipakai di kolom sektor, chip kategori,
  // dan sebagai sampul cadangan ketika sebuah usaha belum mengunggah foto.
  | "kuliner"
  | "kerajinan"
  | "pertanian"
  | "jasa"
  | "ritel"
  | "teknologi"
  // Keadaan dan alur.
  | "clock"
  | "check"
  | "alert"
  | "money"
  | "milestone"
  | "score"
  | "community"
  // Navigasi dan aksi.
  | "arrow-right"
  | "arrow-left"
  | "upload"
  | "image"
  | "dokumen";

// Jalur digambar pada grid 24x24. Ditulis sebagai data, bukan sebagai satu
// komponen React per ikon: daftar ini dipakai juga oleh pagar di
// tests/icons.test.tsx yang memastikan setiap sektor punya ikonnya.
const JALUR: Record<IconName, string> = {
  // Mangkuk dengan dua kepul uap. Bukan sendok-garpu: sendok-garpu adalah
  // lambang "restoran", sedangkan yang didanai di sini kebanyakan usaha
  // makanan rumahan.
  kuliner:
    "M3 11.5h18M20 11.5a8 8 0 0 1-16 0M9 3.2c0 1.1-1 1.3-1 2.3s1 1.2 1 2.3M14.5 3.2c0 1.1-1 1.3-1 2.3s1 1.2 1 2.3",
  // Anyaman: kisi diagonal di dalam bingkai membulat. Membaca sebagai kain
  // atau rotan, dua bahan kerajinan yang paling sering muncul.
  kerajinan:
    "M3.5 6.5a3 3 0 0 1 3-3h11a3 3 0 0 1 3 3v11a3 3 0 0 1-3 3h-11a3 3 0 0 1-3-3zM3.5 12.5l9-9M3.5 19l15.5-15.5M10 20.5l10.5-10.5",
  // Tunas dua daun di atas garis tanah. Garis tanahnya bukan hiasan: tanpa
  // alas, batangnya menggantung dan bentuknya terbaca seperti huruf Y.
  pertanian:
    "M12 20.4v-6.6M12 13.8c0-3.3 2.7-6 6-6 0 3.3-2.7 6-6 6ZM12 13.8c0-2.6-2.1-4.7-4.7-4.7 0 2.6 2.1 4.7 4.7 4.7ZM4.6 20.4h14.8",
  // Roda gigi: jasa adalah pekerjaan yang dikerjakan, bukan barang yang
  // dijual. Dua lingkaran dengan gigi PENDEK di luarnya, bukan satu
  // lingkaran kecil dengan garis panjang memancar: versi pertama digambar
  // begitu dan terbaca sebagai matahari, bukan roda gigi.
  jasa:
    "M12 17.5a5.5 5.5 0 1 1 0-11 5.5 5.5 0 0 1 0 11ZM12 14.2a2.2 2.2 0 1 1 0-4.4 2.2 2.2 0 0 1 0 4.4ZM17.5 12h2.7M12 17.5v2.7M3.8 12h2.7M12 3.8v2.7M15.9 15.9l1.9 1.9M8.1 15.9l-1.9 1.9M8.1 8.1 6.2 6.2M15.9 8.1l1.9-1.9",
  // Kios: badan bangunan, tenda tertutup di atasnya, pintu di tengah.
  // Tendanya ditutup (Z) menjadi bidang trapesium; dibiarkan terbuka seperti
  // versi pertama, ia cuma terbaca sebagai atap datar dan seluruh ikonnya
  // menyerupai brankas.
  ritel:
    "M3.6 9.6h16.8v10.3a.6.6 0 0 1-.6.6H4.2a.6.6 0 0 1-.6-.6ZM2.6 9.6 4.8 3.6h14.4l2.2 6ZM9.6 20.5v-5.6h4.8v5.6",
  // Keping sirkuit berkaki.
  teknologi:
    "M7.6 9.1a1.5 1.5 0 0 1 1.5-1.5h5.8a1.5 1.5 0 0 1 1.5 1.5v5.8a1.5 1.5 0 0 1-1.5 1.5H9.1a1.5 1.5 0 0 1-1.5-1.5zM10 3.6v4M14 3.6v4M10 16.4v4M14 16.4v4M3.6 10h4M3.6 14h4M16.4 10h4M16.4 14h4",

  clock: "M12 20.5a8.5 8.5 0 1 1 0-17 8.5 8.5 0 0 1 0 17ZM12 7.2v5.2l3.4 2",
  check: "M4.5 12.6 9.6 17.7 19.5 6.6",
  alert: "M12 3.4 21.6 20.2H2.4zM12 9.8v4.3M12 17.3h.01",
  // Tumpukan koin: nominal rupiah adalah elemen grafis produk ini
  // (DESIGN.md), jadi lambangnya pun uang yang bertumpuk, bukan dompet.
  money:
    "M19 6.5c0 1.7-3.1 3-7 3s-7-1.3-7-3 3.1-3 7-3 7 1.3 7 3ZM5 6.5v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5M5 11.5v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5",
  // Jalur bertahap: bulatan dihubungkan garis, geometri yang sama dengan
  // MilestoneTimeline dan daftar alur dana di halaman depan.
  milestone:
    "M6 4.8a2 2 0 1 1 0 4 2 2 0 0 1 0-4ZM6 15.2a2 2 0 1 1 0 4 2 2 0 0 1 0-4ZM6 8.8v6.4M11 6.8h8M11 17.2h8",
  // Bintang empat sudut: penilaian AI, dan sengaja bukan otak atau robot.
  score: "M12 3.2 14 9.2l6 2-6 2-2 6-2-6-6-2 6-2zM19 15.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z",
  community:
    "M9 11.4a3.4 3.4 0 1 1 0-6.8 3.4 3.4 0 0 1 0 6.8ZM2.8 20.2c0-3.4 2.8-6.2 6.2-6.2s6.2 2.8 6.2 6.2M16 5.1a3.4 3.4 0 0 1 0 6.6M17.6 14.4c2.1.9 3.6 3 3.6 5.4",

  "arrow-right": "M4.5 12h15M13.5 6l6 6-6 6",
  "arrow-left": "M19.5 12h-15M10.5 18l-6-6 6-6",
  upload: "M12 15.6V3.8M7.8 8l4.2-4.2L16.2 8M4 15v4.2a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V15",
  image:
    "M3.6 7a2.4 2.4 0 0 1 2.4-2.4h12a2.4 2.4 0 0 1 2.4 2.4v10a2.4 2.4 0 0 1-2.4 2.4H6A2.4 2.4 0 0 1 3.6 17zM9 11.2a1.7 1.7 0 1 1 0-3.4 1.7 1.7 0 0 1 0 3.4ZM4 17l5.2-4.7 4.3 3.9 2.8-2.4L20 17",
  // Lembar dengan sudut terlipat dan tiga baris teks. Lipatannya digambar
  // sebagai dua garis (tepi miring lalu sisi dalamnya), bukan satu, supaya
  // ia terbaca sebagai halaman kertas dan bukan sekadar kotak yang sudutnya
  // terpotong.
  dokumen:
    "M13.4 3.4H6.8a1.8 1.8 0 0 0-1.8 1.8v13.6a1.8 1.8 0 0 0 1.8 1.8h10.4a1.8 1.8 0 0 0 1.8-1.8V8.8zM13.4 3.4v5.4h5.6M8.6 13h6.8M8.6 16.6h6.8",
};

type IconProps = Omit<SVGProps<SVGSVGElement>, "name"> & {
  name: IconName;
  /** Ukuran sisi dalam piksel. Default 20, setara tinggi satu baris teks. */
  size?: number;
  /** Isi hanya ketika ikon berdiri SENDIRI tanpa teks yang menjelaskannya.
   * Selama ia menemani teks, biarkan kosong: dibacakan dua kali, ikon justru
   * memperlambat pembaca layar. */
  title?: string;
};

export function Icon({ name, size = 20, title, className = "", ...sisa }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      // shrink-0: ikon di dalam baris flex yang sempit tidak boleh digencet
      // jadi lonjong. Lebarnya sudah ditetapkan, jadi ia tidak ikut menyusut.
      className={`shrink-0 ${className}`}
      {...sisa}
    >
      {title && <title>{title}</title>}
      <path d={JALUR[name]} />
    </svg>
  );
}

// Dipakai pagar di tests/icons.test.tsx dan oleh SectorMark.
export const NAMA_IKON = Object.keys(JALUR) as IconName[];
