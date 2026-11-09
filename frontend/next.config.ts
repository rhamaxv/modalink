import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Wajib untuk frontend/Dockerfile: tanpa ini, `next build` tidak menghasilkan
  // folder .next/standalone yang disalin ke image runner, dan build image gagal.
  output: "standalone",

  // Hanya dipakai e2e/alur-penuh.spec.ts (Fase 11 Task 12) lewat
  // BACKEND_PROXY_URL, bukan produksi: di produksi, Caddy yang menyatukan
  // origin frontend dan backend (lihat Caddyfile), dan env var ini memang
  // tidak pernah disetel di sana. Tanpa rewrite ini, menjalankan backend
  // sungguhan di port lain membuat setiap fetch dari browser jadi lintas
  // origin, dan backend tidak memasang middleware CORS (bukan bug: di balik
  // Caddy, origin memang selalu sama) -- preflight OPTIONS-nya dibalas 405
  // oleh FastAPI dan fetch gagal dengan galat jaringan, dibuktikan sungguh
  // terjadi saat menjalankan e2e task ini terhadap backend terpisah.
  async rewrites() {
    const backend = process.env.BACKEND_PROXY_URL;
    if (!backend) return [];
    return [{ source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*` }];
  },
};

export default nextConfig;
