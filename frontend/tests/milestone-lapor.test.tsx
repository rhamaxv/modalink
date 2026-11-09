import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import MilestoneLapor from "@/app/umkm/milestone/[id]/lapor/page";

const useParams = vi.fn();
const useSearchParams = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: () => useParams(),
  useSearchParams: () => useSearchParams(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { get: vi.fn(), post: vi.fn() } };
});

import { api } from "@/lib/api";

function setRoute(milestoneId: string, proposalId = "p1") {
  useParams.mockReturnValue({ id: milestoneId });
  useSearchParams.mockReturnValue(new URLSearchParams(`proposal=${proposalId}`));
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("milestone report page", () => {
  it("shows no report form for seq 1 but a report form for seq 2", async () => {
    const tahap1 = { id: "m1", seq: 1, title: "Tahap 1", amount: 5_000_000, status: "pending", last_report: null };
    const tahap2 = { id: "m2", seq: 2, title: "Tahap 2", amount: 5_000_000, status: "pending", last_report: null };
    const milestones = [tahap1, tahap2];
    vi.mocked(api.get).mockImplementation(async () => milestones.map((m) => ({ ...m })));

    setRoute("m1");
    const seq1 = render(<MilestoneLapor />);
    await screen.findByText(/menunggu persetujuan/i);
    expect(seq1.queryByLabelText(/laporan progres/i)).toBeNull();
    seq1.unmount();

    // Tahap 2 prasyaratnya (tahap 1) belum cair, jadi belum berupa form juga,
    // tapi dengan alasan yang berbeda: ini bukti bahwa seq 1 dan seq 2 memang
    // diperlakukan berbeda, bukan kebetulan sama-sama tidak tampil.
    tahap1.status = "disbursed";
    setRoute("m2");
    render(<MilestoneLapor />);
    await screen.findByLabelText(/laporan progres/i);
    expect(screen.queryByText(/menunggu persetujuan/i)).toBeNull();
  });

  it("names the unmet prerequisite and keeps the report form unreachable", async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: "m1", seq: 1, title: "Tahap 1", amount: 5_000_000, status: "pending", last_report: null },
      { id: "m2", seq: 2, title: "Tahap 2", amount: 5_000_000, status: "pending", last_report: null },
    ]);
    setRoute("m2");
    render(<MilestoneLapor />);
    expect(await screen.findByText(/tahap 1.*belum cair/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/laporan progres/i)).toBeNull();
  });

  it("names the pending review status and refuses to resend an already submitted report", async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: "m1", seq: 1, title: "Tahap 1", amount: 5_000_000, status: "disbursed", last_report: null },
      {
        id: "m2",
        seq: 2,
        title: "Tahap 2",
        amount: 5_000_000,
        status: "reported",
        last_report: { id: "r1", narrative: "Progres bulan ini...", status: "pending_review", rejection_note: null },
      },
    ]);
    setRoute("m2");
    render(<MilestoneLapor />);
    expect((await screen.findAllByText(/menunggu review/i)).length).toBeGreaterThan(0);
    expect(screen.queryByLabelText(/laporan progres/i)).toBeNull();
    expect(screen.queryByRole("button", { name: /kirim laporan/i })).toBeNull();
  });
});
