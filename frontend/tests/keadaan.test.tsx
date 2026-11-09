import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { KeadaanGalat, KeadaanKosong, KeadaanMuat } from "@/components/ui";

describe("keadaan kosong", () => {
  it("menyebut sebabnya dan satu aksi berikutnya", () => {
    render(<KeadaanKosong
      sebab="Belum ada proposal masuk ke campaign ini."
      aksi={{ label: "Bagikan tautan campaign", onClick: () => {} }} />);
    expect(screen.getByText(/Belum ada proposal masuk/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Bagikan tautan campaign/ }))
      .toBeInTheDocument();
  });

  it("tidak pernah menampilkan teks 'Tidak ada data'", () => {
    // R-27: keadaan kosong harus menyebut sebab dan aksi, bukan label hampa.
    render(<KeadaanKosong sebab="Belum ada pledge." />);
    expect(screen.queryByText(/tidak ada data/i)).toBeNull();
  });
});

describe("keadaan muat", () => {
  it("menyebut apa yang sedang dimuat", () => {
    render(<KeadaanMuat label="Memuat daftar proposal" />);
    expect(screen.getByText(/Memuat daftar proposal/)).toBeInTheDocument();
  });

  it("memesan ruang dengan tinggi yang diminta supaya layout tidak melompat", () => {
    render(<KeadaanMuat label="Memuat daftar proposal" tinggiMinimum={240} />);
    const wadah = screen.getByTestId("keadaan-muat");
    expect(wadah.style.minHeight).toBe("240px");
  });
});

describe("keadaan galat", () => {
  it("menyebut penyebab dan menyediakan tombol coba lagi", () => {
    const coba = vi.fn();
    render(<KeadaanGalat pesan="Koneksi ke server bermasalah." onCobaLagi={coba} />);
    expect(screen.getByText(/Koneksi ke server bermasalah/)).toBeInTheDocument();
    screen.getByRole("button", { name: /Coba lagi/ }).click();
    expect(coba).toHaveBeenCalledOnce();
  });

  it("mengumumkan dirinya ke pembaca layar", () => {
    render(<KeadaanGalat pesan="Gagal memuat." onCobaLagi={() => {}} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
