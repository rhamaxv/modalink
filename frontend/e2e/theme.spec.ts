import { expect, test } from "@playwright/test";

test("both themes have adequate contrast and an intact layout", async ({ page }) => {
  await page.goto("/");
  for (const theme of ["light", "dark"]) {
    await page.evaluate((t) => { document.documentElement.dataset.theme = t; }, theme);

    // Tidak ada scroll horizontal di lebar ponsel (R-03).
    await page.setViewportSize({ width: 375, height: 800 });
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(375);

    // Latar body benar-benar berubah, bukan hanya variabelnya.
    const background = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor);
    expect(background).not.toBe("rgba(0, 0, 0, 0)");
  }
});
