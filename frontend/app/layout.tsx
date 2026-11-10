import type { Metadata } from "next";
import localFont from "next/font/local";
import { AppHeader } from "@/components/AppHeader";
import "./globals.css";

// Dua keluarga, sesuai DESIGN.md: Cabinet Grotesk untuk judul, General Sans
// untuk teks. Keduanya dari Fontshare dengan ITF Free Font License.
//
// Di-host sendiri lewat next/font/local, bukan lewat CDN Fontshare: deployment
// lomba wajib tetap bisa diakses juri sampai penilaian selesai, dan satu
// dependency jaringan pihak ketiga adalah satu cara lagi ia bisa mati di saat
// yang tidak bisa kami kendalikan. Berkasnya ada di app/fonts/.
const display = localFont({
  src: [
    { path: "./fonts/CabinetGrotesk-700.woff2", weight: "700", style: "normal" },
    { path: "./fonts/CabinetGrotesk-800.woff2", weight: "800", style: "normal" },
    { path: "./fonts/CabinetGrotesk-900.woff2", weight: "900", style: "normal" },
  ],
  variable: "--font-display",
  display: "swap",
});

const teks = localFont({
  src: [
    { path: "./fonts/GeneralSans-400.woff2", weight: "400", style: "normal" },
    { path: "./fonts/GeneralSans-500.woff2", weight: "500", style: "normal" },
    { path: "./fonts/GeneralSans-600.woff2", weight: "600", style: "normal" },
    { path: "./fonts/GeneralSans-700.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Modalink",
  description: "Platform pendanaan UMKM: investor mendanai, UMKM mengajukan proposal.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // suppressHydrationWarning: skrip no-flash di bawah menulis data-theme
    // ke elemen ini sebelum React hidrasi, sengaja di luar siklus render
    // React. Tanpa ini, React membandingkan atribut <html> yang sudah
    // diubah skrip itu terhadap markup server (yang tidak mengenal
    // data-theme sama sekali) dan melaporkannya sebagai hydration mismatch,
    // walau atributnya memang benar-benar dikelola di luar React dengan
    // sengaja.
    <html lang="id" className={`${teks.variable} ${display.variable}`} suppressHydrationWarning>
      <head>
        {/*
          Tema disetel sebelum cat pertama supaya tidak ada kedipan saat
          halaman dimuat. Gelap adalah default (DESIGN.md), jadi yang ditulis
          ke <html> adalah data-theme="light" ketika pengguna memintanya, bukan
          sebaliknya. ThemeToggle membaca dan menulis kunci yang sama: "theme".
        */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function () {
              try {
                var tersimpan = localStorage.getItem("theme");
                var terang = tersimpan === "light" ||
                  (!tersimpan && window.matchMedia("(prefers-color-scheme: light)").matches);
                if (terang) document.documentElement.setAttribute("data-theme", "light");
              } catch (e) {}
            })();`,
          }}
        />
      </head>
      <body className="font-sans antialiased">
        <a
          href="#konten-utama"
          className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-sm focus:bg-ink focus:px-3 focus:py-2 focus:text-paper"
        >
          Lewati ke konten utama
        </a>
        {/*
          Header bersama (Fase 11, Task 11): sebelum ini ThemeToggle hanya
          dirender di "/", jadi siapa pun yang membuka halaman lain langsung
          tidak bisa mengubah tema di sana. Dirender satu kali di sini
          supaya hadir di seluruh route tanpa menambal tiap halaman satu
          per satu.
        */}
        <AppHeader />
        <main id="konten-utama">{children}</main>
      </body>
    </html>
  );
}
