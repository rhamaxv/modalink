import type { Config } from "tailwindcss";
import defaultTheme from "tailwindcss/defaultTheme";

// Tailwind tidak mendefinisikan warna atau spasi sendiri di sini: setiap nilai
// menunjuk ke variabel CSS di app/globals.css, supaya token tetap satu sumber
// kebenaran. Mengubah DESIGN.md berarti mengubah globals.css, bukan berkas ini.
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "var(--ink)",
        paper: "var(--paper)",
        surface: "var(--surface)",
        muted: "var(--muted)",
        line: "var(--line)",
        accent: "var(--accent)",
        ok: "var(--ok)",
        warn: "var(--warn)",
        danger: "var(--danger)",
      },
      // Nama bertitik "ruang-N" sengaja dipilih, bukan "1".."7" polos: menimpa skala
      // angka bawaan Tailwind akan membuat p-3 dan p-4 berarti ganda (bawaan vs token),
      // sehingga komponen lain diam-diam memakai angka yang salah tanpa galat apa pun.
      spacing: {
        "ruang-1": "var(--ruang-1)",
        "ruang-2": "var(--ruang-2)",
        "ruang-3": "var(--ruang-3)",
        "ruang-4": "var(--ruang-4)",
        "ruang-5": "var(--ruang-5)",
        "ruang-6": "var(--ruang-6)",
        "ruang-7": "var(--ruang-7)",
      },
      borderRadius: {
        kecil: "var(--radius-kecil)",
        kartu: "var(--radius-kartu)",
        panel: "var(--radius-panel)",
      },
      maxWidth: {
        baca: "var(--lebar-baca)",
      },
      // "--font-sans" diisi next/font di app/layout.tsx; fallback dipakai hanya
      // selama font belum selesai dimuat.
      fontFamily: {
        sans: ["var(--font-sans)", ...defaultTheme.fontFamily.sans],
      },
    },
  },
  plugins: [],
};

export default config;
