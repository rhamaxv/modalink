import { defineConfig, devices } from "@playwright/test";

const PORT = 3100;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  // Satu worker, dan ini bukan kehati-hatian berlebihan.
  //
  // Seluruh spec di folder ini memukul SATU backend dan SATU database yang
  // sama, dengan tiga hal yang saling mengganggu begitu dijalankan paralel:
  // rate limiter per-IP (POST /auth/register 5 per menit, app/middleware.py),
  // akun demo yang dipakai bersama oleh alur-penuh dan alur-pasar, serta
  // status proposal yang bergerak berurutan sepanjang satu skenario.
  // Dijalankan dengan dua worker, ketiganya langsung bertabrakan dan
  // menghasilkan kegagalan yang tidak ada hubungannya dengan kode.
  workers: 1,
  webServer: {
    // Build PRODUKSI, bukan `next dev`, dan bedanya bukan selera.
    //
    // Diukur di mesin ini: dev server mengirim 1.737 KB JavaScript tanpa
    // minifikasi dan memuat /jelajah dalam 3.604 ms; build produksi mengirim
    // 125 KB dan memuat dalam 928 ms. Spec di folder ini berpindah halaman
    // puluhan kali, jadi selisih itu berlipat: satu spec yang sama berjalan
    // 15 menit di dev. Build produksi juga yang lebih dekat dengan apa yang
    // dibuka juri, jadi yang diuji memang yang dikirim.
    //
    // BACKEND_PROXY_URL disetel di sini supaya `make test-e2e` jalan apa
    // adanya; tanpa itu rewrite /api/v1 di next.config.ts tidak aktif dan
    // setiap fetch 404 (lihat komentar di next.config.ts).
    command: `npx next build && npx next start -p ${PORT}`,
    env: { BACKEND_PROXY_URL: process.env.BACKEND_PROXY_URL ?? "http://localhost:8000" },
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 300_000,
  },
  use: {
    baseURL: `http://localhost:${PORT}`,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
