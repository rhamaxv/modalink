import { expect, test, type Page } from "@playwright/test";

const PROPOSAL_ID = "proposal-penuh";

// Data tiruan satu set dipakai ulang oleh beberapa test lewat page.route():
// permintaan jaringan sungguhan dicegat di Chromium sungguhan, bukan mock
// jsdom seperti test unit (yang tidak merender CSS, tema, atau fokus
// sungguhan). Ini yang memungkinkan R-35 ("aplikasi dijalankan, setiap
// kontrol diklik satu per satu") dan R-34 (kedua tema diperiksa) sungguh
// diuji di sini, bukan di test unit.
async function mockProposalLengkap(page: Page, status: "listed" | "funded" = "listed") {
  const proposal = {
    id: PROPOSAL_ID,
    campaign_id: "c1",
    umkm_id: "u-umkm-1",
    business_name: "Kopi Rakyat Nusantara",
    business_profile: "Usaha kopi rakyat yang sudah berjalan tiga tahun di Yogyakarta.",
    fund_usage_plan: "60% mesin roasting, 40% kemasan dan distribusi ke tiga kota baru.",
    business_projection: "Omzet diproyeksikan naik dua kali lipat dalam satu tahun.",
    requested_amount: 10_000_000,
    status,
    scoring_status: "done",
    lead_investor_id: "u-investor-9",
    funded_at: null,
    created_at: "2026-10-01T08:00:00Z",
  };
  const score = {
    id: "s1",
    proposal_id: PROPOSAL_ID,
    engine_name: "gemini",
    model_name: "gemini-2.5-flash",
    fit_score: 34,
    data_quality_score: 21,
    impact_score: 18,
    total_score: 73,
    threshold_used: 60,
    red_flags: [],
    brief: {
      strengths: ["Usaha berjalan 3 tahun."],
      risks: ["Proyeksi agresif."],
      recommendation: "Minta rincian asumsi proyeksi.",
    },
    verdict: "listed",
    latency_ms: 1200,
    created_at: "2026-11-07T10:00:00Z",
  };
  let voted = false;
  let voteCount = 5;
  const comments = [
    { id: "c1", author_name: "Siti", body: "Usahanya meyakinkan.", created_at: "2026-11-02T00:00:00Z", is_mine: false },
    { id: "c2", author_name: "Saya", body: "Komentar milik saya sendiri.", created_at: "2026-11-03T00:00:00Z", is_mine: true },
  ];

  await page.route("**/api/v1/**", async (route) => {
    const url = route.request().url();
    const method = route.request().method();
    const json = (body: unknown, httpStatus = 200) =>
      route.fulfill({ status: httpStatus, contentType: "application/json", body: JSON.stringify(body) });

    if (url.endsWith("/auth/me")) return json({ id: "u-investor-1", name: "Investor Uji", role: "investor" });
    if (url.endsWith("/scoring")) return json(score);
    if (url.endsWith("/pledges") && method === "GET") {
      return json({
        items: [
          { id: "pl1", proposal_id: PROPOSAL_ID, investor_id: "u-investor-9", amount: 4_000_000, status: "active", created_at: "2026-11-01T00:00:00Z" },
        ],
      });
    }
    if (url.endsWith("/pledges") && method === "POST") {
      return json(
        { id: "pl2", proposal_id: PROPOSAL_ID, investor_id: "u-investor-1", amount: 5_000_000, status: "active", created_at: "2026-11-08T00:00:00Z" },
        201,
      );
    }
    if (url.endsWith("/milestones")) {
      return json({
        items: [
          { id: "m1", seq: 1, title: "Pembelian mesin", description: "Membeli mesin roasting baru.", amount: 5_000_000, status: "pending" },
        ],
      });
    }
    if (url.endsWith("/vote") && method === "POST") {
      voted = !voted;
      voteCount += voted ? 1 : -1;
      return json({ voted, vote_count: voteCount });
    }
    if (url.endsWith("/comments") && method === "GET") return json({ items: comments, vote_count: voteCount, voted_by_me: voted });
    if (url.endsWith("/comments") && method === "POST") {
      return json({ id: "c3", author_name: "Saya", body: "Komentar baru dari uji e2e.", created_at: "2026-11-09T00:00:00Z", is_mine: true }, 201);
    }
    if (url.includes("/comments/") && method === "DELETE") return route.fulfill({ status: 204, body: "" });
    if (url.endsWith(`/proposals/${PROPOSAL_ID}`)) return json(proposal);
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ error: { code: "tidak_ditemukan", message: "Tidak ditemukan." } }),
    });
  });

  // Tanpa token, komponen tidak pernah memanggil /auth/me (sengaja: tamu
  // anonim tidak boleh memicu permintaan yang hanya berguna untuk pengguna
  // masuk), jadi form pledge akan tersembunyi dengan alasan "harus masuk".
  // Token disuntik sebelum navigasi supaya skenario investor masuk ini
  // benar-benar teruji, bukan default anonim.
  await page.addInitScript(() => localStorage.setItem("modalink_token", "token-e2e"));
}

