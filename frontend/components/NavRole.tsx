import Link from "next/link";
import type { Role } from "@/lib/auth";

type NavItem = { href: string; label: string };

// Satu tempat untuk tautan nav per peran, supaya AppHeader tidak perlu tahu
// peran mana melihat apa. Peran "community" sengaja tanpa tautan sendiri:
// komunitas memakai nav publik yang sama (Jelajahi) seperti pengunjung
// anonim, tidak ada dashboard khusus untuknya.
const NAV_BY_ROLE: Record<Role, NavItem[]> = {
  investor: [
    { href: "/investor/campaign", label: "Campaign saya" },
    { href: "/investor/milestone", label: "Milestone menunggu" },
  ],
  umkm: [{ href: "/umkm/beranda", label: "Beranda saya" }],
  community: [],
};

// Target sentuh 44px untuk setiap tautan nav header. Audit browser menemukan
// tautan nav hanya setinggi 20-24px di setiap rute: sebelum ini kotak klik
// tautan sama dengan tinggi baris tulisannya sendiri, karena hanya garis
// bawah yang menandai area klik.
//
// Garis bawah permanen yang dulu ada di sini sudah dicabut. Ia membuat
// seluruh nav terbaca sebagai deretan hyperlink mentah, dan karena SEMUA
// tautan bergaris bawah, garis itu tidak membedakan apa pun: ia tidak
// menandai mana yang sedang dibuka, tidak menandai mana yang penting, dan
// hanya menambah berat visual di baris yang seharusnya paling tenang di
// halaman. Penandanya pindah ke keadaan: warna (muted -> ink saat ditunjuk)
// untuk keterjangkauan, dan garis aksen untuk halaman yang sedang dibuka.
export const NAV_LINK_CLASS =
  "inline-flex min-h-[44px] items-center text-body font-medium text-muted transition-colors hover:text-ink focus-visible:text-ink";

// Garis di bawah teks, bukan di bawah kotak klik setinggi 44px: kotak itu
// jauh lebih tinggi dari hurufnya, jadi garis yang menempel ke tepi bawah
// kotak akan melayang terpisah dari kata yang ditandainya.
function markerClass(active: boolean) {
  return active
    ? "border-b-2 border-accent pb-1"
    : "border-b-2 border-transparent pb-1";
}

export function NavLink({
  href,
  label,
  pathname,
  onClick,
}: {
  href: string;
  label: string;
  pathname?: string;
  onClick?: () => void;
}) {
  // Pencocokan awalan, bukan persamaan persis: /investor/campaign tetap
  // ditandai aktif saat pengguna membuka /investor/campaign/<id>, karena
  // halaman detail itu memang berada di bawah tautan nav tersebut.
  const active =
    pathname === href || (href !== "/" && pathname?.startsWith(`${href}/`) === true);
  return (
    <Link
      href={href}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={`${NAV_LINK_CLASS} ${active ? "text-ink" : ""}`}
    >
      <span className={markerClass(active)}>{label}</span>
    </Link>
  );
}

export function NavRole({ role, pathname }: { role: Role; pathname?: string }) {
  const items = NAV_BY_ROLE[role];
  if (items.length === 0) return null;
  return (
    <>
      {items.map((item) => (
        <NavLink key={item.href} href={item.href} label={item.label} pathname={pathname} />
      ))}
    </>
  );
}
