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

// GET /proposals/{id}/milestones membungkus daftarnya dalam { items: [...] }
// (backend/app/schemas/proposal.py: MilestoneListOut), bukan array mentah.
// Mock-mock di berkas ini dulu memakai array mentah, yang lolos tsc dan test
// unit tapi mengkonfirmasi bentuk yang salah: halaman sungguhan melempar
// TypeError terhadap backend asli (laporan Fase 11 Task 12).
describe("milestone report page", () => {
  it("shows no report form for seq 1 but a report form for seq 2", async () => {
    const tahap1 = { id: "m1", seq: 1, title: "Tahap 1", amount: 5_000_000, status: "pending", latest_report: null };
    const tahap2 = { id: "m2", seq: 2, title: "Tahap 2", amount: 5_000_000, status: "pending", latest_report: null };
    const milestones = [tahap1, tahap2];
    vi.mocked(api.get).mockImplementation(async () => ({ items: milestones.map((m) => ({ ...m })) }));

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
    vi.mocked(api.get).mockResolvedValue({
      items: [
        { id: "m1", seq: 1, title: "Tahap 1", amount: 5_000_000, status: "pending", latest_report: null },
        { id: "m2", seq: 2, title: "Tahap 2", amount: 5_000_000, status: "pending", latest_report: null },
      ],
    });
    setRoute("m2");
    render(<MilestoneLapor />);
    expect(await screen.findByText(/tahap 1.*belum cair/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/laporan progres/i)).toBeNull();
  });

  it("names the pending review status and refuses to resend an already submitted report", async () => {
    vi.mocked(api.get).mockResolvedValue({
      items: [
        { id: "m1", seq: 1, title: "Tahap 1", amount: 5_000_000, status: "disbursed", latest_report: null },
        {
          id: "m2",
          seq: 2,
          title: "Tahap 2",
          amount: 5_000_000,
          status: "reported",
          latest_report: { narrative: "Progres bulan ini...", review_status: "pending", reviewer_note: null },
        },
      ],
    });
    setRoute("m2");
    render(<MilestoneLapor />);
    expect((await screen.findAllByText(/menunggu review/i)).length).toBeGreaterThan(0);
    expect(screen.queryByLabelText(/laporan progres/i)).toBeNull();
    expect(screen.queryByRole("button", { name: /kirim laporan/i })).toBeNull();
  });

  it("shows the reviewer's note when the latest report on an otherwise reportable stage was rejected", async () => {
    // Defek yang ditemukan review: halaman dulu membaca
    // `last_report.status === "rejected"` dan `.rejection_note`, field yang
    // tidak pernah dikirim API (nama sungguhannya `latest_report.review_status`
    // dan `.reviewer_note`). UMKM yang laporannya ditolak tidak pernah melihat
    // catatan revisinya. Tahap di sini sudah kembali "pending" (BR-46: reject
    // mengembalikan milestone ke pending, bukan menjadikannya "reported"),
    // jadi form laporan baru tetap terbuka SEKALIGUS catatan revisinya tampil.
    vi.mocked(api.get).mockResolvedValue({
      items: [
        { id: "m1", seq: 1, title: "Tahap 1", amount: 5_000_000, status: "disbursed", latest_report: null },
        {
          id: "m2",
          seq: 2,
          title: "Tahap 2",
          amount: 5_000_000,
          status: "pending",
          latest_report: {
            narrative: "Progres bulan ini...",
            review_status: "rejected",
            reviewer_note: "Lampirkan nota pembelian bahan baku.",
          },
        },
      ],
    });
    setRoute("m2");
    render(<MilestoneLapor />);
    expect(await screen.findByText(/lampirkan nota pembelian bahan baku/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/laporan progres/i)).toBeInTheDocument();
  });
});
