import { describe, expect, it } from "vitest";
import { formatRupiah, persenProgres } from "@/lib/money";

describe("formatRupiah", () => {
  it("memakai titik sebagai pemisah ribuan", () => {
    expect(formatRupiah(5_000_000)).toBe("Rp5.000.000");
    expect(formatRupiah(750)).toBe("Rp750");
  });

  it("nol tetap ditampilkan, bukan string kosong", () => {
    expect(formatRupiah(0)).toBe("Rp0");
  });

  it("menolak nilai bukan integer alih-alih membulatkan diam-diam", () => {
    expect(() => formatRupiah(1_000_000.5)).toThrow();
    expect(() => formatRupiah(Number.NaN)).toThrow();
  });
});

describe("persenProgres", () => {
  it("menghitung persentase bulat", () => {
    expect(persenProgres(4_000_000, 10_000_000)).toBe(40);
  });

  it("tepat penuh menghasilkan 100, bukan 99", () => {
    expect(persenProgres(10_000_000, 10_000_000)).toBe(100);
  });

  it("hampir penuh tidak dibulatkan menjadi 100", () => {
    // 99,99% harus terbaca 99, karena 100% berarti funded.
    expect(persenProgres(9_999_000, 10_000_000)).toBe(99);
  });

  it("target nol tidak menghasilkan NaN", () => {
    expect(persenProgres(0, 0)).toBe(0);
  });
});
