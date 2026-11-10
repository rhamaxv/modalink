import { readFileSync } from "node:fs";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import ExplorePage from "@/app/jelajah/page";
import { ExploreTabs } from "@/components/ExploreTabs";
import { CampaignBrowseCard, CampaignBrowseList } from "@/components/CampaignBrowseCard";
import { CampaignDetailPanel } from "@/components/CampaignDetailPanel";

// Jelajah sekarang punya dua niat (investor cari proposal, UMKM cari
// campaign), jadi test ini menutupi bagian yang baru: ExploreTabs, daftar
// campaign publik, dan halaman detail campaign publik. Test untuk
// ProposalList sendiri sudah ada di tests/composition.test.tsx dan tidak
// diulang di sini.

const OPEN_CAMPAIGN = {
  id: "c-open-1",
  investor_id: "inv1",
  title: "Dana Kuliner Lokal",
  description: "Campaign untuk mendanai usaha kuliner rumahan di sekitar kota.",
  sector: "kuliner",
  target_amount: 100_000_000,
  apply_deadline: "2026-12-01T23:59:59Z",
  funding_deadline: "2027-03-01T23:59:59Z",
  score_threshold: 60,
  status: "open",
  created_at: "2026-01-01T00:00:00Z",
};

const OPEN_CAMPAIGN_URGENT = {
  ...OPEN_CAMPAIGN,
  id: "c-open-2",
  title: "Dana Kerajinan Desa",
  sector: "kerajinan",
  target_amount: 50_000_000,
  apply_deadline: "2026-11-15T23:59:59Z",
};

const CLOSED_CAMPAIGN = {
  ...OPEN_CAMPAIGN,
  id: "c-closed-1",
  title: "Dana Lama Yang Sudah Tutup",
  status: "closed",
};

