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
// bawah yang menandai area klik. AppHeader memakai konstanta yang sama untuk
// tautan publiknya (Jelajahi, Masuk, Daftar), supaya satu-satunya tempat
// ukuran ini berubah adalah di sini.
export const NAV_LINK_CLASS =
  "inline-flex min-h-[44px] items-center text-body font-medium text-ink underline underline-offset-2";

export function NavRole({ role }: { role: Role }) {
  const items = NAV_BY_ROLE[role];
  if (items.length === 0) return null;
  return (
    <>
      {items.map((item) => (
        <Link key={item.href} href={item.href} className={NAV_LINK_CLASS}>
          {item.label}
        </Link>
      ))}
    </>
  );
}
