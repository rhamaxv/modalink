import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";

// Landing page minimal dan jujur: fase ini hanya membuktikan aplikasi bisa
// dibangun dan dua jalur masuk/daftar benar-benar menyala. Landing page
// sungguhan, dengan narasi editorial sesuai DESIGN.md, dibangun di fase 11.
export default function Beranda() {
  return (
    <div className="mx-auto flex max-w-baca flex-col gap-ruang-5 px-ruang-3 py-ruang-6">
      <div className="flex items-center justify-between gap-ruang-3">
        <span className="text-[0.8125rem] font-medium text-muted">Modalink</span>
        <ThemeToggle />
      </div>
      <h1 className="text-[clamp(2.5rem,5vw,4rem)] font-semibold leading-tight text-ink">
        Modalink
      </h1>
      <p className="text-base leading-relaxed text-muted">
        Modalink menghubungkan investor dengan UMKM: investor mendanai proposal usaha
        bertahap per milestone, UMKM mengajukan proposal dan melaporkan kemajuannya.
      </p>
      <div className="flex flex-wrap gap-ruang-3">
        <Link
          href="/daftar"
          className="inline-flex min-h-[44px] items-center rounded-kecil bg-accent px-ruang-4 py-ruang-2 text-sm font-semibold text-ink"
        >
          Daftar
        </Link>
        <Link
          href="/masuk"
          className="inline-flex min-h-[44px] items-center rounded-kecil border border-ink px-ruang-4 py-ruang-2 text-sm font-semibold text-ink"
        >
          Masuk
        </Link>
      </div>
    </div>
  );
}
