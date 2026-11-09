import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Amount } from "@/components/ui/Amount";

describe("Amount", () => {
  it("menampilkan label di atas nominal rupiah yang tabular", () => {
    render(<Amount label="Terkumpul" amount={4_000_000} />);
    expect(screen.getByText("Terkumpul")).toBeInTheDocument();
    const nilai = screen.getByText("Rp4.000.000");
    expect(nilai).toBeInTheDocument();
    expect(nilai.className).toContain("tabular");
  });
});
