import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui";

describe("keadaan kosong", () => {
  it("menyebut sebabnya dan satu aksi berikutnya", () => {
    render(<EmptyState
      reason="Belum ada proposal masuk ke campaign ini."
      action={{ label: "Bagikan tautan campaign", onClick: () => {} }} />);
    expect(screen.getByText(/Belum ada proposal masuk/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Bagikan tautan campaign/ }))
      .toBeInTheDocument();
  });

  it("tidak pernah menampilkan teks 'Tidak ada data'", () => {
    // R-27: keadaan kosong harus menyebut sebab dan aksi, bukan label hampa.
    render(<EmptyState reason="Belum ada pledge." />);
    expect(screen.queryByText(/tidak ada data/i)).toBeNull();
  });
});

describe("keadaan muat", () => {
  it("menyebut apa yang sedang dimuat", () => {
    render(<LoadingState label="Memuat daftar proposal" />);
    expect(screen.getByText(/Memuat daftar proposal/)).toBeInTheDocument();
  });

  it("memesan ruang dengan tinggi yang diminta supaya layout tidak melompat", () => {
    render(<LoadingState label="Memuat daftar proposal" minHeight={240} />);
    const container = screen.getByTestId("loading-state");
    expect(container.style.minHeight).toBe("240px");
  });
});

describe("keadaan galat", () => {
  it("menyebut penyebab dan menyediakan tombol coba lagi", () => {
    const retry = vi.fn();
    render(<ErrorState message="Koneksi ke server bermasalah." onRetry={retry} />);
    expect(screen.getByText(/Koneksi ke server bermasalah/)).toBeInTheDocument();
    screen.getByRole("button", { name: /Coba lagi/ }).click();
    expect(retry).toHaveBeenCalledOnce();
  });

  it("mengumumkan dirinya ke pembaca layar", () => {
    render(<ErrorState message="Gagal memuat." onRetry={() => {}} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
