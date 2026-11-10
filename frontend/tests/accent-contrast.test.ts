import { readFileSync } from "node:fs";
import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// Aturan paling keras di DESIGN.md: teks di atas --accent selalu gelap.
// Pagar sebelumnya menggeledah string "white" dan "#fff" dan melaporkan bersih,
// padahal `text-ink` berbalik menjadi #F2EEE6 di tema gelap dan menghasilkan
// 1.32:1 di atas kuning -- lebih buruk daripada putih 1.53:1 yang dilarang.
// Jadi yang diperiksa di sini bukan ejaannya, tapi apakah tokennya berbalik.

function luminance(hex: string): number {
  const ch = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = ch.map((c) =>
    c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4,
  ) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

function berkas(dir: string): string[] {
  return readdirSync(dir).flatMap((nama) => {
    const p = join(dir, nama);
    return statSync(p).isDirectory() ? berkas(p) : p.endsWith(".tsx") ? [p] : [];
  });
}

const css = readFileSync("app/globals.css", "utf8");

function nilaiToken(nama: string, temaInversi: boolean): string | null {
  // Gelap adalah default di :root; blok inversinya sekarang [data-theme="light"].
  const sumber = temaInversi ? css.slice(css.indexOf('[data-theme="light"]')) : css;
  const m = new RegExp(`--${nama}:\\s*(#[0-9A-Fa-f]{6})`).exec(sumber);
  return m?.[1] ?? null;
}

describe("kontras teks di atas aksen", () => {
  it("keeps the on-accent token stable across both themes", () => {
    const dasar = nilaiToken("on-accent", false);
    const inversi = nilaiToken("on-accent", true);
    expect(dasar).not.toBeNull();
    // Tidak didefinisikan ulang di blok inversi: itu seluruh maksud tokennya.
    // Berlaku untuk kedua aksen, karena keduanya tidak pernah berbalik.
    expect(inversi).toBe(dasar);
    expect(nilaiToken("accent", true)).toBe(nilaiToken("accent", false));
    expect(nilaiToken("accent-2", true)).toBe(nilaiToken("accent-2", false));
  });

  it("measures both accent pairs above the WCAG AA threshold", () => {
    const teks = nilaiToken("on-accent", false)!;
    for (const nama of ["accent", "accent-2"]) {
      expect(ratio(teks, nilaiToken(nama, false)!)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("rejects pairing an accent surface with a token that flips per theme", () => {
    const pelanggar: string[] = [];
    for (const p of [...berkas("app"), ...berkas("components")]) {
      for (const baris of readFileSync(p, "utf8").split("\n")) {
        if (!baris.includes("bg-accent") && !baris.includes("bg-accent-2")) continue;
        if (/\btext-(ink|paper|white)\b/.test(baris)) pelanggar.push(`${p}: ${baris.trim()}`);
      }
    }
    expect(pelanggar).toEqual([]);
  });

  it("proves the flipping token would actually have failed", () => {
    // Nilai yang dilarang DESIGN.md, dihitung ulang di sini supaya angkanya
    // tidak hanya ada di komentar. Putih di atas kedua aksen lebih buruk
    // daripada putih-pada-kuning 1.53:1 yang arah sebelumnya sudah melarang.
    expect(ratio("#FFFFFF", "#DDFD6C")).toBeLessThan(1.53);
    expect(ratio("#FFFFFF", "#AAB2FF")).toBeLessThan(2.1);
    expect(ratio("#100F0F", "#DDFD6C")).toBeGreaterThan(16);
  });
});
