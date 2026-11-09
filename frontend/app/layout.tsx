import type { Metadata } from "next";
import { Source_Sans_3 } from "next/font/google";
import "./globals.css";

// Satu keluarga sans humanis untuk seluruh produk (DESIGN.md). Source Sans 3
// dipilih dari tiga kandidat yang disebut DESIGN.md (Source Sans 3, Public Sans,
// IBM Plex Sans): bentuk hurufnya terbuka dan netral, cocok untuk formulir
// panjang berbahasa Indonesia, dan tidak membawa asosiasi merek seperti IBM
// Plex (identitas IBM) atau Public Sans (identitas pemerintah AS/USWDS).
const sansHumanis = Source_Sans_3({
  subsets: ["latin"],
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
    <html lang="id" className={sansHumanis.variable}>
      <head>
        {/*
          Tema disetel sebelum cat pertama supaya tidak ada kedipan dari terang
          ke gelap saat halaman dimuat. ThemeToggle menulis dan membaca kunci
          localStorage yang sama: "theme", nilai "light"/"dark".
        */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function () {
              try {
                var tersimpan = localStorage.getItem("theme");
                var gelap = tersimpan === "dark" ||
                  (!tersimpan && window.matchMedia("(prefers-color-scheme: dark)").matches);
                if (gelap) document.documentElement.setAttribute("data-theme", "dark");
              } catch (e) {}
            })();`,
          }}
        />
      </head>
      <body className="font-sans antialiased">
        <a
          href="#konten-utama"
          className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-kecil focus:bg-ink focus:px-3 focus:py-2 focus:text-paper"
        >
          Lewati ke konten utama
        </a>
        <main id="konten-utama">{children}</main>
      </body>
    </html>
  );
}
