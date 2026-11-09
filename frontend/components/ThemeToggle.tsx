"use client";

import { useLayoutEffect, useState } from "react";

const THEME_STORAGE_KEY = "theme";

// Dibaca dalam urutan ini: atribut yang sudah ada di <html> (ditulis oleh
// skrip no-flash di layout.tsx sebelum cat pertama) lebih dipercaya daripada
// localStorage, karena skrip itu sudah menggabungkan localStorage dengan
// prefers-color-scheme. localStorage dipakai sebagai cadangan, misalnya saat
// komponen ini dirender langsung di test tanpa skrip tersebut.
function readInitialTheme(): "light" | "dark" {
  try {
    if (document.documentElement.dataset.theme === "dark") return "dark";
  } catch {
    // document tidak tersedia (render di server); abaikan.
  }
  try {
    if (localStorage.getItem(THEME_STORAGE_KEY) === "dark") return "dark";
  } catch {
    // localStorage tidak tersedia; tetap pada terang.
  }
  return "light";
}

// Sakelar sungguhan, bukan <div onClick>: aria-pressed menyatakan status
// terkini, dan elemen <button> memberi aktivasi keyboard (Enter/Space) tanpa
// kode tambahan.
export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">(readInitialTheme);

  useLayoutEffect(() => {
    if (theme === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
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
      // bg-surface/paper, gagal ambang 3:1 untuk batas elemen interaktif.
      className="inline-flex min-h-[44px] items-center gap-ruang-2 rounded-kecil border border-ink px-ruang-3 py-ruang-2 text-sm font-medium text-ink"
    >
      {theme === "dark" ? "Tema: gelap" : "Tema: terang"}
    </button>
  );
}
