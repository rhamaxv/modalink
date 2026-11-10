import Link from "next/link";

const LANGKAH = [
  {
    nomor: "01",
    judul: "UMKM mengajukan proposal",
    teks: "Lengkap dengan rencana pemakaian dana dan tahap milestone, bukan sekadar angka yang diminta.",
  },
  {
    nomor: "02",
    judul: "AI menilai lebih dulu",
    teks: "Kelengkapan data dan risikonya dinilai dalam hitungan menit, bukan menunggu giliran manual.",
  },
  {
    nomor: "03",
    judul: "Investor patungan mendanai",
    teks: "Satu investor atau beberapa sekaligus bisa ikut mendanai proposal yang sudah lolos penilaian.",
  },
  {
    nomor: "04",
    judul: "Dana cair bertahap",
    teks: "Satu milestone cair setelah laporannya disetujui lead investor, baru lanjut ke milestone berikutnya.",
  },
];

// Landing page sungguhan (Fase 11, Task 11). DESIGN.md memberi halaman ini
// dial ENERGY 2: karakter lebih kuat daripada halaman dashboard yang tenang,
// dicapai lewat ukuran (nomor langkah besar di section 2) dan komposisi
// (empat pola berbeda berurutan), bukan lewat dekorasi tambahan.
//
// H1 sengaja tidak berisi "Modalink": nama produk sudah ada di header
// (AppHeader, dirender app/layout.tsx), H1 menyampaikan apa yang produk ini
// kerjakan.
//
// Tidak ada statistik, testimoni, atau bilah logo di halaman ini: produk
// ini belum punya satu pun data nyata untuk itu (R-17, R-18, R-36).
export default function Beranda() {
  return (
    <div className="flex flex-col">
      <section data-pola="naratif-kiri" className="mx-auto w-full max-w-measure px-space-3 py-space-7">
        <h1 className="text-[clamp(2.5rem,5vw,4rem)] font-semibold leading-tight text-ink">
          Usaha lokal didanai bersama, dicairkan selangkah demi selangkah.
        </h1>
        <p className="mt-space-4 text-body text-muted">
          Modalink menghubungkan investor dengan UMKM. Proposal dinilai AI lebih dulu, investor
          patungan mendanainya, dan dananya cair bertahap setelah tiap milestone disetujui.
        </p>
        <div className="mt-space-4 flex flex-wrap gap-space-4">
          <Link href="/jelajah" className="text-base font-medium text-ink underline">
            Jelajahi proposal yang terbuka
          </Link>
          <Link href="/daftar" className="text-base font-medium text-ink underline">
            Daftar
          </Link>
        </div>
      </section>

      <section data-pola="daftar-bernomor" className="w-full border-t border-line bg-panel px-space-3 py-space-7">
        <div className="mx-auto w-full max-w-[72rem]">
          <h2 className="text-[1.75rem] font-semibold text-ink">Bagaimana dananya bergerak</h2>
          <ol className="mt-space-5 flex flex-col gap-space-5">
            {LANGKAH.map((langkah) => (
              <li key={langkah.nomor} className="flex gap-space-4 border-t border-line pt-space-4 first:border-t-0 first:pt-0">
                <span aria-hidden="true" className="tabular shrink-0 text-[2rem] font-semibold leading-none text-muted">
                  {langkah.nomor}
                </span>
                <div className="flex max-w-measure flex-col gap-space-1">
                  <p className="text-[1.125rem] font-semibold text-ink">{langkah.judul}</p>
                  <p className="text-body text-muted">{langkah.teks}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section data-pola="dua-kolom-setara" className="mx-auto w-full max-w-[72rem] px-space-3 py-space-7">
        <div className="grid gap-space-6 md:grid-cols-2">
          <div className="flex flex-col gap-space-2">
            <h2 className="text-[1.75rem] font-semibold text-ink">Untuk investor</h2>
            <p className="max-w-measure text-body text-muted">
              Baca brief AI dan bukan hanya skornya, ikut patungan mendanai proposal yang Anda
              percayai, dan setujui pencairan tiap milestone berdasarkan laporan kemajuan nyata.
            </p>
            <Link href="/jelajah" className="mt-space-2 text-base font-medium text-ink underline">
              Lihat proposal yang terbuka untuk didanai
            </Link>
          </div>
          <div className="flex flex-col gap-space-2 border-t border-line pt-space-5 md:border-t-0 md:border-l md:pl-space-6 md:pt-0">
            <h2 className="text-[1.75rem] font-semibold text-ink">Untuk UMKM</h2>
            <p className="max-w-measure text-body text-muted">
              Ajukan proposal lengkap dengan rencana milestone, lalu laporkan kemajuan usaha
              Anda setiap tahap selesai untuk mencairkan dana ke tahap berikutnya.
            </p>
            <Link href="/daftar" className="mt-space-2 text-base font-medium text-ink underline">
              Daftar dan ajukan proposal
            </Link>
          </div>
        </div>
      </section>

      <section data-pola="lebar-penuh-cta" className="w-full border-t border-line bg-panel px-space-3 py-space-7">
        <div className="mx-auto flex max-w-measure flex-col items-start gap-space-3">
          <h2 className="text-[1.75rem] font-semibold text-ink">Siap mulai?</h2>
          <p className="text-body text-muted">
            Daftar sebagai investor untuk mulai mendanai, atau sebagai UMKM untuk mengajukan
            proposal usaha Anda.
          </p>
          <Link
            href="/daftar"
            className="inline-flex min-h-[44px] items-center rounded-sm bg-accent px-space-4 py-space-2 text-base font-semibold text-on-accent"
          >
            Daftar sekarang
          </Link>
        </div>
      </section>
    </div>
  );
}
