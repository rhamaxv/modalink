"use client";

import { useLayoutEffect, useState } from "react";

const KUNCI_TEMA = "tema";

// Dibaca dalam urutan ini: atribut yang sudah ada di <html> (ditulis oleh
// skrip no-flash di layout.tsx sebelum cat pertama) lebih dipercaya daripada
// localStorage, karena skrip itu sudah menggabungkan localStorage dengan
// prefers-color-scheme. localStorage dipakai sebagai cadangan, misalnya saat
// komponen ini dirender langsung di test tanpa skrip tersebut.
function bacaTemaAwal(): "light" | "dark" {
  try {
    if (document.documentElement.dataset.theme === "dark") return "dark";
  } catch {
    // document tidak tersedia (render di server); abaikan.
  }
  try {
    if (localStorage.getItem(KUNCI_TEMA) === "dark") return "dark";
  } catch {
    // localStorage tidak tersedia; tetap pada terang.
  }
  return "light";
}

// Sakelar sungguhan, bukan <div onClick>: aria-pressed menyatakan status
// terkini, dan elemen <button> memberi aktivasi keyboard (Enter/Space) tanpa
// kode tambahan.
export function SakelarTema() {
  const [tema, setTema] = useState<"light" | "dark">(bacaTemaAwal);

  useLayoutEffect(() => {
    if (tema === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  }, [tema]);

  function alihTema() {
    const berikutnya = tema === "dark" ? "light" : "dark";
    setTema(berikutnya);
    try {
      localStorage.setItem(KUNCI_TEMA, berikutnya);
    } catch {
      // Gagal menyimpan bukan alasan untuk gagal mengganti tema.
    }
  }

  return (
    <button
      type="button"
      onClick={alihTema}
      aria-pressed={tema === "dark"}
      // border-ink, bukan border-line: border-line hanya 1.27:1 terhadap
      // bg-surface/paper, gagal ambang 3:1 untuk batas elemen interaktif.
      className="inline-flex min-h-[44px] items-center gap-ruang-2 rounded-kecil border border-ink px-ruang-3 py-ruang-2 text-sm font-medium text-ink"
    >
      {tema === "dark" ? "Tema: gelap" : "Tema: terang"}
    </button>
  );
}
