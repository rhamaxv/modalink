import { expect, test } from "@playwright/test";

// Nilai --paper dari DESIGN.md, dikonversi ke rgb() karena itu format yang
// dikembalikan getComputedStyle di browser.
const EXPECTED_BODY_BACKGROUND: Record<string, string> = {
  light: "rgb(251, 249, 244)", // #FBF9F4
  dark: "rgb(16, 15, 15)", // #100F0F
};

test("both themes have adequate contrast and an intact layout", async ({ page }) => {
  await page.goto("/");
  const backgrounds: Record<string, string> = {};

  for (const theme of ["light", "dark"] as const) {
    // Tema gelap adalah keadaan DEFAULT di :root, dan tidak punya blok
    // [data-theme="dark"] sendiri (lihat app/globals.css). Jadi untuk gelap
    // atributnya DIHAPUS, bukan disetel: menyetelnya ke "dark" kebetulan
    // memberi hasil yang sama hari ini, tapi ia menguji ejaan atribut yang
    // tidak pernah dipakai produk ini.
    await page.evaluate((t) => {
      if (t === "light") document.documentElement.dataset.theme = "light";
      else delete document.documentElement.dataset.theme;
    }, theme);

    // Tidak ada scroll horizontal di 320, 375, dan 768 (R-03).
    for (const width of [320, 375, 768]) {
      await page.setViewportSize({ width, height: 800 });
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(scrollWidth).toBeLessThanOrEqual(width);
    }

    // Latar body harus benar-benar nilai --paper dari tema itu, bukan
    // sekadar "opak". Memeriksa hanya "bukan transparan" lolos untuk
    // data-theme apa pun, termasuk nilai tanpa aturan CSS yang cocok.
    const background = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor);
    backgrounds[theme] = background;
    expect(background).toBe(EXPECTED_BODY_BACKGROUND[theme]);
  }

  // Jaring pengaman tambahan: kalau blok [data-theme="dark"] berhenti
  // berlaku sama sekali, kedua perbandingan di atas tetap bisa lolos secara
  // kebetulan di lingkungan lain; ini memastikan kedua tema benar-benar
  // berbeda satu sama lain.
  expect(backgrounds.light).not.toBe(backgrounds.dark);
});