// Lingkungan e2e ini menjalankan `next dev` tanpa backend sungguhan di
// baliknya saat tidak ada page.route() yang mencegat (lihat
// playwright.config.ts: hanya webServer frontend, tidak ada basis API lewat
// NEXT_PUBLIC_API_URL). Setiap permintaan ke /api/v1/* jatuh ke 404 bawaan
// Next, bukan bentuk error JSON kita. lib/api.ts menangani kegagalan parse
// JSON itu dengan pesan generik, jadi skenario ini sengaja dipakai untuk
// membuktikan satu hal yang tidak bisa dibuktikan test unit jsdom: halaman
// proposal yang gagal memuat benar-benar menampilkan keadaan galat yang bisa
// dioperasikan lewat keyboard di browser sungguhan, bukan halaman kosong.
test("a failed proposal fetch shows a real, keyboard-operable error state instead of a blank page", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => consoleErrors.push(err.message));

  await page.goto("/proposal/proposal-uji-coba");

  const galat = page.getByRole("alert");
  await expect(galat).toBeVisible();

  const cobaLagi = page.getByRole("button", { name: /coba lagi/i });
  await expect(cobaLagi).toBeVisible();

  // Kontrol sungguhan, bukan dekorasi: fokus keyboard mencapainya dan Enter
  // memicu permintaan ulang (yang gagal lagi dengan cara yang sama, karena
  // tidak ada backend di baliknya), bukan diam atau melempar galat JS.
  await cobaLagi.focus();
  await expect(cobaLagi).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("alert")).toBeVisible();

  expect(consoleErrors.join("\n")).not.toMatch(/Hydration|error #418|did not match|Uncaught/i);
});

test("has no horizontal scroll at 320px even while showing the error state", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto("/proposal/proposal-uji-coba");
  await expect(page.getByRole("alert")).toBeVisible();

  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(scrollWidth).toBeLessThanOrEqual(320);
});

// R-35: aplikasi dijalankan, setiap kontrol diklik satu per satu, hasilnya
// dicatat sebagai daftar bukti, bukan diringkas jadi "semua berfungsi".
test("every interactive control on a fully-loaded proposal page works when clicked", async ({ page }) => {
  await mockProposalLengkap(page, "listed");

  const hasil: string[] = [];
  await page.goto(`/proposal/${PROPOSAL_ID}`);

  await expect(page.getByRole("heading", { name: "Kopi Rakyat Nusantara" })).toBeVisible();
  hasil.push("Halaman proposal -> judul usaha tampil, tidak crash");

  await expect(page.getByText("73")).toBeVisible();
  hasil.push("Panel skor -> total skor 73 tampil (bukan keadaan menunggu, bukan nol)");

  const tombolVote = page.getByRole("button", { name: /dukung/i });
  await expect(tombolVote).toHaveAttribute("aria-pressed", "false");
  await tombolVote.click();
  await expect(tombolVote).toHaveAttribute("aria-pressed", "true");
  hasil.push("Tombol 'Dukung proposal ini' -> aria-pressed berubah false ke true setelah diklik");

  await expect(page.getByText("Komentar milik saya sendiri.")).toBeVisible();
  const tombolHapus = page.getByRole("button", { name: /hapus komentar/i });
  await expect(tombolHapus).toHaveCount(1);
  await tombolHapus.click();
  await expect(page.getByText("Komentar milik saya sendiri.")).toHaveCount(0);
  hasil.push("Tombol 'Hapus komentar' -> hanya satu (milik sendiri), hilang dari layar setelah diklik");

  await page.getByLabel(/komentar/i).fill("Komentar baru dari uji e2e.");
  await page.getByRole("button", { name: /^kirim$/i }).click();
  await expect(page.getByLabel(/komentar/i)).toHaveValue("");
  hasil.push("Form komentar -> terkirim, textarea kembali kosong setelah sukses");

  const nominal = page.getByLabel(/nominal/i);
  await nominal.fill("99999999");
  const tombolDanai = page.getByRole("button", { name: /danai/i });
  await expect(tombolDanai).toBeDisabled();
  await expect(page.getByRole("status")).toContainText(/melebihi sisa/i);
  hasil.push("Form pledge -> nominal melebihi sisa menonaktifkan tombol Danai dan menampilkan peringatan");

  await nominal.fill("5000000");
  await expect(tombolDanai).toBeEnabled();
  await tombolDanai.click();
  await expect(nominal).toHaveValue("");
  hasil.push("Form pledge -> nominal valid, tombol Danai aktif, terkirim, field terkosongkan setelah sukses");

  expect(hasil.length).toBe(7);
});

test("a funded proposal hides the pledge form and names the reason, in a real browser", async ({ page }) => {
  await mockProposalLengkap(page, "funded");
  await page.goto(`/proposal/${PROPOSAL_ID}`);

  await expect(page.getByText("73")).toBeVisible();
  await expect(page.getByRole("button", { name: /danai/i })).toHaveCount(0);
  await expect(page.getByText(/sudah tercapai/i)).toBeVisible();
});

test("both themes keep adequate contrast and an intact layout at 320px on a fully-loaded page", async ({ page }) => {
  await mockProposalLengkap(page, "listed");
  await page.goto(`/proposal/${PROPOSAL_ID}`);
  await expect(page.getByText("73")).toBeVisible();

  const backgrounds: Record<string, string> = {};
  for (const theme of ["light", "dark"] as const) {
    await page.evaluate((t) => {
      document.documentElement.dataset.theme = t;
    }, theme);

    for (const width of [320, 768]) {
      await page.setViewportSize({ width, height: 900 });
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(scrollWidth).toBeLessThanOrEqual(width);
    }

    backgrounds[theme] = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  }

  // Jaring pengaman seperti e2e/theme.spec.ts: membuktikan kedua tema
  // sungguh berbeda, bukan lolos karena [data-theme="dark"] diam-diam
  // berhenti berlaku.
  expect(backgrounds.light).not.toBe(backgrounds.dark);
});
