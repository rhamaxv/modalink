import Link from "next/link";
import { ButtonLink } from "@/components/ui";
import { FeaturedProposalHighlight } from "@/components/ProposalCard";

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

// Kelas tautan teks yang dipakai berulang di halaman ini. Bukan tombol
// (bg-accent dijatah tiga kemunculan per layar oleh DESIGN.md dan sudah
// habis untuk CTA di section terakhir), tapi tetap butuh kotak klik 44px:
// audit browser menemukan tautan semacam ini hanya setinggi baris tulisannya
// sendiri di seluruh rute (lihat juga NavRole.NAV_LINK_CLASS).
const TAUTAN_TEKS =
  "inline-flex min-h-[44px] items-center text-body font-medium text-ink underline underline-offset-2";

// Landing page sungguhan (Fase 11, Task 11; diarahkan ulang ke DESIGN.md yang
// ditulis ulang 10 November 2026). ENERGY 4 di DESIGN.md dicapai lewat
// tipografi tegas (text-page/text-section: leading 1.10, bobot 700) dan
// komposisi asimetris, bukan lewat dekorasi tambahan.
//
// H1 sengaja tidak berisi "Modalink": nama produk sudah ada di header
// (AppHeader, dirender app/layout.tsx), H1 menyampaikan apa yang produk ini
// kerjakan.
//
// Tidak ada statistik, testimoni, atau bilah logo di halaman ini: produk
// ini belum punya satu pun data nyata untuk itu (R-17, R-18, R-36). Ruang
// yang di referensi (the5ers.com) diisi 341 foto manusia, di sini diisi satu
// nominal rupiah nyata (FeaturedProposalHighlight): DESIGN.md menjawab
// "apa yang mengisi ruang tempat foto bekerja" dengan uang, bukan ilustrasi
// yang dikarang.
//
// RHYTHM 3 (DESIGN.md): setiap elemen section memasang data-pola, dan
// tests/composition.test.tsx menolak dua pola berurutan yang sama, lalu
// memeriksa bahwa pola itu benar sesuai struktur yang dirender, bukan
// sekadar label. Empat section di bawah: kiri-sorotan-nominal (asimetris,
// dua kolom tak setara), daftar-bernomor (daftar bernomor sungguhan),
// dua-kolom-setara (dua kolom selebar sama), lebar-penuh-cta (latar
// menembus tepi, teks terbatas measure).
export default function Beranda() {
  return (
    <div className="flex flex-col">
      {/*
        min-h: hero sempat setinggi 98px di viewport 722px, yaitu 14 persen
        layar, dan itu alasan utama halaman terasa terlalu sederhana.
        Referensi yang ditunjuk pemilik project mengisi hampir seluruh layar
        pertama.
      */}
      <section
        data-pola="kiri-sorotan-nominal"
        className="mx-auto flex w-full max-w-[72rem] items-center px-space-3 py-space-7 md:min-h-[78vh]"
      >
        <div className="grid w-full gap-space-6 md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] md:items-center">
          <div className="flex max-w-measure flex-col gap-space-4">
            <h1 className="text-page font-display text-ink">
              Usaha lokal didanai bersama, dicairkan selangkah demi selangkah.
            </h1>
            <p className="text-body text-muted">
              Modalink menghubungkan investor dengan UMKM. Proposal dinilai AI lebih dulu,
              investor patungan mendanainya, dan dananya{" "}
              {/*
                bg-accent-2 + text-on-accent, bukan accent-2 sebagai warna teks polos:
                accent-2 tidak pernah berbalik warna per tema (DESIGN.md),
                tapi --paper dan --panel berbalik dari hampir hitam ke hampir
                putih. Dipakai sebagai teks biasa di atas latar yang ikut
                berbalik, accent-2 mengukur 1,90:1 di tema terang (gagal
                jauh di bawah ambang 4,5:1), celah yang tidak ada di tabel
                kontras DESIGN.md karena baris itu cuma mengukur accent-2
                sebagai teks di atas --paper GELAP. Sebagai latar highlight
                kecil berpasangan dengan --on-accent, kombinasinya sama
                persis dengan yang sudah diukur DESIGN.md lolos 9,59:1, dan
                tidak berubah saat tema berganti karena ketiga tokennya sama
                sekali tidak berbalik.
              */}
              <span className="rounded-sm bg-accent-2 px-1 text-on-accent">cair bertahap</span>{" "}
              setelah tiap milestone disetujui.
            </p>
            {/*
              Tombol berlatar aksen, bukan tautan teks. Versi sebelumnya
              menjadikan keduanya tautan dengan alasan anggaran tiga aksen
              sudah habis untuk CTA di section terakhir. Pembacaannya sah,
              pertukarannya terbalik: aksi utama di hero adalah momen aksen
              paling penting di halaman, dan menghabiskannya di bawah lipatan
              membuat layar pertama tidak punya satu pun warna. CTA penutup
              yang turun jadi sekunder.
            */}
            <div className="flex flex-wrap gap-space-3">
              <ButtonLink href="/jelajah">Jelajahi proposal yang terbuka</ButtonLink>
              <ButtonLink href="/daftar" varian="secondary">
                Daftar
              </ButtonLink>
            </div>
          </div>
          <FeaturedProposalHighlight />
        </div>
      </section>

      <section
        data-pola="daftar-bernomor"
        className="w-full border-t border-line bg-panel px-space-3 py-space-7"
      >
        <div className="mx-auto w-full max-w-[72rem]">
          <p className="inline-block rounded-sm bg-accent-2 px-space-2 py-space-1 text-label font-medium uppercase tracking-wide text-on-accent">
            Alur dana
          </p>
          <h2 className="mt-space-2 text-section font-display text-ink">
            Bagaimana dananya bergerak
          </h2>
          {/*
            Daftar ini adalah satu-satunya tempat di produk yang menunjukkan
            keempat tahap alur dana sekaligus, jadi ia digambar sebagai jalur
            bertahap (bulatan bernomor beraksen-2 dihubungkan garis vertikal),
            bukan empat baris datar: geometri yang sama, dalam bentuk lebih
            kecil, yang dipakai MilestoneTimeline untuk tahap milestone
            sungguhan. "Real geometry... the product's own data given form"
            (brief), bukan dekorasi lepas: garis dan bulatan ini memang
            mengikuti urutan nyata proses, bukan ditambahkan untuk estetika.
          */}
          <ol className="relative mt-space-6 flex flex-col gap-space-6 border-l-2 border-line pl-space-5 md:pl-space-6">
            {LANGKAH.map((langkah) => (
              <li key={langkah.nomor} className="relative flex list-none flex-col gap-space-1">
                <span
                  aria-hidden="true"
                  className="tabular absolute -left-[2.85rem] top-0 flex h-9 w-9 items-center justify-center rounded-full bg-accent-2 text-label font-display font-bold text-on-accent md:-left-[3.35rem]"
                >
                  {langkah.nomor}
                </span>
                <div className="flex max-w-measure flex-col gap-space-1">
                  <p className="text-card-title font-semibold text-ink">{langkah.judul}</p>
                  <p className="text-body text-muted">{langkah.teks}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section
        data-pola="dua-kolom-setara"
        className="mx-auto w-full max-w-[72rem] px-space-3 py-space-7"
      >
        <p className="inline-block rounded-sm bg-accent-2 px-space-2 py-space-1 text-label font-medium uppercase tracking-wide text-on-accent">
          Untuk siapa
        </p>
        {/*
          Dua kolom selebar sama (grid-cols-2, pagar RHYTHM mengunci ini),
          tapi bukan dua kotak kembar: kolom investor dibungkus panel
          terangkat (rounded-feature, salah satu dari satu-atau-dua blok
          sorotan yang DESIGN.md izinkan per halaman) sementara kolom UMKM
          tetap teks polos. "Varied cell sizes... so a list is not N
          identical rectangles" (brief), diterapkan lewat bobot visual, bukan
          lewat lebar kolom yang pagar pagarnya sendiri menuntut setara.
        */}
        <div className="mt-space-3 grid gap-space-6 md:grid-cols-2">
          <div className="flex flex-col gap-space-3 rounded-feature border border-line bg-panel-raised px-space-5 py-space-6">
            <p className="inline-block w-fit rounded-sm bg-accent-2 px-space-2 py-space-1 text-label font-medium uppercase tracking-wide text-on-accent">
              Investor
            </p>
            <h2 className="text-section font-display text-ink">Mendanai patungan</h2>
            <p className="max-w-measure text-body text-muted">
              Baca brief AI dan bukan hanya skornya, ikut patungan mendanai proposal yang Anda
              percayai, dan setujui pencairan tiap milestone berdasarkan laporan kemajuan nyata.
            </p>
            <Link href="/jelajah" className={`mt-space-2 ${TAUTAN_TEKS}`}>
              Lihat proposal yang terbuka untuk didanai
            </Link>
          </div>
          <div className="flex flex-col gap-space-3 border-t border-line pt-space-5 md:border-t-0 md:pl-space-2 md:pt-space-6">
            <p className="inline-block w-fit rounded-sm bg-accent-2 px-space-2 py-space-1 text-label font-medium uppercase tracking-wide text-on-accent">
              UMKM
            </p>
            <h2 className="text-section font-display text-ink">Mengajukan proposal</h2>
            <p className="max-w-measure text-body text-muted">
              Ajukan proposal lengkap dengan rencana milestone, lalu laporkan kemajuan usaha
              Anda setiap tahap selesai untuk mencairkan dana ke tahap berikutnya.
            </p>
            <Link href="/daftar" className={`mt-space-2 ${TAUTAN_TEKS}`}>
              Daftar dan ajukan proposal
            </Link>
          </div>
        </div>
      </section>

      {/*
        Satu-satunya permukaan berlatar --accent penuh di halaman ini: sebuah
        SURFACE, bukan AKSI (brief ini sendiri yang membedakannya, dan
        anggaran "satu aksi berlatar aksen" DESIGN.md menghitung aksi, bukan
        latar). Tautannya di bawah sengaja memakai text-on-accent bergaris
        bawah, bukan ButtonLink varian apa pun: varian "secondary" memakai
        border-line-strong dan text-ink, dan text-ink BERBALIK ikut tema
        sementara latar --accent di sini TIDAK, jadi di tema gelap teks itu
        akan jadi putih di atas lime (1,14:1, dilarang DESIGN.md). Hanya
        warna on-accent (tidak pernah berbalik) yang aman dipasangkan dengan
        latar ini di kedua tema.
      */}
      <section
        data-pola="lebar-penuh-cta"
        className="w-full border-t border-line bg-accent px-space-3 py-space-7"
      >
        <div className="mx-auto flex max-w-measure flex-col items-start gap-space-3">
          <h2 className="text-section font-display text-on-accent">Siap mulai?</h2>
          <p className="text-body text-on-accent">
            Daftar sebagai investor untuk mulai mendanai, atau sebagai UMKM untuk mengajukan
            proposal usaha Anda.
          </p>
          <Link
            href="/daftar"
            className="mt-space-1 inline-flex min-h-[44px] items-center text-body font-semibold text-on-accent underline underline-offset-2"
          >
            Daftar sekarang
          </Link>
        </div>
      </section>
    </div>
  );
}
