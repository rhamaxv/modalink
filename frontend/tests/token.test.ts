import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const css = readFileSync("app/globals.css", "utf8");
const designMd = readFileSync("../DESIGN.md", "utf8");

// Dicari sebagai selektor di awal baris, bukan sebagai substring: komentar di
// dalam :root menyebut [data-theme="light"] untuk menjelaskan maksudnya, dan
// indexOf biasa berhenti di komentar itu lalu memotong blok :root terlalu awal.
const posisiInversi = css.search(/^\[data-theme="light"\]/m);
const blokRoot = css.slice(css.search(/^:root/m), posisiInversi);
const blokInversi = css.slice(posisiInversi, css.indexOf("}", posisiInversi));

describe("token design", () => {
  it("defines every token DESIGN.md names", () => {
    for (const token of [
      "--paper", "--panel", "--panel-raised", "--ink", "--muted",
      "--line", "--line-strong", "--accent", "--accent-2", "--on-accent",
      "--ok", "--warn", "--danger",
      "--radius-sm", "--radius-card", "--radius-panel", "--radius-feature", "--radius-pill",
      "--measure", "--leading-display", "--leading-body",
    ]) {
      expect(css, `${token} hilang dari globals.css`).toContain(`${token}:`);
    }
  });

  it("makes dark the default and light the inversion", () => {
    // Bukan sekadar "ada dua tema": DESIGN.md menetapkan gelap sebagai keadaan
    // yang dirancang, jadi nilai gelap hidup di :root dan blok override-nya
    // adalah [data-theme="light"]. Terbalik berarti skrip no-flash di
    // layout.tsx menulis atribut yang salah dan halaman berkedip.
    expect(css).toMatch(/\[data-theme=['"]light['"]\]/);
    expect(css).not.toMatch(/\[data-theme=['"]dark['"]\]/);
    expect(posisiInversi).toBeGreaterThan(0);
    expect(blokRoot).toContain("#100F0F");
  });

  it("uses the exact hex values DESIGN.md records", () => {
    // Dibaca dari DESIGN.md, bukan diketik ulang di sini: dokumen itu yang
    // mengikat, dan test yang menyalin angkanya akan tetap hijau ketika
    // keduanya berpisah jalan.
    for (const hex of ["#100F0F", "#DDFD6C", "#AAB2FF", "#FBF9F4"]) {
      expect(designMd, `${hex} tidak ada di DESIGN.md`).toContain(hex);
      expect(css, `${hex} tidak ada di globals.css`).toContain(hex);
    }
  });

  it("never redefines the accents per theme", () => {
    // Inti bug yang pernah terkirim ke produksi: --ink berbalik saat tema
    // berganti, aksen tidak, jadi teks di atas aksen tidak boleh mengikuti
    // token yang berbalik. Blok inversi tidak boleh menyentuh ketiganya.
    for (const token of ["--accent:", "--accent-2:", "--on-accent:"]) {
      expect(blokInversi, `${token} tidak boleh didefinisikan ulang per tema`).not.toContain(token);
    }
  });

  it("keeps the decorative line separate from the interactive one", () => {
    // --line mengukur 1.46:1 dan sengaja di bawah ambang 3:1, jadi ia hanya
    // sah sebagai pemisah. Menghapus --line-strong berarti batas kontrol
    // kembali memakai nilai yang gagal, dan tidak ada yang akan menyadarinya.
    expect(css).toContain("--line-strong:");
    expect(css).toContain("#767166");
  });

  it("carries no default blue to purple gradient", () => {
    // R-01: palet berasal dari DESIGN.md, bukan dari default model.
    expect(css.toLowerCase()).not.toMatch(/linear-gradient\([^)]*#?(6366f1|8b5cf6|a855f7)/);
  });
});
