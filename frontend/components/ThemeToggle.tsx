"use client";

import { useEffect, useState } from "react";

const THEME_STORAGE_KEY = "theme";

// Dibaca dalam urutan ini: atribut yang sudah ada di <html> (ditulis oleh
// skrip no-flash di layout.tsx sebelum cat pertama) lebih dipercaya daripada
// localStorage, karena skrip itu sudah menggabungkan localStorage dengan
// prefers-color-scheme. localStorage dipakai sebagai cadangan, misalnya saat
// komponen ini dirender langsung di test tanpa skrip tersebut.
function readStoredTheme(): "light" | "dark" {
  try {
    if (document.documentElement.dataset.theme === "light") return "light";
  } catch {
    // document tidak tersedia (render di server); abaikan.
  }
  try {
    if (localStorage.getItem(THEME_STORAGE_KEY) === "light") return "light";
  } catch {
    // localStorage tidak tersedia; tetap pada gelap.
  }
  return "dark";
}

// Sakelar sungguhan, bukan <div onClick>: aria-pressed menyatakan status
// terkini, dan elemen <button> memberi aktivasi keyboard (Enter/Space) tanpa
// kode tambahan.
export function ThemeToggle() {
  // State awal SELALU "dark", sama persis dengan yang dirender server
  // (document dan localStorage tidak ada di sana) dan sama dengan default
  // DESIGN.md. Memanggil readStoredTheme langsung di initializer useState
  // membuat render pertama di klien berbeda dari HTML yang dikirim server
  // begitu skrip no-flash sudah menyalakan data-theme="light" sebelum
  // hidrasi, dan React menolak hasilnya (error #418), membuang seluruh HTML
  // server lalu merender ulang dari nol. Nilai sungguhan baru dibaca di
  // useEffect di bawah, setelah hidrasi selesai: warna halaman sudah benar
  // sejak awal karena skrip no-flash mengurusnya di <html>, yang menyusul
  // belakangan hanya label dan aria-pressed tombol.
  const [theme, setTheme] = useState<"light" | "dark">("dark");

  useEffect(() => {
    const stored = readStoredTheme();
    if (stored === "light") setTheme("light");
  }, []);

  useEffect(() => {
    if (theme === "light") {
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  }, [theme]);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // Gagal menyimpan bukan alasan untuk gagal mengganti tema.
    }
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-pressed={theme === "dark"}
      // border-ink, bukan border-line: border-line hanya 1.27:1 terhadap
      // bg-panel/paper, gagal ambang 3:1 untuk batas elemen interaktif.
      className="inline-flex min-h-[44px] items-center gap-space-2 rounded-sm border border-ink px-space-3 py-space-2 text-body font-medium text-ink"
    >
      {theme === "dark" ? "Tema: gelap" : "Tema: terang"}
    </button>
  );
}
