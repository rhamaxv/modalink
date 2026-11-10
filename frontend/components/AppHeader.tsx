"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ThemeToggle } from "@/components/ThemeToggle";
import { NavRole, NAV_LINK_CLASS } from "@/components/NavRole";
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
  // Panel nav tertutup secara default di semua lebar layar, termasuk
  // desktop: di atas breakpoint md kelas `md:flex` pada <nav> yang menimpa
  // `hidden`, jadi nilai state ini sendiri tidak pernah dibaca di sana.
  // Aman diinisialisasi false tanpa membaca apa pun milik klien, tidak
  // seperti `auth` di atas yang harus "checking" dulu (lihat komentar di
  // bawah): status buka/tutup menu bukan sesuatu yang server tahu atau
  // tebak keliru, jadi tidak ada risiko hidrasi di sini.
  const [menuOpen, setMenuOpen] = useState(false);

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
    setMenuOpen(false);
    router.push("/");
  }

  function tutupMenu() {
    setMenuOpen(false);
  }

  return (
    <header className="sticky top-0 z-10 border-b border-line bg-paper">
      {/*
        Dua baris yang digabung jadi satu lewat flex-wrap, bukan dua
        <div> bertingkat: baris pertama (merek + tombol Menu) selalu
        tampil dan tidak pernah lebih dari satu baris tinggi. Audit
        browser menemukan header sticky tumbuh sampai 161px di 320px
        lebar karena ia dulu menyelesaikan mobile dengan membungkus baris
        nav desktop apa adanya. <nav> di bawah memakai `hidden` sampai
        menuOpen aktif ATAU lebar layar mencapai md, dan w-full memaksanya
        pindah ke baris sendiri saat memang ditampilkan, jadi tinggi
        default (tertutup, di bawah md) tetap satu baris.
      */}
      <div className="mx-auto flex w-full max-w-[72rem] flex-wrap items-center justify-between gap-space-3 px-space-3 py-space-2">
        <Link href="/" className="text-label font-semibold text-ink" onClick={tutupMenu}>
          Modalink
        </Link>
        <button
          type="button"
          onClick={() => setMenuOpen((terbuka) => !terbuka)}
          aria-expanded={menuOpen}
          aria-controls="nav-utama"
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-sm border border-line-strong px-space-3 text-body font-medium text-ink md:hidden"
        >
          {menuOpen ? "Tutup" : "Menu"}
        </button>
        <nav
          id="nav-utama"
          className={`${menuOpen ? "flex" : "hidden"} w-full flex-col items-start gap-space-3 border-t border-line pt-space-3 md:flex md:w-auto md:flex-row md:items-center md:gap-space-4 md:border-t-0 md:pt-0`}
        >
          <Link href="/jelajah" className={NAV_LINK_CLASS} onClick={tutupMenu}>
            Jelajahi
          </Link>
          {auth.status === "signed-in" && <NavRole role={auth.user.role} />}
          {auth.status === "guest" && (
            <>
              <Link href="/masuk" className={NAV_LINK_CLASS} onClick={tutupMenu}>
                Masuk
              </Link>
              <Link href="/daftar" className={NAV_LINK_CLASS} onClick={tutupMenu}>
                Daftar
              </Link>
            </>
          )}
          {auth.status === "signed-in" && (
            <button
              type="button"
              onClick={keluar}
              className="inline-flex min-h-[44px] items-center rounded-sm border border-ink px-space-3 py-space-2 text-body font-medium text-ink"
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
