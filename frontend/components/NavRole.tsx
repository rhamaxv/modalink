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

export function NavRole({ role }: { role: Role }) {
  const items = NAV_BY_ROLE[role];
  if (items.length === 0) return null;
  return (
    <>
      {items.map((item) => (
        <Link key={item.href} href={item.href} className="text-base font-medium text-ink underline">
          {item.label}
        </Link>
      ))}
    </>
  );
}
