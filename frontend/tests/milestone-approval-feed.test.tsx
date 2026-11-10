import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MilestoneApprovalFeed } from "@/components/MilestoneApprovalFeed";

vi.mock("@/lib/auth", async () => {
  const actual = await vi.importActual<typeof import("@/lib/auth")>("@/lib/auth");
  return { ...actual, fetchCurrentUser: vi.fn() };
});

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { get: vi.fn(), post: vi.fn() } };
});

import { api } from "@/lib/api";
import { fetchCurrentUser } from "@/lib/auth";

const ME = { id: "inv1", email: "investor@contoh.id", name: "Investor Satu", role: "investor" as const, created_at: "2026-01-01T00:00:00Z" };

afterEach(() => {
  vi.clearAllMocks();
});

describe("MilestoneApprovalFeed: hero amount", () => {
  it("shows the real sum of amounts awaiting disbursement across the queue, as the screen's single lime accent", async () => {
    vi.mocked(fetchCurrentUser).mockResolvedValue(ME);
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path === "/proposals") {
        return {
          items: [
            { id: "p1", business_name: "Kopi Senja", status: "funded", lead_investor_id: "inv1" },
            { id: "p2", business_name: "Batik Lereng", status: "funded", lead_investor_id: "inv1" },
          ],
        };
      }
      if (path === "/proposals/p1/milestones") {
        return { items: [{ id: "m1", seq: 1, title: "Beli mesin", amount: 5_000_000, status: "pending" }] };
      }
      if (path === "/proposals/p2/milestones") {
        return { items: [{ id: "m2", seq: 1, title: "Bahan baku", amount: 3_000_000, status: "pending" }] };
      }
      throw new Error(`permintaan tak terduga: ${path}`);
    });

    const { container } = render(<MilestoneApprovalFeed />);
    expect(await screen.findByText("Total menunggu pencairan Anda")).toBeInTheDocument();
    expect(screen.getByText("Rp8.000.000")).toBeInTheDocument();
    // Satu-satunya kemunculan --accent di layar ini: lihat komentar di
    // MilestoneApprovalFeed.tsx. MilestoneTimeline/ApprovalQueue sendiri
    // tidak lagi memakai bg-accent sama sekali (lihat milestone.test.tsx).
    // text-accent-text, bukan text-accent: yang terakhir adalah token latar
    // dan gagal 1,09:1 dipakai sebagai teks di tema terang (Amount.tsx).
    expect(container.querySelectorAll(".bg-accent").length).toBe(0);
    expect(container.querySelectorAll(".text-accent-text").length).toBe(1);
  });

  it("hides the hero amount instead of showing a fabricated zero when nothing is waiting", async () => {
    vi.mocked(fetchCurrentUser).mockResolvedValue(null);
    render(<MilestoneApprovalFeed />);
    expect(await screen.findByText(/belum ada laporan yang menunggu/i)).toBeInTheDocument();
    expect(screen.queryByText("Total menunggu pencairan Anda")).toBeNull();
  });
});
