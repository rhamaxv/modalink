import { readFileSync } from "node:fs";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ExplorePage from "@/app/jelajah/page";
import Beranda from "@/app/page";

// Dipakai oleh dua halaman (jelajah dan landing): tidak boleh ada dua
// <section> berurutan dengan data-pola yang sama (RHYTHM 3, DESIGN.md).
function checkPolaBerurutanBerbeda(sourcePath: string) {
  const source = readFileSync(sourcePath, "utf8");
  const patterns = [...source.matchAll(/data-pola="([a-z-]+)"/g)].map((m) => m[1]);
  expect(patterns.length).toBeGreaterThanOrEqual(4);
  patterns.forEach((pattern, i) => {
    if (i > 0) expect(pattern).not.toBe(patterns[i - 1]);
  });
}

function checkSetiapSectionBerpola(sourcePath: string) {
  const source = readFileSync(sourcePath, "utf8");
  const sectionCount = (source.match(/<section/g) ?? []).length;
  const patternCount = (source.match(/data-pola=/g) ?? []).length;
  expect(patternCount).toBe(sectionCount);
}

// ProposalList (dalam ProposalCard.tsx) memanggil fetch begitu ia dipasang.
// Tes di bawah ini hanya menyoroti struktur halaman (RHYTHM, H1, navigasi),
// bukan isi daftar proposal, jadi fetch distub supaya tidak pernah
// benar-benar memanggil jaringan dan tidak menyisakan rejection tak tertangani.
function stubEmptyFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(new Response(JSON.stringify({ items: [] }), { status: 200 }))),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RHYTHM 3 on the explore page", () => {
  it("has no two consecutive sections sharing the same composition pattern", () => {
    checkPolaBerurutanBerbeda("app/jelajah/page.tsx");
  });

  it("gives every section an explicit pattern attribute", () => {
    checkSetiapSectionBerpola("app/jelajah/page.tsx");
  });
});

describe("RHYTHM 3 on the landing page", () => {
  it("has no two consecutive sections sharing the same composition pattern", () => {
    checkPolaBerurutanBerbeda("app/page.tsx");
  });

  it("gives every section an explicit pattern attribute", () => {
    checkSetiapSectionBerpola("app/page.tsx");
  });

  it("proves the guard actually fails when two consecutive sections share a pattern", () => {
    // Pembuktian bahwa pagar ini bisa merah: dua pola identik berurutan
    // yang disuntikkan langsung ke string sumber, bukan ke file sungguhan,
    // supaya tidak perlu menulis-lalu-memulihkan app/page.tsx di tengah test run.
    const palsu = `
      <section data-pola="naratif-kiri">a</section>
      <section data-pola="naratif-kiri">b</section>
      <section data-pola="daftar-bernomor">c</section>
      <section data-pola="dua-kolom-setara">d</section>
    `;
    const patterns = [...palsu.matchAll(/data-pola="([a-z-]+)"/g)].map((m) => m[1]);
    expect(() => {
      patterns.forEach((pattern, i) => {
        if (i > 0) expect(pattern).not.toBe(patterns[i - 1]);
      });
    }).toThrow();
  });
});

describe("explore page is free of default AI-slop shapes", () => {
  it("has no eyebrow pill badge above the H1", () => {
    stubEmptyFetch();
    render(<ExplorePage />);
    const h1 = screen.getByRole("heading", { level: 1 });
    const previousSibling = h1.previousElementSibling;
    expect(previousSibling?.getAttribute("data-pola")).not.toBe("eyebrow-badge");
  });

  it("has no statistic with no real data source", () => {
    stubEmptyFetch();
    render(<ExplorePage />);
    // R-17: tidak ada "10rb+ pengguna" atau sejenisnya.
    expect(screen.queryByText(/\d+(rb|k|jt)\+/i)).toBeNull();
  });

  it("has no testimonial", () => {
    stubEmptyFetch();
    render(<ExplorePage />);
    expect(screen.queryByText(/testimoni/i)).toBeNull();
  });

  it("links every navigation item to a route that actually exists", () => {
    stubEmptyFetch();
    render(<ExplorePage />);
    const staticRoutes = ["/", "/jelajah", "/masuk", "/daftar"];
    screen.getAllByRole("link").forEach((a) => {
      const href = a.getAttribute("href") ?? "";
      if (!href.startsWith("/")) return;
      const path = href.split("#")[0] ?? href;
      // Rute detail proposal dibangun stream lain di worktree lain
      // (brief f11-b), tapi rutenya nyata: menautkannya dari sini sah.
      const isProposalDetailRoute = /^\/proposal\/[^/]+$/.test(path);
      expect(staticRoutes.includes(path) || isProposalDetailRoute).toBe(true);
    });
  });
});

