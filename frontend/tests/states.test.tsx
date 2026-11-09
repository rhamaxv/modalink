import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui";

describe("empty state", () => {
  it("names the reason and offers one next action", () => {
    render(<EmptyState
      reason="Belum ada proposal masuk ke campaign ini."
      action={{ label: "Bagikan tautan campaign", onClick: () => {} }} />);
    expect(screen.getByText(/Belum ada proposal masuk/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Bagikan tautan campaign/ }))
      .toBeInTheDocument();
  });

  it("never shows an empty 'Tidak ada data' label", () => {
    // R-27: keadaan kosong harus menyebut sebab dan aksi, bukan label hampa.
    render(<EmptyState reason="Belum ada pledge." />);
    expect(screen.queryByText(/tidak ada data/i)).toBeNull();
  });
});

describe("loading state", () => {
  it("names what is loading", () => {
    render(<LoadingState label="Memuat daftar proposal" />);
    expect(screen.getByText(/Memuat daftar proposal/)).toBeInTheDocument();
  });

  it("reserves the requested height so the layout does not shift", () => {
    render(<LoadingState label="Memuat daftar proposal" minHeight={240} />);
    const container = screen.getByTestId("loading-state");
    expect(container.style.minHeight).toBe("240px");
  });

  it("reserves a non-zero default height when the caller does not specify one", () => {
    // Pemanggil yang lupa mengisi minHeight tidak boleh jatuh ke 0 lalu
    // membuat layout melompat begitu data datang.
    render(<LoadingState label="Memuat daftar proposal" />);
    const container = screen.getByTestId("loading-state");
    expect(Number.parseInt(container.style.minHeight, 10)).toBeGreaterThan(0);
  });
});

describe("error state", () => {
  it("names the cause and provides a retry button", () => {
    const retry = vi.fn();
    render(<ErrorState message="Koneksi ke server bermasalah." onRetry={retry} />);
    expect(screen.getByText(/Koneksi ke server bermasalah/)).toBeInTheDocument();
    screen.getByRole("button", { name: /Coba lagi/ }).click();
    expect(retry).toHaveBeenCalledOnce();
  });

  it("announces itself to screen readers", () => {
    render(<ErrorState message="Gagal memuat." onRetry={() => {}} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
