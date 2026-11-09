import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ProposalForm } from "@/components/ProposalForm";

// Helper mengisi nominal tiap tahap milestone. Dipakai fireEvent.change,
// bukan userEvent.type: tes ini menguji apakah teks selisih ikut berubah,
// bukan menguji simulasi pengetikan karakter per karakter (itu milik tes
// penolakan nominal pecahan di bawah, yang memang butuh userEvent.type).
// fireEvent.change juga tidak memindahkan fokus browser seperti userEvent,
// sehingga tes "tanpa memindahkan fokus" di bawah tetap valid.
function fillMilestones(amounts: number[]) {
  const fields = screen.getAllByLabelText(/nominal tahap/i);
  amounts.forEach((amount, index) => {
    const field = fields[index];
    if (!field) throw new Error(`Kolom nominal tahap ke-${index + 1} tidak ditemukan.`);
    fireEvent.change(field, { target: { value: String(amount) } });
  });
}

function nominalField(index: number): HTMLElement {
  const field = screen.getAllByLabelText(/nominal tahap/i)[index];
  if (!field) throw new Error(`Kolom nominal tahap ke-${index + 1} tidak ditemukan.`);
  return field;
}

describe("milestone plan", () => {
  it("shows the shortfall when the milestone sum is below the requested amount", () => {
    render(<ProposalForm requestedAmount={10_000_000} />);
    fillMilestones([5_000_000, 4_000_000]);
    expect(screen.getByRole("status")).toHaveTextContent("Kurang Rp1.000.000 dari dana yang diminta");
  });

  it("shows the excess when the milestone sum is above the requested amount", () => {
    render(<ProposalForm requestedAmount={10_000_000} />);
    fillMilestones([6_000_000, 6_000_000]);
    expect(screen.getByRole("status")).toHaveTextContent("Lebih Rp2.000.000 dari dana yang diminta");
  });

  it("marks the sum as matched when it equals the requested amount exactly", () => {
    render(<ProposalForm requestedAmount={10_000_000} />);
    fillMilestones([5_000_000, 5_000_000]);
    expect(screen.getByRole("status")).toHaveTextContent("Jumlah sudah pas");
  });

  it("keeps the submit button disabled while the sum does not match", () => {
    render(<ProposalForm requestedAmount={10_000_000} />);
    fillMilestones([5_000_000, 4_000_000]);
    expect(screen.getByRole("button", { name: /kirim proposal/i })).toBeDisabled();
  });

  it("offers no delete button while exactly the minimum two rows exist", () => {
    render(<ProposalForm requestedAmount={10_000_000} />);
    const hapus = screen.queryAllByRole("button", { name: /hapus tahap/i });
    expect(hapus).toHaveLength(0);
  });

  it("rejects a fractional value typed into the amount column", async () => {
    render(<ProposalForm requestedAmount={10_000_000} />);
    const kolom = nominalField(0);
    await userEvent.type(kolom, "5000000.5");
    expect(nominalField(0)).toHaveValue("5000000");
  });

  it("announces the shortfall to screen readers without stealing focus", () => {
    render(<ProposalForm requestedAmount={10_000_000} />);
    const kolom = nominalField(0);
    kolom.focus();
    fillMilestones([5_000_000, 4_000_000]);
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
    expect(document.activeElement).toBe(kolom);
  });
});
