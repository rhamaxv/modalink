import { expect, test } from "@playwright/test";

// Menjaga dua hal yang tidak bisa diperiksa oleh test unit jsdom, karena
// keduanya hanya muncul lewat SSR + hidrasi sungguhan di browser:
//
// 1. Skrip no-flash di app/layout.tsx membaca kunci localStorage "theme"
//    sebelum cat pertama. Kalau kuncinya tertukar kembali jadi "tema",
//    seluruh test unit dan e2e lain tetap hijau karena mereka tidak
//    menjalankan skrip inline itu; hanya test ini yang menyuntikkan
//    localStorage lalu memeriksa <html> segera setelah navigasi.
// 2. ThemeToggle tidak boleh membaca document/localStorage langsung di
//    initializer state-nya: itu membuat render pertama di klien berbeda
//    dari HTML server begitu skrip no-flash sudah menyalakan data-theme,
//    dan React membuang seluruh hasil hidrasi (error #418).

test("reads the stored theme key before first paint, with no hydration error", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => consoleErrors.push(err.message));

  await page.addInitScript(() => localStorage.setItem("theme", "dark"));
  await page.goto("/");

  // Diperiksa sesegera mungkin setelah goto resolve, bukan menunggu hidrasi
  // React: ini membuktikan skrip inline sendiri yang menyalakan atributnya.
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  await page.waitForTimeout(300);
  expect(consoleErrors.join("\n")).not.toMatch(/Hydration|error #418|did not match/i);

  const button = page.getByRole("button", { name: /tema/i });
  await expect(button).toHaveAttribute("aria-pressed", "true");
});

test("stays light with no stored key and no OS dark preference, with no hydration error", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => consoleErrors.push(err.message));

  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/");

  await expect(page.locator("html")).not.toHaveAttribute("data-theme", "dark");

  await page.waitForTimeout(300);
  expect(consoleErrors.join("\n")).not.toMatch(/Hydration|error #418|did not match/i);
});

test("applies dark from the OS preference with no hydration error", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => consoleErrors.push(err.message));

  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");

  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  await page.waitForTimeout(300);
  expect(consoleErrors.join("\n")).not.toMatch(/Hydration|error #418|did not match/i);

  const button = page.getByRole("button", { name: /tema/i });
  await expect(button).toHaveAttribute("aria-pressed", "true");
});
