import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Wajib untuk frontend/Dockerfile: tanpa ini, `next build` tidak menghasilkan
  // folder .next/standalone yang disalin ke image runner, dan build image gagal.
  output: "standalone",
};

export default nextConfig;