function fakeResponse(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

// Router endpoint sederhana: cocokkan jalur, bukan urutan panggilan, supaya
// stub ini sama tahan terhadap Promise.all di ExploreTabs/CampaignBrowseList
// (keduanya mount bersamaan di balik tab yang hidden).
function stubEndpoints(handlers: { me?: unknown; campaigns?: unknown[]; proposals?: unknown[] }) {
  vi.stubGlobal("fetch", (url: string) => {
    if (url.includes("/auth/me")) {
      return handlers.me === undefined
        ? fakeResponse(401, { error: { code: "tidak_sah", message: "Tidak sah" } })
        : fakeResponse(200, handlers.me);
    }
    if (url.includes("/campaigns") && url.includes("/proposals")) {
      return fakeResponse(200, { items: handlers.proposals ?? [] });
    }
    if (url.includes("/campaigns/")) {
      const match = /\/campaigns\/([^/]+)$/.exec(url);
      const id = match?.[1];
      const found = (handlers.campaigns ?? []).find((c) => (c as { id: string }).id === id);
      return found
        ? fakeResponse(200, found)
        : fakeResponse(404, { error: { code: "campaign_tidak_ada", message: "Campaign tidak ditemukan." } });
    }
    if (url.includes("/campaigns")) {
      return fakeResponse(200, { items: handlers.campaigns ?? [] });
    }
    if (url.includes("/proposals")) {
      return fakeResponse(200, { items: handlers.proposals ?? [] });
    }
    throw new Error(`unexpected fetch call to ${url}`);
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("CampaignBrowseList: three states, same discipline as ProposalList", () => {
  it("shows the loading state before data arrives", () => {
    vi.stubGlobal("fetch", () => new Promise(() => {}));
    render(<CampaignBrowseList />);
    expect(screen.getByText("Memuat daftar campaign")).toBeInTheDocument();
  });

  it("shows an error state with a working retry button", async () => {
    let calls = 0;
    vi.stubGlobal("fetch", () => {
      calls += 1;
      return calls === 1
        ? fakeResponse(500, { error: { code: "galat_server", message: "Server sedang bermasalah." } })
        : fakeResponse(200, { items: [] });
    });
    render(<CampaignBrowseList />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Server sedang bermasalah.");
    await userEvent.click(screen.getByRole("button", { name: /coba lagi/i }));
    expect(
      await screen.findByText("Belum ada campaign yang terbuka untuk menerima proposal saat ini."),
    ).toBeInTheDocument();
  });

  it("shows an empty state with a real reason, not a bare 'no data' label", async () => {
    stubEndpoints({ campaigns: [] });
    render(<CampaignBrowseList />);
    expect(
      await screen.findByText("Belum ada campaign yang terbuka untuk menerima proposal saat ini."),
    ).toBeInTheDocument();
  });

  it("filters out closed campaigns client-side, proving the documented backend gap workaround", async () => {
    // GET /campaigns tidak memfilter status di backend (lihat komentar di
    // CampaignBrowseCard.tsx), jadi daftar ini wajib membuang yang closed
    // sendiri. Kalau filter ini dihapus, test ini merah.
    stubEndpoints({ campaigns: [OPEN_CAMPAIGN, CLOSED_CAMPAIGN] });
    render(<CampaignBrowseList />);
    expect(await screen.findByText("Dana Kuliner Lokal")).toBeInTheDocument();
    expect(screen.queryByText("Dana Lama Yang Sudah Tutup")).not.toBeInTheDocument();
  });

  it("makes the whole row a link to the campaign, named by the campaign it belongs to", async () => {
    // Satu tautan per baris, bukan tautan "Lihat campaign ini" terpisah: di
    // daftar dua puluh baris, dua puluh tautan bernama sama persis tidak
    // bisa dinavigasi pembaca layar.
    stubEndpoints({ campaigns: [OPEN_CAMPAIGN] });
    render(<CampaignBrowseList />);
    await screen.findByText("Dana Kuliner Lokal");
    const link = screen
      .getAllByRole("link")
      .find((a) => a.getAttribute("href") === "/jelajah/campaign/c-open-1");
    expect(link).toBeDefined();
    expect(link?.textContent).toContain("Dana Kuliner Lokal");
  });

  it("marks only the apply deadline that is genuinely close, and leaves the others plain", async () => {
    // Pagar ini dulu juga menuntut campaign dengan tenggat terdekat
    // bernominal LEBIH BESAR dari yang lain. Tuntutan itu dicabut bersama
    // perombakan halaman jelajah menjadi halaman indeks: nominal yang
    // sejajar adalah yang membuat daftar panjang bisa dipindai, dan satu
    // baris yang dibesarkan justru merusak kolomnya. Yang tetap dijaga
    // adalah penanda warnanya, karena ia yang membawa informasi.
    stubEndpoints({ campaigns: [OPEN_CAMPAIGN, OPEN_CAMPAIGN_URGENT] });
    render(<CampaignBrowseList />);
    await screen.findByText("Dana Kerajinan Desa");

    const beraksen = screen
      .getAllByText(/\d{1,2} \w+ 20\d\d/)
      .filter((el) => el.className.split(" ").includes("text-accent-text"));
    // Tepat satu: hanya OPEN_CAMPAIGN_URGENT yang tenggatnya dalam tujuh
    // hari. Kalau keduanya ikut berwarna, warnanya berhenti berarti.
    expect(beraksen).toHaveLength(1);
    expect(beraksen[0]?.textContent).toMatch(/hari lagi/);
  });

  it("never renders the sector as bare accent-coloured text, in a row or in a chip", async () => {
    // accent-2 sebagai warna TEKS polos mengukur 1,90:1 di tema terang dan
    // dilarang DESIGN.md. Ada dua bentuk sektor di produk ini dan keduanya
    // harus aman: teks biasa di baris daftar, dan chip di kartu.
    stubEndpoints({ campaigns: [OPEN_CAMPAIGN] });
    const { unmount } = render(<CampaignBrowseList />);
    const diBaris = await screen.findByText("Kuliner");
    expect(diBaris.className).not.toMatch(/\btext-accent-2\b/);
    expect(diBaris.className).not.toMatch(/\btext-accent\b/);
    unmount();

    const { getByText } = render(<CampaignBrowseCard campaign={OPEN_CAMPAIGN} />);
    const chip = getByText("Kuliner");
    expect(chip.className).toContain("bg-accent-2");
    expect(chip.className).toContain("text-on-accent");
    expect(chip.className).not.toMatch(/\btext-accent-2\b/);
  });

  it("shows both deadlines with labels that tell them apart, even in the dense row (D-16)", async () => {
    // Satu tenggat saja mengundang UMKM menyangka ia punya waktu sampai
    // tanggal yang sebenarnya milik tenggat yang lain.
    stubEndpoints({ campaigns: [OPEN_CAMPAIGN] });
    render(<CampaignBrowseList />);
    await screen.findByText("Dana Kuliner Lokal");
    expect(screen.getByText("Tenggat pengajuan")).toBeInTheDocument();
    expect(screen.getByText("Tenggat pendanaan")).toBeInTheDocument();
  });
});

describe("ExploreTabs: two intents, one screen, neither hidden from a signed-out visitor", () => {
  it("defaults to the Proposal tab for an anonymous visitor, with the Campaign tab still present", async () => {
    stubEndpoints({ proposals: [], campaigns: [] });
    render(<ExploreTabs />);
    const tabProposal = screen.getByRole("tab", { name: "Proposal" });
    const tabCampaign = screen.getByRole("tab", { name: "Campaign" });
    expect(tabProposal).toHaveAttribute("aria-selected", "true");
    expect(tabCampaign).toHaveAttribute("aria-selected", "false");
    // Tab yang tidak aktif tetap ADA di DOM dan tetap bisa diklik, bukan
    // dihapus: ini bedanya tab dari menyembunyikan satu sisi pasar.
    expect(tabCampaign).toBeEnabled();
  });

  it("defaults to the Campaign tab once a signed-in UMKM account is detected", async () => {
    localStorage.setItem("modalink_token", "token-umkm");
    stubEndpoints({
      me: { id: "u1", email: "umkm1@demo.example.com", name: "UMKM Satu", role: "umkm", created_at: "2026-01-01T00:00:00Z" },
      proposals: [],
      campaigns: [],
    });
    render(<ExploreTabs />);
    await waitFor(() => expect(screen.getByRole("tab", { name: "Campaign" })).toHaveAttribute("aria-selected", "true"));
    expect(screen.getByRole("tab", { name: "Proposal" })).toHaveAttribute("aria-selected", "false");
  });

  it("keeps the Proposal tab selected for an investor account", async () => {
    localStorage.setItem("modalink_token", "token-investor");
    stubEndpoints({
      me: { id: "u2", email: "investor1@demo.example.com", name: "Investor Satu", role: "investor", created_at: "2026-01-01T00:00:00Z" },
      proposals: [],
      campaigns: [],
    });
    render(<ExploreTabs />);
    await waitFor(() => expect(screen.getByRole("tab", { name: "Proposal" })).toHaveAttribute("aria-selected", "true"));
  });

  it("a manual click always wins over the role-based default", async () => {
    localStorage.setItem("modalink_token", "token-umkm");
    stubEndpoints({
      me: { id: "u1", email: "umkm1@demo.example.com", name: "UMKM Satu", role: "umkm", created_at: "2026-01-01T00:00:00Z" },
      proposals: [],
      campaigns: [],
    });
    render(<ExploreTabs />);
    await waitFor(() => expect(screen.getByRole("tab", { name: "Campaign" })).toHaveAttribute("aria-selected", "true"));
    await userEvent.click(screen.getByRole("tab", { name: "Proposal" }));
    expect(screen.getByRole("tab", { name: "Proposal" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Campaign" })).toHaveAttribute("aria-selected", "false");
  });

  it("is operable by keyboard: a tab button activates on Enter, matching a native button", async () => {
    stubEndpoints({ proposals: [], campaigns: [] });
    render(<ExploreTabs />);
    const tabCampaign = screen.getByRole("tab", { name: "Campaign" });
    tabCampaign.focus();
    expect(tabCampaign).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(tabCampaign).toHaveAttribute("aria-selected", "true");
  });

  it("clicking Campaign reveals real campaign cards, and the Proposal panel stays mounted but inaccessible", async () => {
    stubEndpoints({ proposals: [], campaigns: [OPEN_CAMPAIGN] });
    render(<ExploreTabs />);
    await userEvent.click(screen.getByRole("tab", { name: "Campaign" }));
    expect(await screen.findByText("Dana Kuliner Lokal")).toBeInTheDocument();
    // Panel proposal tidak dilepas dari DOM (lihat komentar di
    // ExploreTabs.tsx), tapi query berbasis role mengecualikannya karena
    // atribut hidden, sama seperti yang akan dilihat pembaca layar.
    expect(screen.queryByRole("status", { name: /memuat daftar proposal/i })).not.toBeInTheDocument();
  });
});

describe("the explore page stays colourful and keeps exactly one accent action, regardless of which tab is active by default", () => {
  function stubEmptyFetch() {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => fakeResponse(200, { items: [] })),
    );
  }

  // DESIGN.md menjatah AKSI berlatar aksen, bukan warna secara umum: tepat
  // satu per layar. Dipisah dari tests/composition.test.tsx (yang menjaga
  // aturan ini untuk landing page) supaya perubahan di sini tidak
  // menyentuh berkas yang juga dipakai stream lain.
  function hitungAksiAksen(container: HTMLElement): number {
    return [...container.querySelectorAll("a[href], button")].filter((el) =>
      el.className.split(" ").includes("bg-accent"),
    ).length;
  }

  function hitungMomenWarna(container: HTMLElement): number {
    const KELAS_WARNA = [
      "bg-accent", "bg-accent-2", "text-accent-text", "text-accent-2-text",
      "border-accent", "text-ok", "text-warn", "text-danger",
    ];
    return [...container.querySelectorAll<HTMLElement>("*")].filter((el) => {
      const kelas = el.className?.split?.(" ") ?? [];
      return KELAS_WARNA.some((k) => kelas.includes(k));
    }).length;
  }

  it("has exactly one accent-background action on the page", async () => {
    stubEmptyFetch();
    const { container } = render(<ExplorePage />);
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
    expect(hitungAksiAksen(container)).toBe(1);
  });

  it("is not colourless: at least three real colour moments outside the one action", async () => {
    stubEmptyFetch();
    const { container } = render(<ExplorePage />);
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
    expect(hitungMomenWarna(container)).toBeGreaterThanOrEqual(3);
  });

  it("proves both guards above can actually fail, on fabricated markup", () => {
    const duaAksi = document.createElement("div");
    duaAksi.innerHTML = '<button class="bg-accent">a</button><a href="/x" class="bg-accent">b</a>';
    expect(hitungAksiAksen(duaAksi)).toBe(2);

    const monokrom = document.createElement("div");
    monokrom.innerHTML = '<p class="text-ink">tanpa warna</p>';
    expect(hitungMomenWarna(monokrom)).toBeLessThan(3);
  });

  it("has no em dash in its copy", () => {
    const source = readFileSync("app/jelajah/page.tsx", "utf8");
    const textBlocks = [...source.matchAll(/>([^<>{}]*)</g)].map((m) => m[1]);
    textBlocks.forEach((text) => expect(text).not.toContain("—"));
  });
});

describe("CampaignDetailPanel: the public screen a UMKM decides from", () => {
  it("shows the loading state before data arrives", () => {
    vi.stubGlobal("fetch", () => new Promise(() => {}));
    render(<CampaignDetailPanel campaignId="c-open-1" />);
    expect(screen.getByText("Memuat campaign")).toBeInTheDocument();
  });

  it("shows an error state with a working retry button", async () => {
    let calls = 0;
    vi.stubGlobal("fetch", () => {
      calls += 1;
      return calls <= 2
        ? fakeResponse(500, { error: { code: "galat_server", message: "Server sedang bermasalah." } })
        : fakeResponse(200, calls === 3 ? OPEN_CAMPAIGN : { items: [] });
    });
    render(<CampaignDetailPanel campaignId="c-open-1" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Server sedang bermasalah.");
    await userEvent.click(screen.getByRole("button", { name: /coba lagi/i }));
    expect(await screen.findByText("Dana Kuliner Lokal")).toBeInTheDocument();
  });

  it("shows both deadlines with distinct labels and values", async () => {
    stubEndpoints({ campaigns: [OPEN_CAMPAIGN], proposals: [] });
    render(<CampaignDetailPanel campaignId="c-open-1" />);
    await screen.findByText("Dana Kuliner Lokal");
    const applyLabel = screen.getByText("Tenggat pengajuan proposal");
    const fundingLabel = screen.getByText("Tenggat pendanaan");
    const applyBlock = applyLabel.closest("div");
    const fundingBlock = fundingLabel.closest("div");
    expect(applyBlock?.textContent).not.toBe(fundingBlock?.textContent);
  });

  it("offers a working apply CTA to /umkm/proposal/baru when the campaign is open and the deadline has not passed", async () => {
    stubEndpoints({ campaigns: [OPEN_CAMPAIGN], proposals: [] });
    render(<CampaignDetailPanel campaignId="c-open-1" />);
    const cta = await screen.findByRole("link", { name: /ajukan proposal ke campaign ini/i });
    expect(cta.getAttribute("href")).toBe("/umkm/proposal/baru");
  });

  it("marks the apply deadline as the live decision with accent-text when the campaign can still be applied to", async () => {
    stubEndpoints({ campaigns: [OPEN_CAMPAIGN], proposals: [] });
    render(<CampaignDetailPanel campaignId="c-open-1" />);
    await screen.findByText("Dana Kuliner Lokal");
    const applyLabel = screen.getByText("Tenggat pengajuan proposal");
    const dd = applyLabel.closest("div")?.querySelector("dd");
    expect(dd?.className).toContain("text-accent-text");
  });

  it("shows a closed message and no apply CTA when the campaign is closed", async () => {
    stubEndpoints({ campaigns: [CLOSED_CAMPAIGN], proposals: [] });
    render(<CampaignDetailPanel campaignId="c-closed-1" />);
    expect(await screen.findByText(/campaign ini sudah ditutup/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /ajukan proposal/i })).not.toBeInTheDocument();
  });

  it("shows an expired message and no apply CTA when the apply deadline has passed, even if status is still open", async () => {
    const lewat = { ...OPEN_CAMPAIGN, id: "c-lewat", apply_deadline: "2020-01-01T00:00:00Z" };
    stubEndpoints({ campaigns: [lewat], proposals: [] });
    render(<CampaignDetailPanel campaignId="c-lewat" />);
    expect(await screen.findByText(/tenggat pengajuan proposal untuk campaign ini sudah lewat/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /ajukan proposal/i })).not.toBeInTheDocument();
  });

  it("shows an empty state with a real reason when no proposal has been submitted yet", async () => {
    stubEndpoints({ campaigns: [OPEN_CAMPAIGN], proposals: [] });
    render(<CampaignDetailPanel campaignId="c-open-1" />);
    expect(await screen.findByText("Belum ada proposal yang diajukan ke campaign ini.")).toBeInTheDocument();
  });

  it("maps the full business_profile from GET /campaigns/{id}/proposals into a real excerpt, truncated not fabricated", async () => {
    const profilPanjang = "Usaha kopi rumahan ".repeat(20).trim();
    stubEndpoints({
      campaigns: [OPEN_CAMPAIGN],
      proposals: [
        {
          id: "p1",
          business_name: "Kopi Senja",
          business_profile: profilPanjang,
          requested_amount: 25_000_000,
          status: "listed",
          scoring_status: "done",
          created_at: "2026-01-01T00:00:00Z",
          total_score: 80,
          vote_count: 2,
        },
      ],
    });
    render(<CampaignDetailPanel campaignId="c-open-1" />);
    expect(await screen.findByText("Kopi Senja")).toBeInTheDocument();
    const cuplikan = `${profilPanjang.slice(0, 160)}...`;
    expect(screen.getByText(cuplikan)).toBeInTheDocument();
    expect(screen.queryByText(profilPanjang)).not.toBeInTheDocument();
  });

  it("renders every submitted proposal as a real link to its own detail page", async () => {
    stubEndpoints({
      campaigns: [OPEN_CAMPAIGN],
      proposals: [
        {
          id: "p1",
          business_name: "Kopi Senja",
          business_profile: "Usaha kopi rumahan yang sudah berjalan tiga tahun.",
          requested_amount: 25_000_000,
          status: "listed",
          scoring_status: "done",
          created_at: "2026-01-01T00:00:00Z",
          total_score: 80,
          vote_count: 2,
        },
      ],
    });
    render(<CampaignDetailPanel campaignId="c-open-1" />);
    const link = await screen.findByRole("link", { name: /baca proposal$/i });
    expect(link.getAttribute("href")).toBe("/proposal/p1");
  });
});

describe("the new public campaign detail route resolves", () => {
  it("has a page.tsx at app/jelajah/campaign/[id], the route every CampaignBrowseCard links to", () => {
    // Dibaca dari filesystem, bukan ditebak: kalau berkasnya dipindah atau
    // dihapus tanpa mengubah tautannya, test ini merah.
    expect(() => readFileSync("app/jelajah/campaign/[id]/page.tsx", "utf8")).not.toThrow();
  });
});
