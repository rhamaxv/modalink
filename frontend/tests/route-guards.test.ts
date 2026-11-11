import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// Setiap segmen route yang khusus satu peran WAJIB punya layout.tsx yang
// memasang RequireRole untuk peran itu.
//
// Pagar ini ada karena lubang yang sungguh terjadi: app/investor/ punya
// layout penjaganya, app/umkm/ tidak punya sama sekali, dan akibatnya
// seluruh /umkm/* berjalan tanpa pemeriksaan peran. Penyebabnya tercatat di
// komentar e2e/auth-guard.spec.ts: kedua segmen dibangun di worktree
// berbeda, guard yang satu diasumsikan sama dengan yang lain, dan tidak ada
// yang memeriksanya setelah digabung.
//
// Diperiksa dari SUMBER, bukan dengan merender: yang dijaga di sini adalah
// keberadaan penjaga itu sendiri, yang justru tidak terlihat oleh test
// manapun yang hanya merender halaman di dalamnya.
const SEGMEN_PERAN: Record<string, string> = {
  investor: "investor",
  umkm: "umkm",
};

describe("every role-scoped route segment is guarded at its own layout", () => {
  it.each(Object.entries(SEGMEN_PERAN))(
    "app/%s has a layout that requires the %s role",
    (segmen, peran) => {
      const layout = path.join("app", segmen, "layout.tsx");
      expect(existsSync(layout), `${layout} tidak ada: segmen ini tanpa pagar peran`).toBe(
        true,
      );
      const sumber = readFileSync(layout, "utf8");
      expect(sumber).toContain("RequireRole");
      expect(sumber).toMatch(new RegExp(`role=["']${peran}["']`));
    },
  );

  it("covers every role segment that actually exists under app/", () => {
    // Kalau segmen peran baru ditambahkan (misal app/community/), daftar di
    // atas harus ikut bertambah. Tanpa baris ini, pagar ini diam-diam
    // berhenti menutupi segmen yang paling baru.
    const adaDiDisk = readdirSync("app", { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => d.name)
      .filter((nama) => Object.keys(SEGMEN_PERAN).includes(nama));
    expect(adaDiDisk.sort()).toEqual(Object.keys(SEGMEN_PERAN).sort());
  });
});
