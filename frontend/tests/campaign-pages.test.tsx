import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CampaignForm } from "@/components/CampaignForm";
import { CampaignManagePanel } from "@/components/CampaignManagePanel";
import { CampaignList } from "@/components/CampaignList";

// CampaignForm dan CampaignManagePanel memanggil useRouter untuk navigasi
// setelah sukses, sama seperti SignUpForm/SignInForm.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}));

function fakeResponse(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

const BASE_CAMPAIGN = {
  id: "c1",
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

const CURRENT_USER = {
  id: "inv1",
  email: "investor@contoh.id",
  name: "Investor Satu",
  role: "investor",
  created_at: "2026-01-01T00:00:00Z",
};

function stubCampaignEndpoints(overrides: Partial<typeof BASE_CAMPAIGN> = {}, proposals: unknown[] = []) {
  const campaign = { ...BASE_CAMPAIGN, ...overrides };
  vi.stubGlobal("fetch", (url: string, init?: RequestInit) => {
    if (url.includes("/auth/me")) return fakeResponse(200, CURRENT_USER);
    if (url.endsWith("/close")) {
      return fakeResponse(200, { ...campaign, status: "closed" });
    }
    if (url.includes("/proposals")) return fakeResponse(200, { items: proposals });
    if (url.includes("/campaigns/")) {
      if (init?.method === "PATCH") {
        const body = JSON.parse(init.body as string);
        return fakeResponse(200, { ...campaign, ...body });
      }
      return fakeResponse(200, campaign);
    }
    throw new Error(`unexpected fetch call to ${url}`);
  });
  return campaign;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("CampaignManagePanel: campaign has two deadlines", () => {
  it("shows the apply deadline and funding deadline with labels that tell them apart", async () => {
    stubCampaignEndpoints();
    render(<CampaignManagePanel campaignId="c1" />);
    expect(await screen.findByText(/tenggat pengajuan/i)).toBeInTheDocument();
    const fundingLabel = screen.getByText(/tenggat funding/i);
    expect(fundingLabel).toBeInTheDocument();

    // Dua tenggat itu harus membawa dua tanggal yang berbeda, bukan satu
    // tenggat yang ditampilkan dua kali dengan label berbeda.
    const applyBlock = screen.getByText(/tenggat pengajuan/i).closest("div");
    const fundingBlock = fundingLabel.closest("div");
    expect(applyBlock?.textContent).not.toBe(fundingBlock?.textContent);
  });
});

describe("CampaignManagePanel: manual close confirmation", () => {
  it("asks for confirmation on the page before calling the server, never window.confirm", async () => {
    const confirmSpy = vi.spyOn(window, "confirm");
    stubCampaignEndpoints();
    render(<CampaignManagePanel campaignId="c1" />);

    const closeButton = await screen.findByRole("button", { name: /tutup campaign/i });
    await userEvent.click(closeButton);

    // Klik pertama hanya membuka konfirmasi inline; belum memanggil server.
    expect(await screen.findByText(/yakin ingin menutup/i)).toBeInTheDocument();
    expect(confirmSpy).not.toHaveBeenCalled();

    const confirmButton = screen.getByRole("button", { name: /ya, tutup campaign/i });
    await userEvent.click(confirmButton);

    expect(confirmSpy).not.toHaveBeenCalled();
    await screen.findByText(/campaign ini sudah ditutup/i);
    expect(screen.queryByRole("button", { name: /^tutup campaign$/i })).not.toBeInTheDocument();
  });
});

describe("CampaignManagePanel: already-closed campaign", () => {
  it("hides the close button and states the reason", async () => {
    stubCampaignEndpoints({ status: "closed" });
    render(<CampaignManagePanel campaignId="c1" />);

    await screen.findByText(BASE_CAMPAIGN.title);
    expect(screen.queryByRole("button", { name: /tutup campaign/i })).not.toBeInTheDocument();
    expect(screen.getByText(/campaign ini sudah ditutup/i)).toBeInTheDocument();
  });
});

describe("CampaignForm: client-side score_threshold validation", () => {
  async function fillRequiredFields() {
    await userEvent.type(screen.getByLabelText(/judul campaign/i), "Dana Kuliner Lokal Kita");
    await userEvent.type(
      screen.getByLabelText(/deskripsi/i),
      "Deskripsi campaign ini panjangnya lebih dari lima puluh karakter supaya lolos validasi minimal.",
    );
    await userEvent.type(screen.getByLabelText(/dana target/i), "5000000");
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 10);
    const laterDate = new Date();
    laterDate.setDate(laterDate.getDate() + 40);
    await userEvent.type(screen.getByLabelText(/tenggat pengajuan/i), tomorrow.toISOString().slice(0, 10));
    await userEvent.type(screen.getByLabelText(/tenggat funding/i), laterDate.toISOString().slice(0, 10));
  }

  it("rejects a score_threshold above 100 before sending any request", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    render(<CampaignForm mode="create" />);

    await fillRequiredFields();
    const thresholdInput = screen.getByLabelText(/ambang skor/i);
    await userEvent.clear(thresholdInput);
    await userEvent.type(thresholdInput, "150");
    await userEvent.click(screen.getByRole("button", { name: /buat campaign/i }));

    expect(await screen.findByText(/0 sampai 100/i)).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("rejects a negative score_threshold before sending any request", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    render(<CampaignForm mode="create" />);

    await fillRequiredFields();
    const thresholdInput = screen.getByLabelText(/ambang skor/i);
    await userEvent.clear(thresholdInput);
    await userEvent.type(thresholdInput, "-5");
    await userEvent.click(screen.getByRole("button", { name: /buat campaign/i }));

    expect(await screen.findByText(/0 sampai 100/i)).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("accepts a valid score_threshold and sends the request", async () => {
    vi.stubGlobal("fetch", (url: string) => {
      if (url.includes("/campaigns")) return fakeResponse(201, { ...BASE_CAMPAIGN, id: "c-new" });
      throw new Error(`unexpected fetch call to ${url}`);
    });
    render(<CampaignForm mode="create" />);

    await fillRequiredFields();
    await userEvent.click(screen.getByRole("button", { name: /buat campaign/i }));

    // Tidak ada pesan galat validasi threshold yang tersisa.
    expect(screen.queryByText(/0 sampai 100/i)).toBeNull();
  });
});

describe("CampaignList: investor's own campaigns", () => {
  it("shows a loading state, then only the campaigns owned by the current investor", async () => {
    vi.stubGlobal("fetch", (url: string) => {
      if (url.includes("/auth/me")) return fakeResponse(200, CURRENT_USER);
      if (url.includes("/campaigns")) {
        return fakeResponse(200, {
          items: [
            BASE_CAMPAIGN,
            { ...BASE_CAMPAIGN, id: "c2", investor_id: "other-investor", title: "Campaign Investor Lain" },
          ],
        });
      }
      throw new Error(`unexpected fetch call to ${url}`);
    });

    render(<CampaignList />);
    expect(screen.getByText(/memuat/i)).toBeInTheDocument();

    expect(await screen.findByText(BASE_CAMPAIGN.title)).toBeInTheDocument();
    expect(screen.queryByText("Campaign Investor Lain")).not.toBeInTheDocument();
  });

  it("shows an empty state with a create-campaign action when there are none yet", async () => {
    vi.stubGlobal("fetch", (url: string) => {
      if (url.includes("/auth/me")) return fakeResponse(200, CURRENT_USER);
      if (url.includes("/campaigns")) return fakeResponse(200, { items: [] });
      throw new Error(`unexpected fetch call to ${url}`);
    });

    render(<CampaignList />);
    expect(await screen.findByText(/belum punya campaign/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /buat campaign baru/i })).toBeInTheDocument();
  });

  it("shows an error state with a retry button", async () => {
    vi.stubGlobal("fetch", () =>
      fakeResponse(500, { error: { code: "galat_server", message: "Server sedang bermasalah." } }),
    );

    render(<CampaignList />);
    const alert = await screen.findByRole("alert");
    expect(await within(alert).findByText(/server sedang bermasalah/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /coba lagi/i })).toBeInTheDocument();
  });

  it("never renders the create-campaign action twice, whether the list is empty or not", async () => {
    // Laporan review: app/investor/campaign/page.tsx dulu merender tombol
    // header "Buat campaign baru" SENDIRI, lalu CampaignList merender aksi
    // EmptyState dengan label identik begitu daftar kosong, dua tombol aksen
    // bertumpuk. Halaman sekarang tidak lagi punya salinannya sendiri (lihat
    // app/investor/campaign/page.tsx); test ini mengunci itu dari sisi
    // CampaignList untuk kedua keadaan, kosong maupun terisi.
    vi.stubGlobal("fetch", (url: string) => {
      if (url.includes("/auth/me")) return fakeResponse(200, CURRENT_USER);
      if (url.includes("/campaigns")) return fakeResponse(200, { items: [] });
      throw new Error(`unexpected fetch call to ${url}`);
    });
    render(<CampaignList />);
    expect(await screen.findAllByText(/buat campaign baru/i)).toHaveLength(1);
  });

  it("renders exactly one create-campaign link once the investor already has a campaign", async () => {
    vi.stubGlobal("fetch", (url: string) => {
      if (url.includes("/auth/me")) return fakeResponse(200, CURRENT_USER);
      if (url.includes("/campaigns")) return fakeResponse(200, { items: [BASE_CAMPAIGN] });
      throw new Error(`unexpected fetch call to ${url}`);
    });
    render(<CampaignList />);
    expect(await screen.findAllByText(/buat campaign baru/i)).toHaveLength(1);
  });
});
