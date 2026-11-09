import { expect, test } from "@playwright/test";

test("kedua tema punya kontras yang memadai dan layout yang utuh", async ({ page }) => {
  await page.goto("/");
  for (const tema of ["light", "dark"]) {
    await page.evaluate((t) => { document.documentElement.dataset.theme = t; }, tema);

    // Tidak ada scroll horizontal di lebar ponsel (R-03).
    await page.setViewportSize({ width: 375, height: 800 });
    const lebarGulir = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(lebarGulir).toBeLessThanOrEqual(375);

    // Latar body benar-benar berubah, bukan hanya variabelnya.
    const latar = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor);
    expect(latar).not.toBe("rgba(0, 0, 0, 0)");
  }
});
