import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import UmkmBeranda from "@/app/umkm/beranda/page";
import ProposalBaru from "@/app/umkm/proposal/baru/page";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { get: vi.fn(), post: vi.fn() } };
});

import { api } from "@/lib/api";

afterEach(() => {
  vi.clearAllMocks();
});

describe("umkm beranda", () => {
  it("names why it is empty and offers an action leading to the submission form", async () => {
    vi.mocked(api.get).mockResolvedValueOnce([]);
    render(<UmkmBeranda />);
    expect(await screen.findByText(/belum (ada|pernah) mengajukan proposal/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /ajukan proposal/i }));
    expect(push).toHaveBeenCalledWith("/umkm/proposal/baru");
  });

  it("offers a rescore action and never implies rejection when scoring failed technically", async () => {
    vi.mocked(api.get).mockResolvedValueOnce([
      {
        id: "p1",
        business_name: "Warung Kopi Berkah",
        requested_amount: 10_000_000,
        status: "submitted",
        scoring_status: "failed",
      },
    ]);
    render(<UmkmBeranda />);
    const kartu = await screen.findByText(/Warung Kopi Berkah/i);
    const area = kartu.closest("[data-testid='kartu-proposal']") ?? kartu.parentElement!;
    expect(screen.getByRole("button", { name: /nilai ulang/i })).toBeInTheDocument();
    // D-09: kegagalan teknis mesin skor bukan penolakan usaha. Kata-kata yang
    // berarti "ditolak" tidak boleh muncul sama sekali di kartu ini.
    expect(area.textContent).not.toMatch(/ditolak/i);
    expect(area.textContent).not.toMatch(/tidak lolos/i);
  });

  it("shows the score panel including a red flag for a proposal that was already scored", async () => {
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path === "/proposals/mine") {
        return [
          {
            id: "p2",
            business_name: "Batik Senja",
            requested_amount: 20_000_000,
            status: "listed",
            scoring_status: "done",
          },
        ];
      }
      if (path === "/proposals/p2/scoring") {
        return {
          fit_score: 30,
          data_quality_score: 20,
          impact_score: 18,
          red_flags: [
            {
              code: "rencana_dana_kabur",
              severity: "warning",
              message: "Rencana penggunaan dana tidak merinci porsi per pos.",
              evidence: "dana akan dipakai untuk kebutuhan usaha",
            },
          ],
          brief: {
            strengths: ["Lokasi strategis"],
            risks: ["Rencana dana kurang rinci"],
            recommendation: "Perlu rincian penggunaan dana.",
          },
        };
      }
      throw new Error(`permintaan tak terduga: ${path}`);
    });
    render(<UmkmBeranda />);
    await screen.findByText(/Batik Senja/i);
    expect(await screen.findByText(/rencana penggunaan dana tidak merinci porsi per pos/i))
      .toBeInTheDocument();
  });
});

describe("umkm proposal submission", () => {
  // GET /campaigns membungkus daftarnya dalam { items: [...] }
  // (backend/app/schemas/campaign.py: CampaignListOut), bukan array mentah.
  // Mock ini dulu memakai array mentah, yang lolos tsc dan test unit tapi
  // mengkonfirmasi bentuk yang salah: halaman sungguhan melempar TypeError
  // terhadap backend asli (laporan Fase 11 Task 12).
  function mockCampaigns(overrides: Partial<{ apply_deadline: string }> = {}) {
    vi.mocked(api.get).mockResolvedValueOnce({
      items: [
        {
          id: "c1",
          title: "UMKM Kuliner Jabodetabek",
          target_amount: 50_000_000,
          apply_deadline: overrides.apply_deadline ?? "2099-01-01T00:00:00Z",
        },
      ],
    });
  }

  it("refuses submission to a campaign whose apply deadline has passed, stating the reason before sending", async () => {
    mockCampaigns({ apply_deadline: "2020-01-01T00:00:00Z" });
    render(<ProposalBaru />);
    await screen.findByRole("heading", { name: /ajukan proposal/i });
    expect(screen.getByRole("alert").textContent).toMatch(/tenggat/i);
    expect(screen.getByRole("button", { name: /kirim proposal/i })).toBeDisabled();
    expect(api.post).not.toHaveBeenCalled();
  });

  it("rejects a fund usage plan shorter than the minimum, stating how many more characters are needed", async () => {
    mockCampaigns();
    render(<ProposalBaru />);
    await screen.findByRole("heading", { name: /ajukan proposal/i });

    await userEvent.type(screen.getByLabelText(/^nama usaha/i), "Warung Kopi Berkah");
    await userEvent.type(
      screen.getByLabelText(/^profil usaha/i),
      "Usaha warung kopi rumahan yang sudah berjalan tiga tahun di Bandung dengan dua orang pekerja tetap dan omzet stabil setiap bulannya.",
    );
    await userEvent.type(screen.getByLabelText(/^rencana penggunaan dana/i), "beli mesin kopi");

    await waitFor(() => {
      expect(screen.getByText(/rencana penggunaan dana masih kurang \d+ karakter/i)).toBeInTheDocument();
    });
    expect(api.post).not.toHaveBeenCalled();
  });
});
