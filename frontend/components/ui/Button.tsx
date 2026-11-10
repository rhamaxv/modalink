import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

type Varian = "primary" | "secondary" | "ghost";

// Bahasa tombol satu tempat, bukan ditemukan ulang per halaman. Tanpa ini
// setiap rute memilih sendiri apakah ajakan bertindak berupa tombol berwarna
// atau tautan bergaris bawah, dan hasilnya halaman depan sempat tidak punya
// satu pun tombol berlatar: setiap CTA transparan, sehingga aksen tidak
// pernah muncul di layar pertama meski DESIGN.md menyebut aksen sebagai
// tindakan utama.
//
// Pil hanya di tombol (DESIGN.md). R-11 melarang pil di mana-mana; pil yang
// konsisten hanya di tombol justru menjadi bahasa tombol, bukan dekorasi.
const VARIAN: Record<Varian, string> = {
  // text-on-accent, tidak pernah text-ink: --ink berbalik ikut tema sementara
  // aksen tidak, dan putih di atas lime mengukur 1.14:1.
  primary: "bg-accent text-on-accent hover:brightness-95",
  // border-line-strong, bukan border-line: yang kedua mengukur 1.46:1 dan
  // hanya sah sebagai pemisah dekoratif, bukan sebagai batas kontrol.
  secondary: "border border-line-strong text-ink hover:bg-panel",
  // text-accent-text pada hover, bukan text-accent polos: token terakhir itu
  // adalah warna LATAR, 1,09:1 saat dipakai sebagai teks di atas --paper
  // terang (DESIGN.md). text-accent-text berbalik ikut tema karena ia duduk
  // di atas --paper yang juga berbalik, persis pasangan yang sudah diukur
  // lolos 6,21:1 gelap dan 6,21:1/5,70:1 terang.
  ghost: "text-ink underline underline-offset-4 hover:text-accent-text",
};

const DASAR =
  "inline-flex min-h-[44px] items-center justify-center gap-space-2 rounded-pill px-space-4 py-space-2 text-body font-semibold transition-colors disabled:cursor-not-allowed disabled:border disabled:border-line-strong disabled:bg-panel disabled:text-muted";

type Bersama = { varian?: Varian; className?: string; children: ReactNode };

export function ButtonLink({
  varian = "primary",
  className = "",
  children,
  ...sisa
}: Bersama & ComponentProps<typeof Link>) {
  return (
    <Link className={`${DASAR} ${VARIAN[varian]} ${className}`} {...sisa}>
      {children}
    </Link>
  );
}

export function Button({
  varian = "primary",
  className = "",
  children,
  type = "button",
  ...sisa
}: Bersama & ComponentProps<"button">) {
  return (
    <button type={type} className={`${DASAR} ${VARIAN[varian]} ${className}`} {...sisa}>
      {children}
    </button>
  );
}