describe("landing page is free of default AI-slop shapes", () => {
  it("has no eyebrow pill badge above the H1", () => {
    render(<Beranda />);
    const h1 = screen.getByRole("heading", { level: 1 });
    const previousSibling = h1.previousElementSibling;
    expect(previousSibling).toBeNull();
  });

  it("does not use the product name as the H1", () => {
    render(<Beranda />);
    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1.textContent?.trim().toLowerCase()).not.toBe("modalink");
  });

  it("has no statistic with no real data source", () => {
    render(<Beranda />);
    expect(screen.queryByText(/\d+(rb|k|jt)\+/i)).toBeNull();
  });

  it("has no testimonial", () => {
    render(<Beranda />);
    expect(screen.queryByText(/testimoni/i)).toBeNull();
  });

  it("has no em dash in its copy", () => {
    const source = readFileSync("app/page.tsx", "utf8");
    const textBlocks = [...source.matchAll(/>([^<>{}]*)</g)].map((m) => m[1]);
    textBlocks.forEach((text) => expect(text).not.toContain("—"));
  });

  it("links every navigation item to a route that actually exists", () => {
    render(<Beranda />);
    const staticRoutes = ["/", "/jelajah", "/masuk", "/daftar"];
    screen.getAllByRole("link").forEach((a) => {
      const href = a.getAttribute("href") ?? "";
      if (!href.startsWith("/")) return;
      const path = href.split("#")[0] ?? href;
      expect(staticRoutes.includes(path)).toBe(true);
    });
  });

  it("uses the accent colour on at most one primary action on this screen", () => {
    const { container } = render(<Beranda />);
    const akzen = container.querySelectorAll(".bg-accent");
    expect(akzen.length).toBeLessThanOrEqual(1);
  });
});

describe("public proposal list on the explore page", () => {
  function stubFetchWithProposals() {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  id: "p1",
                  campaign_id: "c1",
                  umkm_id: "u1",
                  business_name: "Kopi Senja",
                  business_profile:
                    "Usaha kopi rumahan yang sudah berjalan tiga tahun dan ingin memperluas kapasitas produksi.",
                  fund_usage_plan: "Mesin roasting baru.",
                  business_projection: "Naik dua kali lipat.",
                  requested_amount: 25_000_000,
                  status: "listed",
                  scoring_status: "done",
                  lead_investor_id: null,
                  funded_at: null,
                  created_at: "2026-01-01T00:00:00Z",
                },
                {
                  id: "p2",
                  campaign_id: "c1",
                  umkm_id: "u2",
                  business_name: "Batik Lereng",
                  business_profile: "Usaha batik tulis.",
                  fund_usage_plan: "Bahan baku.",
                  business_projection: "Stabil.",
                  requested_amount: 15_000_000,
                  status: "partially_funded",
                  scoring_status: "done",
                  lead_investor_id: "inv1",
                  funded_at: null,
                  created_at: "2025-12-01T00:00:00Z",
                },
              ],
            }),
            { status: 200 },
          ),
        ),
      ),
    );
  }

  it("renders every proposal as a link to its detail page", async () => {
    stubFetchWithProposals();
    render(<ExplorePage />);
    expect(await screen.findByText("Kopi Senja")).toBeInTheDocument();
    expect(screen.getByText("Batik Lereng")).toBeInTheDocument();
    const links = screen.getAllByRole("link", { name: /baca proposal/i });
    expect(links).toHaveLength(2);
    links.forEach((a) => expect(a.getAttribute("href")).toMatch(/^\/proposal\//));
  });

  it("gives the first proposal a larger nominal than the following ones", async () => {
    stubFetchWithProposals();
    render(<ExplorePage />);
    await screen.findByText("Kopi Senja");
    const featuredAmount = screen.getByText("Rp25.000.000");
    const standardAmount = screen.getByText("Rp15.000.000");
    expect(featuredAmount.className).toContain("1.75rem");
    expect(standardAmount.className).not.toContain("1.75rem");
  });
});
