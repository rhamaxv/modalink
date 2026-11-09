import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Nominal } from "@/components/ui/Nominal";

describe("Nominal", () => {
  it("menampilkan label di atas nominal rupiah yang tabular", () => {
    render(<Nominal label="Terkumpul" nominal={4_000_000} />);
    expect(screen.getByText("Terkumpul")).toBeInTheDocument();
    const nilai = screen.getByText("Rp4.000.000");
    expect(nilai).toBeInTheDocument();
    expect(nilai.className).toContain("tabular");
  });
});
