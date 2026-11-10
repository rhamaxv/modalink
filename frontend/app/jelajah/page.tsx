import type { Metadata } from "next";
import { ExploreTabs } from "@/components/ExploreTabs";
import { ButtonLink } from "@/components/ui";

export const metadata: Metadata = {
  title: "Jelajahi - Modalink",
};

// Halaman INDEKS, bukan halaman pendaratan.
//
// Versi sebelumnya punya hero setinggi 62vh, dua kartu pintu masuk, esai dua
// paragraf tentang alur dana, dan ajakan mendaftar yang panjang. Semuanya
// berdiri di depan satu-satunya alasan orang membuka rute ini: melihat apa
// yang sedang terbuka. Diukur di browser, hero itu memakan 63 persen layar
// pertama, daftarnya mulai di bawah lipatan, dan tidak ada satu pun filter,
// pengurutan, atau kontrol halaman. Dengan lima puluh proposal, halaman itu
// diam-diam menampilkan dua puluh pertama dan tidak memberi jalan ke sisanya.
//
// Penjelasan alur dana tidak hilang, ia memang sudah ada di halaman landing
// (app/page.tsx, daftar bernomor "Bagaimana dananya bergerak"). Mengulangnya
// di sini berarti menunda daftar demi sesuatu yang sudah dibaca pengunjung
// satu klik sebelumnya.
//
// Tanpa "use client" di sini: hanya ExploreTabs dan isinya (ProposalList,
// CampaignBrowseList) yang menyimpan state fetch, filter, dan halaman,
// sesuai konvensi di .claude/skills/nextjs-app-conventions/SKILL.md.
//
// RHYTHM 3 (DESIGN.md): setiap elemen section memasang data-pola, dan
// tests/composition.test.tsx menolak dua pola berurutan yang sama DAN
// memeriksa bahwa pola itu benar sesuai struktur yang dirender. Tiga section
// di bawah: judul-dan-kendali (judul ringkas satu kolom), daftar-bernomor
// (<ol> sungguhan di tab yang aktif), lebar-penuh-cta (latar menembus tepi,
// satu aksi).
export default function ExplorePage() {
  return (
    <div className="flex flex-col">
      {/*
        py-space-5, tanpa min-h: judul halaman indeks hanya perlu memberi
        tahu di mana Anda berada dan apa yang akan Anda lihat. Tingginya
        dibatasi supaya baris pertama daftar sudah terlihat di layar pertama,
        yang persis kebalikan dari versi sebelumnya.
      */}
      <section
        data-pola="judul-dan-kendali"
        className="mx-auto w-full max-w-[72rem] px-space-3 pb-space-4 pt-space-5"
      >
        <h1 className="max-w-measure text-section font-display text-ink">
          Yang sedang terbuka
        </h1>
        <p className="mt-space-2 max-w-measure text-body text-muted">
          Proposal UMKM yang sudah lolos penilaian AI dan terbuka untuk didanai, serta campaign
          investor yang sedang menerima proposal baru. Saring per sektor, urutkan, dan telusuri
          halamannya.
        </p>
      </section>

      <section
        data-pola="daftar-bernomor"
        className="mx-auto w-full max-w-[72rem] px-space-3 pb-space-6"
      >
        <ExploreTabs />
      </section>

      {/*
        Satu baris penutup, bukan section ajakan setinggi layar. Ia memegang
        satu-satunya aksi berlatar aksen di halaman ini (DESIGN.md menjatah
        tepat satu per layar), dan ia diletakkan SETELAH daftar karena pada
        halaman indeks, mendaftar adalah yang Anda lakukan sesudah melihat
        ada sesuatu yang layak, bukan sebelumnya.
      */}
      <section
        data-pola="lebar-penuh-cta"
        className="w-full border-t border-line bg-panel px-space-3 py-space-5"
      >
        <div className="mx-auto flex w-full max-w-[72rem] flex-wrap items-center justify-between gap-space-3">
          <p className="max-w-measure text-body text-muted">
            Mendanai proposal atau mengajukan proposal usaha Anda sendiri sama-sama butuh akun.
          </p>
          <ButtonLink href="/daftar">Daftar</ButtonLink>
        </div>
      </section>
    </div>
  );
}
