import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ApprovalQueue, MilestoneTimeline, type Milestone } from "@/components/MilestoneTimeline";

describe("MilestoneTimeline", () => {
  it("marks the stage awaiting a decision as active and distinguishes it from a disbursed one in text", () => {
    const milestones: Milestone[] = [
      { id: "m1", seq: 1, status: "disbursed", amount: 5_000_000, title: "Beli mesin" },
      { id: "m2", seq: 2, status: "reported", amount: 5_000_000, title: "Bahan baku" },
    ];
    render(<MilestoneTimeline milestones={milestones} />);
    expect(screen.getByText(/menunggu persetujuan/i)).toBeInTheDocument();
    expect(screen.getByText(/sudah cair/i)).toBeInTheDocument();
  });

  it("never conveys a stage's status through colour alone", () => {
    const milestones: Milestone[] = [
      { id: "m1", seq: 1, status: "disbursed", amount: 5_000_000, title: "Beli mesin" },
      { id: "m2", seq: 2, status: "reported", amount: 5_000_000, title: "Bahan baku" },
    ];
    const { container } = render(<MilestoneTimeline milestones={milestones} />);
    container.querySelectorAll("[data-status]").forEach((el) => {
      expect(el.textContent?.trim()).not.toBe("");
    });
  });

  it("shows the approve button only to the lead investor", () => {
    const milestones: Milestone[] = [
      { id: "m1", seq: 1, status: "reported", amount: 5_000_000, title: "Beli mesin" },
    ];
    const { rerender } = render(<MilestoneTimeline milestones={milestones} isLeadInvestor={false} />);
    expect(screen.queryByRole("button", { name: /setujui/i })).toBeNull();

    rerender(<MilestoneTimeline milestones={milestones} isLeadInvestor />);
    expect(screen.getByRole("button", { name: /setujui/i })).toBeInTheDocument();
  });

  it("opens a note field on reject and disables the submit until the note is long enough", async () => {
    const milestones: Milestone[] = [
      { id: "m1", seq: 1, status: "reported", amount: 5_000_000, title: "Beli mesin" },
    ];
    render(<MilestoneTimeline milestones={milestones} isLeadInvestor />);
    await userEvent.click(screen.getByRole("button", { name: /tolak/i }));
    await userEvent.type(screen.getByLabelText(/catatan/i), "ok");
    expect(screen.getByRole("button", { name: /kirim penolakan/i })).toBeDisabled();
  });

  it("enables reject submit once the note reaches ten characters", async () => {
    const milestones: Milestone[] = [
      { id: "m1", seq: 1, status: "reported", amount: 5_000_000, title: "Beli mesin" },
    ];
    render(<MilestoneTimeline milestones={milestones} isLeadInvestor />);
    await userEvent.click(screen.getByRole("button", { name: /tolak/i }));
    await userEvent.type(screen.getByLabelText(/catatan/i), "Belum ada bukti nota.");
    expect(screen.getByRole("button", { name: /kirim penolakan/i })).toBeEnabled();
  });

  it("keeps a rejected report's revision history visible together with the reviewer's note", () => {
    const milestones: Milestone[] = [
      {
        id: "m2",
        seq: 2,
        status: "pending",
        amount: 5_000_000,
        title: "Bahan baku",
        reports: [
          {
            review_status: "rejected",
            narrative: "Laporan awal.",
            reviewer_note: "Angka omzet belum disertai bukti.",
          },
          { review_status: "pending", narrative: "Revisi dengan bukti." },
        ],
      },
    ];
    render(<MilestoneTimeline milestones={milestones} />);
    expect(screen.getByText(/Angka omzet belum disertai bukti/)).toBeInTheDocument();
    expect(screen.getByText(/Laporan awal/)).toBeInTheDocument();
    expect(screen.getByText(/Revisi dengan bukti/)).toBeInTheDocument();
  });

  it("lets the first milestone be approved without a report", () => {
    const milestones: Milestone[] = [
      { id: "m1", seq: 1, status: "pending", amount: 5_000_000, title: "Beli mesin" },
      { id: "m2", seq: 2, status: "pending", amount: 5_000_000, title: "Bahan baku" },
    ];
    render(<MilestoneTimeline milestones={milestones} isLeadInvestor />);
    expect(screen.getByRole("button", { name: /setujui/i })).toBeInTheDocument();
    // Tahap kedua belum bisa diajukan laporan sebelum tahap pertama cair
    // (BR-43), jadi ia tidak dapat tombol aksi sendiri.
    expect(screen.getAllByRole("button", { name: /setujui/i })).toHaveLength(1);
  });
});

describe("ApprovalQueue", () => {
  it("shows an honest empty state, not a bare placeholder, when nothing needs approval", () => {
    render(<ApprovalQueue milestones={[]} />);
    expect(screen.getByText(/belum ada laporan yang menunggu/i)).toBeInTheDocument();
    expect(screen.queryByText(/tidak ada data/i)).toBeNull();
  });

  it("renders one timeline per proposal waiting on a decision, linked to its detail page", () => {
    render(
      <ApprovalQueue
        milestones={[
          {
            id: "m9",
            proposalId: "p9",
            businessName: "Kopi Senja",
            seq: 2,
            status: "reported",
            amount: 8_000_000,
            title: "Bahan baku",
          },
        ]}
      />,
    );
    expect(screen.getByText("Kopi Senja")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Kopi Senja" })).toHaveAttribute("href", "/proposal/p9");
  });
});
