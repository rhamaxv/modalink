import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ScorePanel } from "@/components/ScorePanel";

const score = {
  fit_score: 34,
  data_quality_score: 21,
  impact_score: 18,
  total_score: 73,
  threshold_used: 60,
  model_name: "gemini-2.5-flash",
  created_at: "2026-11-07T10:00:00Z",
  red_flags: [
    {
      code: "projeksi_tidak_realistis",
      severity: "critical" as const,
      message: "Proyeksi omzet naik 40 kali lipat dalam 6 bulan.",
      evidence: "target omzet Rp400 juta per bulan",
    },
  ],
  brief: {
    strengths: ["Usaha berjalan 3 tahun."],
    risks: ["Proyeksi agresif."],
    recommendation: "Minta rincian asumsi proyeksi.",
  },
};

describe("score panel", () => {
  it("shows the three score components with their maximum", () => {
    render(<ScorePanel score={score} />);
    expect(screen.getByText("34")).toBeInTheDocument();
    expect(screen.getByText(/dari 40/)).toBeInTheDocument();
    expect(screen.getAllByText(/dari 30/).length).toBeGreaterThan(0);
  });

  it("shows the campaign threshold next to the total", () => {
    render(<ScorePanel score={score} />);
    expect(screen.getByText(/ambang campaign: 60/i)).toBeInTheDocument();
  });

  it("a red flag shows its severity and evidence quote", () => {
    render(<ScorePanel score={score} />);
    expect(screen.getByText(/kritis/i)).toBeInTheDocument();
    expect(screen.getByText(/target omzet Rp400 juta per bulan/)).toBeInTheDocument();
  });

  it("red flag severity is not conveyed by colour alone", () => {
    render(<ScorePanel score={score} />);
    // Teks "kritis" harus benar-benar ada sebagai teks terbaca, bukan span kosong berwarna.
    const label = screen.getByText(/kritis/i);
    expect(label.textContent?.trim().length).toBeGreaterThan(0);
  });

  it("names the model and when it was scored", () => {
    render(<ScorePanel score={score} />);
    expect(screen.getByText(/gemini-2.5-flash/)).toBeInTheDocument();
  });

  it("states that the final decision rests with the investor", () => {
    render(<ScorePanel score={score} />);
    expect(screen.getByText(/keputusan akhir ada di/i)).toBeInTheDocument();
  });

  it("shows a 'still scoring' state while scoring is not finished", () => {
    render(<ScorePanel score={null} scoringStatus="processing" />);
    expect(screen.getByText(/sedang dinilai/i)).toBeInTheDocument();
  });

  it("shows a rescore button when scoring failed, not a rejection message", () => {
    render(<ScorePanel score={null} scoringStatus="failed" />);
    expect(screen.getByRole("button", { name: /nilai ulang/i })).toBeInTheDocument();
    expect(screen.queryByText(/ditolak/i)).toBeNull();
  });

  it("renders the AI brief's strengths and risks, not only the recommendation", () => {
    // Sebelumnya brief.strengths dan brief.risks hanya dideklarasikan di tipe
    // ScoreBrief, tidak pernah mencapai layar: hanya recommendation yang
    // dirender, padahal halaman jelajah menjanjikan investor bisa membaca
    // brief AI (laporan tinjauan minggu ini, R-26/R-38).
    render(<ScorePanel score={score} />);
    expect(screen.getByText(/usaha berjalan 3 tahun/i)).toBeInTheDocument();
    expect(screen.getByText(/proyeksi agresif/i)).toBeInTheDocument();
  });

  it("keeps strengths and risks behind a closed disclosure until opened, operable without JavaScript event wiring", () => {
    render(<ScorePanel score={score} />);
    const rincian = screen.getByText(/lihat kekuatan dan risiko/i).closest("details");
    expect(rincian).not.toBeNull();
    expect(rincian).not.toHaveAttribute("open");
  });

  it("does not use the accent colour, which this screen reserves for funding and pledging", () => {
    // PanelSkor adalah informasi, bukan aksi: DESIGN.md menyimpan aksen untuk
    // bilah funding, tombol pledge, dan penanda milestone aktif.
    const { container } = render(<ScorePanel score={score} />);
    expect(container.innerHTML).not.toMatch(/bg-accent/);
  });
});
