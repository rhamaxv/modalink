import { expect, test, type Page } from "@playwright/test";

// Rute terlindungi sungguhan yang sudah ada di worktree ini. app/umkm/* ada
// di brief yang sama tapi dibangun stream lain di worktree lain (f11-c), dan
// berkas-berkasnya belum ada di sini, jadi guard RequireRole untuk peran
// "umkm" dibuktikan lewat endpoint yang sama (RequireRole, lib/auth.ts)
// dipakai pada rute yang benar-benar ada: /investor/campaign dengan peran
// akun yang BUKAN investor. Mekanismenya identik; hanya rute contohnya beda.
const PROTECTED_INVESTOR_ROUTE = "/investor/campaign";

function routeAuth(page: Page, role: "investor" | "umkm" | "community" | null) {
  return page.route("**/api/v1/**", async (route) => {
    const url = route.request().url();
    const json = (body: unknown, httpStatus = 200) =>
      route.fulfill({ status: httpStatus, contentType: "application/json", body: JSON.stringify(body) });

    if (url.endsWith("/auth/me")) {
      if (!role) {
        return json({ error: { code: "tidak_sah", message: "Token tidak sah." } }, 401);
      }
      return json({
        id: "u1",
        email: "pengguna@contoh.id",
        name: "Pengguna Uji",
        role,
        created_at: "2026-01-01T00:00:00Z",
      });
    }
    if (url.endsWith("/auth/login")) {
      return json({ access_token: "token-e2e" });
    }
    if (url.endsWith("/campaigns")) {
      return json({ items: [] });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ error: { code: "tidak_ditemukan", message: "Tidak ditemukan." } }),
    });
  });
}

test("a signed-out visitor is redirected to /masuk, carrying the originally intended page", async ({ page }) => {
  await routeAuth(page, null);
  await page.goto(PROTECTED_INVESTOR_ROUTE);
  await expect(page).toHaveURL(`/masuk?next=${encodeURIComponent(PROTECTED_INVESTOR_ROUTE)}`);
  await expect(page.getByRole("heading", { level: 1, name: "Masuk" })).toBeVisible();
});

test("signing in from that redirect returns to the originally intended page, not to /", async ({ page }) => {
  await routeAuth(page, "investor");
  await page.goto(`/masuk?next=${encodeURIComponent(PROTECTED_INVESTOR_ROUTE)}`);
  await page.getByLabel("Email").fill("investor@contoh.id");
  await page.getByLabel("Password").fill("sandi-aman-123");
  await page.getByRole("button", { name: "Masuk" }).click();
  await expect(page).toHaveURL(PROTECTED_INVESTOR_ROUTE);
});

test("a role mismatch shows a not-found page, not a forbidden one", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("modalink_token", "token-e2e"));
  await routeAuth(page, "umkm");
  const response = await page.goto(PROTECTED_INVESTOR_ROUTE);
  await expect(page.getByText(/404|tidak ditemukan/i)).toBeVisible();
  // RequireRole menolak lewat notFound(), bukan dengan menampilkan pesan
  // "akses ditolak": investor yang salah peran tidak diberi tahu bahwa
  // halamannya memang ada, hanya ditolak (10-api-contract.md: 403 vs 404).
  expect(response?.status()).not.toBe(403);
});

test("a signed-in account matching the role reaches the real page", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("modalink_token", "token-e2e"));
  await routeAuth(page, "investor");
  await page.goto(PROTECTED_INVESTOR_ROUTE);
  await expect(page.getByRole("heading", { level: 1, name: "Campaign saya" })).toBeVisible();
});

test("a malformed stored token (the literal string \"undefined\") is treated as signed out", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("modalink_token", "undefined"));
  let calledAuthMe = false;
  await page.route("**/api/v1/auth/me", async (route) => {
    calledAuthMe = true;
    await route.fulfill({ status: 401, contentType: "application/json", body: "{}" });
  });
  await page.goto(PROTECTED_INVESTOR_ROUTE);
  await expect(page).toHaveURL(`/masuk?next=${encodeURIComponent(PROTECTED_INVESTOR_ROUTE)}`);
  expect(calledAuthMe).toBe(false);
});

test("signing out clears the token and sends the visitor to /, and the protected route then redirects again", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("modalink_token", "token-e2e"));
  await routeAuth(page, "investor");
  await page.goto(PROTECTED_INVESTOR_ROUTE);
  await page.getByRole("button", { name: /keluar/i }).click();
  await expect(page).toHaveURL("/");
  const token = await page.evaluate(() => localStorage.getItem("modalink_token"));
  expect(token).toBeNull();

  await routeAuth(page, null);
  await page.goto(PROTECTED_INVESTOR_ROUTE);
  await expect(page).toHaveURL(`/masuk?next=${encodeURIComponent(PROTECTED_INVESTOR_ROUTE)}`);
});

test("the shared header and its theme toggle appear on every route checked", async ({ page }) => {
  await routeAuth(page, null);
  for (const path of ["/", "/jelajah", "/masuk", "/daftar"]) {
    await page.goto(path);
    await expect(page.getByRole("link", { name: "Modalink" })).toBeVisible();
    await expect(page.getByRole("button", { name: /tema/i })).toBeVisible();
  }
});
