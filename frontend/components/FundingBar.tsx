import { formatRupiah, persenProgres } from "@/lib/money";
import { Amount } from "@/components/ui/Amount";

type FundingBarProps = {
  terkumpul: number;
  target: number;
  /** undefined saat jumlah pendana belum diketahui (pengunjung tanpa akun:
   * GET .../pledges yang menghitungnya butuh login, sementara terkumpul dan
   * target sendiri datang dari GET /proposals/{id} yang publik). Baris
   * "Didanai oleh N investor" disembunyikan, bukan ditampilkan sebagai 0:
   * nol adalah jumlah yang sah, undefined bukan. */
  pendana?: number;
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
        {/* "Terkumpul" lewat komponen Amount, bukan ukuran yang diketik tangan:
            DESIGN.md menetapkan nominal pendukung di 1,75rem/700/leading 1,10
            (token "amount-sm"), dan setiap nominal rupiah pakai satu komponen
            ini supaya tabular-nums dan ukurannya tidak menyimpang sendiri. */}
        <Amount label="Terkumpul" amount={terkumpul} size="large" />
        <p className="tabular text-body text-muted">dari {formatRupiah(target)}</p>
      </div>

      {/*
        Bilah 24px dengan angka persentase di sampingnya, bukan garis 4px:
        ini adalah satu dari tiga kemunculan --accent yang dijatah DESIGN.md
        untuk layar ini, dan ia jawaban pertanyaan pertama investor begitu
        membuka proposal. Persentasenya dihitung dari angka yang sama yang
        menggambar lebar bilah (persenProgres di lib/money.ts), bukan nilai
        terpisah yang bisa menyimpang darinya.
      */}
      <div className="flex items-center gap-space-3">
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={persen}
          aria-valuetext={`${formatRupiah(terkumpul)} dari ${formatRupiah(target)}`}
          className="h-6 w-full overflow-hidden rounded-sm bg-panel"
        >
          <div className="h-full bg-accent" style={{ width: `${persen}%` }} />
        </div>
        <p className="tabular shrink-0 text-card-title font-display font-bold text-ink">{persen}%</p>
      </div>

      <div className="flex flex-wrap items-baseline justify-between gap-space-2 text-label font-medium text-muted">
        <p className="tabular">sisa {formatRupiah(sisa)}</p>
        {pendana !== undefined && <p className="tabular">Didanai oleh {pendana} investor</p>}
      </div>
    </div>
  );
}
