export function formatRupiah(nominal: number): string {
  if (!Number.isInteger(nominal)) {
    throw new TypeError("Nominal rupiah harus bilangan bulat.");
  }
  return `Rp${nominal.toLocaleString("id-ID")}`;
}

export function persenProgres(terkumpul: number, target: number): number {
  if (target <= 0) return 0;
  // floor, bukan round: 99,9% tidak boleh terbaca 100% pada proposal yang belum funded.
  return Math.min(Math.floor((terkumpul / target) * 100), 100);
}
