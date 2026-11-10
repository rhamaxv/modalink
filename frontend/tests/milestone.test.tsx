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

  it("shows the latest report's narrative together with the reviewer's rejection note", () => {
    // GET /proposals/{id}/milestones (10-api-contract.md baris 73) hanya
    // mengirim satu laporan terbaru lewat `latest_report`, bukan array
    // riwayat `reports`: test ini mencerminkan bentuk wire yang sungguhan,
    // bukan bentuk yang pernah dibayangkan komponen (lihat laporan Fase 12).
    const milestones: Milestone[] = [
      {
        id: "m2",
        seq: 2,
        status: "pending",
        amount: 5_000_000,
        title: "Bahan baku",
        latest_report: {
          review_status: "rejected",
          narrative: "Revisi dengan bukti nota.",
          reviewer_note: "Angka omzet belum disertai bukti.",
        },
      },
    ];
    render(<MilestoneTimeline milestones={milestones} />);
    expect(screen.getByText(/Angka omzet belum disertai bukti/)).toBeInTheDocument();
    expect(screen.getByText(/Revisi dengan bukti nota/)).toBeInTheDocument();
  });

  it("lets the lead investor read the pending report's narrative before any decision button renders", () => {
    // Defek yang ditemukan review: lead investor bisa menyetujui pencairan
    // tanpa pernah melihat laporannya. Test ini membuktikan narasi laporan
    // sungguhan tampil di DOM, bukan hanya disebut di komentar kode.
    const milestones: Milestone[] = [
      {
        id: "m1",
        seq: 2,
        status: "reported",
        amount: 5_000_000,
        title: "Bahan baku",
        latest_report: { review_status: "pending", narrative: "Omzet bulan ini naik 20%." },
      },
    ];
    render(<MilestoneTimeline milestones={milestones} isLeadInvestor />);
    expect(screen.getByText(/Omzet bulan ini naik 20%/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /setujui/i })).toBeInTheDocument();
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

  it("stays within the three-lime-accent budget regardless of how many entries the queue holds", () => {
    // Audit browser menemukan EMPAT kemunculan --accent pada investor/milestone
    // dengan dua entri antrian, karena MilestoneTimeline dulu merender dua
    // aksen lime per entri (lencana "Tahap berjalan" + tombol "Setujui") tanpa
    // batas. DESIGN.md menghitung anggaran per LAYAR, bukan per entri, jadi
    // test ini memakai TIGA entri justru untuk membuktikan jumlahnya tidak
    // ikut bertambah seiring panjang antrian.
    const entry = (seq: number) => ({
      id: `m${seq}`,
      proposalId: `p${seq}`,
      businessName: `Usaha ${seq}`,
      seq,
      status: "reported" as const,
      amount: 5_000_000,
      title: "Bahan baku",
    });
    const { container } = render(
      <ApprovalQueue milestones={[entry(2), entry(3), entry(4)]} />,
    );
    expect(container.querySelectorAll(".bg-accent").length).toBe(0);
  });
});
