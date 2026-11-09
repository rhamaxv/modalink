import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";

// Landing page minimal dan jujur: fase ini hanya membuktikan aplikasi bisa
// dibangun dan dua jalur masuk/daftar benar-benar menyala. Landing page
// sungguhan, dengan narasi editorial sesuai DESIGN.md, dibangun di fase 11.
export default function Beranda() {
  return (
    <div className="mx-auto flex max-w-measure flex-col gap-space-5 px-space-3 py-space-6">
      <div className="flex items-center justify-between gap-space-3">
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
      <div className="flex flex-wrap gap-space-3">
        <Link
          href="/daftar"
          className="inline-flex min-h-[44px] items-center rounded-sm bg-accent px-space-4 py-space-2 text-base leading-[1.6] font-semibold text-ink"
        >
          Daftar
        </Link>
        <Link
          href="/masuk"
          className="inline-flex min-h-[44px] items-center rounded-sm border border-ink px-space-4 py-space-2 text-base leading-[1.6] font-semibold text-ink"
        >
          Masuk
        </Link>
      </div>
    </div>
  );
}
