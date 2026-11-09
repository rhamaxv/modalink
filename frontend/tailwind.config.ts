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
        "on-accent": "var(--on-accent)",
        ok: "var(--ok)",
        warn: "var(--warn)",
        danger: "var(--danger)",
      },
      // Nama bertitik "space-N" sengaja dipilih, bukan "1".."7" polos: menimpa skala
      // angka bawaan Tailwind akan membuat p-3 dan p-4 berarti ganda (bawaan vs token),
      // sehingga komponen lain diam-diam memakai angka yang salah tanpa galat apa pun.
      spacing: {
        "space-1": "var(--space-1)",
        "space-2": "var(--space-2)",
        "space-3": "var(--space-3)",
        "space-4": "var(--space-4)",
        "space-5": "var(--space-5)",
        "space-6": "var(--space-6)",
        "space-7": "var(--space-7)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        card: "var(--radius-card)",
        panel: "var(--radius-panel)",
      },
      maxWidth: {
        measure: "var(--measure)",
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
