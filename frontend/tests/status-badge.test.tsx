import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "@/components/ui/StatusBadge";

describe("StatusBadge", () => {
  it("renders the Indonesian label for a known status", () => {
    render(<StatusBadge status="partially_funded" />);
    expect(screen.getByText("Sebagian terdanai")).toBeInTheDocument();
  });

  it("renders an unknown status verbatim instead of hiding it", () => {
    // Status baru dari backend harus terlihat di UI, bukan hilang tanpa jejak.
    render(<StatusBadge status="status_yang_belum_ada" />);
    expect(screen.getByText("status_yang_belum_ada")).toBeInTheDocument();
  });

  it("never uses the accent colour, which DESIGN.md reserves for three moments", () => {
    const { container } = render(<StatusBadge status="funded" />);
    const kelas = container.querySelector("span")?.className ?? "";
    expect(kelas).not.toMatch(/accent/);
  });

  it("distinguishes a status needing action from a successful one", () => {
    // Tanpa test ini seluruh badge bisa memakai satu warna dan tetap hijau.
    const { container: perlu } = render(<StatusBadge status="reported" />);
    const { container: berhasil } = render(<StatusBadge status="disbursed" />);
    const a = perlu.querySelector("span")?.className ?? "";
    const b = berhasil.querySelector("span")?.className ?? "";
    expect(a).not.toBe(b);
    expect(a).toMatch(/text-warn/);
    expect(b).toMatch(/text-ok/);
  });
});
