import type { Config } from "tailwindcss";
import defaultTheme from "tailwindcss/defaultTheme";

// Tailwind tidak mendefinisikan warna atau spasi sendiri di sini: setiap nilai
// menunjuk ke variabel CSS di app/globals.css, supaya token tetap satu sumber
// kebenaran. Mengubah DESIGN.md berarti mengubah globals.css, bukan berkas ini.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "var(--paper)",
        panel: "var(--panel)",
        "panel-raised": "var(--panel-raised)",
        ink: "var(--ink)",
        muted: "var(--muted)",
        line: "var(--line)",
        // Dipisah dari `line` dengan sengaja: `line` mengukur 1.46:1 dan hanya
        // sah sebagai pemisah dekoratif. Batas kontrol interaktif memakai yang
        // ini (3.94:1), karena satu tombol pernah lolos review dengan 1.27:1.
        "line-strong": "var(--line-strong)",
        accent: "var(--accent)",
        "accent-2": "var(--accent-2)",
        "on-accent": "var(--on-accent)",
        // Dipakai sebagai warna teks, bukan latar. Berbalik ikut tema karena
        // ia duduk di atas --paper yang juga berbalik; bandingkan on-accent
        // yang justru tidak boleh berbalik.
        "accent-text": "var(--accent-text)",
        "accent-2-text": "var(--accent-2-text)",
        ok: "var(--ok)",
        warn: "var(--warn)",
        danger: "var(--danger)",
      },
      // Nama berawalan "space-N", bukan "1".."7" polos: menimpa skala angka
      // bawaan Tailwind akan membuat p-3 dan p-4 berarti ganda (bawaan vs
      // token), sehingga komponen lain diam-diam memakai angka yang salah
      // tanpa galat apa pun.
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
        feature: "var(--radius-feature)",
        pill: "var(--radius-pill)",
      },
      maxWidth: { measure: "var(--measure)" },
      fontFamily: {
        sans: ["var(--font-sans)", ...defaultTheme.fontFamily.sans],
        display: ["var(--font-display)", "var(--font-sans)", ...defaultTheme.fontFamily.sans],
      },
      // Skala DESIGN.md sebagai token, bukan nilai yang diketik ulang di tiap
      // komponen: leading 1.10 pada judul adalah separuh dari efeknya, dan ia
      // hilang begitu seseorang memakai text-5xl bawaan Tailwind yang
      // leading-nya lebih longgar.
      fontSize: {
        label: ["0.8125rem", { lineHeight: "1.4" }],
        body: ["1rem", { lineHeight: "var(--leading-body)" }],
        "card-title": ["1.25rem", { lineHeight: "1.3" }],
        "amount-sm": ["1.75rem", { lineHeight: "1.1", fontWeight: "700" }],
        section: ["clamp(2rem, 4vw, 2.75rem)", { lineHeight: "var(--leading-display)", fontWeight: "700" }],
        page: ["clamp(2.75rem, 6vw, 4.5rem)", { lineHeight: "var(--leading-display)", fontWeight: "700" }],
        amount: ["clamp(3rem, 7vw, 5rem)", { lineHeight: "1", fontWeight: "800" }],
      },
    },
  },
  plugins: [],
};

export default config;
