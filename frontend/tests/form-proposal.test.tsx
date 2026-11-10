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

  it("gives the delete-stage button an interactive-boundary border, not the decorative one", async () => {
    // Laporan review: tombol "Hapus tahap" memakai border-line (1.27:1
    // terhadap bg-panel), gagal ambang 3:1 untuk batas kontrol interaktif.
    // Satu-satunya batas interaktif di aplikasi ini yang terlewat saat
    // batas lain sudah dipindahkan ke border-line-strong (3.62:1).
    render(<ProposalForm requestedAmount={10_000_000} />);
    await userEvent.click(screen.getByRole("button", { name: /tambah tahap/i }));
    const hapus = screen.getByRole("button", { name: /hapus tahap 3/i });
    const classes = hapus.className.split(/\s+/);
    expect(classes).toContain("border-line-strong");
    expect(classes).not.toContain("border-line");
  });

  it("rejects a fractional value typed into the amount column", async () => {
    render(<ProposalForm requestedAmount={10_000_000} />);
    const kolom = nominalField(0);
    await userEvent.type(kolom, "5000000.5");
    expect(nominalField(0)).toHaveValue("5000000");
  });

  it("shows a numeric keypad on mobile for both money inputs, matching CampaignForm's treatment of the same kind of value", () => {
    // Laporan review: nominal milestone dan nominal proposal dulu
    // type="text" tanpa inputMode sama sekali, jadi ponsel menampilkan
    // keyboard huruf untuk nominal rupiah, sementara CampaignForm sudah
    // type="number" untuk field sejenis. inputMode="numeric" menyamakan
    // keypadnya tanpa kehilangan filter digit kustom (type tetap "text").
    render(<ProposalForm requestedAmount={10_000_000} />);
    expect(screen.getByLabelText(/jumlah dana yang diminta/i)).toHaveAttribute("inputmode", "numeric");
    nominalField(0);
    screen.getAllByLabelText(/nominal tahap/i).forEach((field) => {
      expect(field).toHaveAttribute("inputmode", "numeric");
    });
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
