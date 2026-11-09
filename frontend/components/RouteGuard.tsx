"use client";

import { useEffect, useState } from "react";
import { notFound, usePathname, useRouter } from "next/navigation";
import { fetchCurrentUser, type Role } from "@/lib/auth";

type GuardState = "checking" | "allowed" | "mismatch";

type RequireRoleProps = {
  role: Role;
  children: React.ReactNode;
};

// Dipasang satu kali di layout.tsx segmen yang berperan (misal
// app/investor/layout.tsx), bukan diulang di setiap page.tsx di bawahnya:
// satu client boundary per segmen, bukan satu per halaman. ".claude/skills/
// nextjs-app-conventions/SKILL.md" meminta "use client" di komponen
// terkecil yang membutuhkannya, dan untuk penjaga route, komponen terkecil
// yang masih menutupi seluruh segmen adalah layout-nya, bukan tiap page.
export function RequireRole({ role, children }: RequireRoleProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [state, setState] = useState<GuardState>("checking");

  useEffect(() => {
    let dibatalkan = false;
    fetchCurrentUser().then((user) => {
      if (dibatalkan) return;
      if (!user) {
        // Akun belum masuk: arahkan ke /masuk sambil membawa tujuan asal
        // lewat query "next". Membuang tujuan asal memaksa pengguna
        // menavigasi ulang dari nol begitu berhasil masuk.
        router.replace(`/masuk?next=${encodeURIComponent(pathname)}`);
        return;
      }
      if (user.role !== role) {
        // 404, bukan 403: mengikuti pola yang sudah dipakai backend
        // (.claude/prd/10-api-contract.md). 403 memberi tahu pengunjung
        // bahwa halaman itu memang ada, hanya ditolak; investor yang salah
        // membuka route UMKM tidak perlu tahu sebanyak itu.
        setState("mismatch");
        return;
      }
      setState("allowed");
    });
    return () => {
      dibatalkan = true;
    };
  }, [role, router, pathname]);

  // notFound() wajib dipanggil di badan render, bukan di dalam efek:
  // ia melempar error bertanda khusus yang ditangkap NotFoundBoundary
  // Next.js, dan boundary itu hanya mengawasi error yang terjadi selama
  // render/commit, bukan error di dalam Promise terpisah. Dibuktikan
  // langsung di browser sungguhan (e2e/auth-guard.spec.ts): memanggilnya
  // dari dalam .then() hanya menghasilkan error React tak tertangani,
  // bukan halaman 404 Next.js yang sesungguhnya.
  if (state === "mismatch") notFound();
  // "checking": tidak merender apa pun dulu, supaya konten terlindungi
  // tidak pernah sempat berkedip tampil sebelum keputusan redirect/404
  // selesai diambil.
  if (state !== "allowed") return null;
  return <>{children}</>;
}
