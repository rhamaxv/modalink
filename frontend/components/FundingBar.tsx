import { formatRupiah, persenProgres } from "@/lib/money";

type FundingBarProps = {
  terkumpul: number;
  target: number;
  pendana: number;
};

// Bilah funding: salah satu dari tepat tiga tempat --accent dipakai di layar
// ini (DESIGN.md), karena bilah ini sendiri adalah jawaban atas pertanyaan
// pertama investor begitu membuka proposal: berapa yang sudah terkumpul.
// Ketiga tempat lain (tombol pledge, penanda milestone aktif) tidak boleh
// menambah kemunculannya; kalau aksen dipakai lagi di luar tiga itu, dia
// berhenti berarti sebagai aksen (DESIGN.md).
export function FundingBar({ terkumpul, target, pendana }: FundingBarProps) {
  const persen = persenProgres(terkumpul, target);
  const sisa = Math.max(target - terkumpul, 0);

  return (
    <div className="flex flex-col gap-space-3">
      <div className="flex flex-wrap items-baseline justify-between gap-space-2">
        <div className="text-left">
          <p className="text-[0.8125rem] font-medium text-muted">Terkumpul</p>
          <p className="tabular text-[1.75rem] font-semibold text-ink">{formatRupiah(terkumpul)}</p>
        </div>
        <p className="tabular text-base leading-[1.6] text-muted">dari {formatRupiah(target)}</p>
      </div>

      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={persen}
        aria-valuetext={`${formatRupiah(terkumpul)} dari ${formatRupiah(target)}`}
        className="h-3 w-full overflow-hidden rounded-sm bg-surface"
      >
        <div className="h-full bg-accent" style={{ width: `${persen}%` }} />
      </div>

      <div className="flex flex-wrap items-baseline justify-between gap-space-2 text-[0.8125rem] font-medium text-muted">
        <p className="tabular">sisa {formatRupiah(sisa)}</p>
        <p className="tabular">Didanai oleh {pendana} investor</p>
      </div>
    </div>
  );
}
