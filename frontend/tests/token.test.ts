import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const css = readFileSync("app/globals.css", "utf8");

describe("token design", () => {
  it("mendefinisikan seluruh token dari DESIGN.md", () => {
    for (const token of ["--ink", "--paper", "--surface", "--muted",
                         "--line", "--accent", "--ok", "--warn", "--danger"]) {
      expect(css).toContain(`${token}:`);
    }
  });

  it("mendefinisikan ulang token untuk mode gelap", () => {
    expect(css).toMatch(/\[data-theme=['"]dark['"]\]/);
  });

  it("memakai nilai hex persis seperti di DESIGN.md", () => {
    expect(css).toContain("#FFC94A");   // accent
    expect(css).toContain("#FBF9F4");   // paper terang
    expect(css).toContain("#141310");   // paper gelap
  });

  it("tidak memuat warna gradien biru ke ungu", () => {
    // R-01: palet berasal dari DESIGN.md, bukan dari default model.
    expect(css.toLowerCase()).not.toMatch(/linear-gradient\([^)]*#?(6366f1|8b5cf6|a855f7)/);
  });
});
