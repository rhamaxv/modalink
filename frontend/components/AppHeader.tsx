"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ThemeToggle } from "@/components/ThemeToggle";
import { NavRole } from "@/components/NavRole";
import { clearToken, fetchCurrentUser, getToken, type CurrentUser } from "@/lib/auth";

type AuthState =
  | { status: "checking" }
  | { status: "guest" }
  | { status: "signed-in"; user: CurrentUser };

// Header bersama (Fase 11, Task 11), dirender sekali di layout.tsx supaya
// muncul di setiap route, termasuk ThemeToggle: sebelum task ini ia hanya
// ada di "/", jadi siapa pun yang membuka halaman lain langsung tidak bisa
// mengubah tema di sana (temuan reviewer yang sengaja ditunda ke task ini).
//
// Keadaan "checking" (GET /auth/me belum selesai) sengaja tidak menampilkan
// apa pun di slot nav peran: tidak Masuk/Daftar, dan tidak nav peran. Kalau
// slot itu lebih dulu menampilkan Masuk/Daftar lalu berganti ke nav peran
// begitu /auth/me selesai, pengguna yang sudah masuk melihat kedipan
// keadaan yang salah sesaat sebelum keadaan yang benar muncul. Jelajahi dan
// ThemeToggle tidak menunggu apa pun, jadi tetap tampil dari awal.
//
// State awal SELALU "checking", bukan membaca getToken() di initializer
// useState seperti sebelumnya: initializer itu berjalan juga saat SSR (lewat
// next dev/next start), di mana localStorage tidak ada dan getToken() selalu
// null -> "guest", sedangkan render pertama di klien sungguh membaca
// localStorage sungguhan. Untuk akun yang sedang masuk, HTML server
// ("guest": tautan Masuk/Daftar) berbeda dari tebakan pertama klien
// ("checking": slot nav kosong), dan React membuang hasil hidrasi
// (laporan Fase 11 Task 12: dibuktikan e2e lewat navigasi penuh/reload
// sungguhan sebagai akun yang sudah masuk, bukan navigasi client-side yang
// tidak pernah memicu SSR ulang). Sama seperti ThemeToggle (lihat
// e2e/no-flash.spec.ts): initializer tidak boleh membaca apa pun yang hanya
// ada di klien.
export function AppHeader() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthState>({ status: "checking" });

  useEffect(() => {
    if (!getToken()) {
      setAuth({ status: "guest" });
      return;
    }
    let dibatalkan = false;
    fetchCurrentUser().then((user) => {
      if (dibatalkan) return;
      setAuth(user ? { status: "signed-in", user } : { status: "guest" });
    });
    return () => {
      dibatalkan = true;
    };
  }, []);

  function keluar() {
    clearToken();
    setAuth({ status: "guest" });
    router.push("/");
  }

  return (
    <header className="sticky top-0 z-10 border-b border-line bg-paper">
      <div className="mx-auto flex w-full max-w-[72rem] flex-wrap items-center justify-between gap-space-3 px-space-3 py-space-3">
        <Link href="/" className="text-label font-semibold text-ink">
          Modalink
        </Link>
        <nav className="flex flex-wrap items-center gap-space-4">
          <Link href="/jelajah" className="text-base font-medium text-ink underline">
            Jelajahi
          </Link>
          {auth.status === "signed-in" && <NavRole role={auth.user.role} />}
          {auth.status === "guest" && (
            <>
              <Link href="/masuk" className="text-base font-medium text-ink underline">
                Masuk
              </Link>
              <Link href="/daftar" className="text-base font-medium text-ink underline">
                Daftar
              </Link>
            </>
          )}
          {auth.status === "signed-in" && (
            <button
              type="button"
              onClick={keluar}
              className="min-h-[44px] rounded-sm border border-ink px-space-3 py-space-2 text-base font-medium text-ink"
            >
              Keluar
            </button>
          )}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
