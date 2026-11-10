import type { Metadata } from "next";
import Link from "next/link";
import { ExploreTabs } from "@/components/ExploreTabs";

export const metadata: Metadata = {
  title: "Jelajahi - Modalink",
};

// Keputusan di layar ini: proposal mana yang layak dibaca lebih dalam, ATAU
// campaign mana yang layak diajukan proposal. Dua niat, satu layar: investor
// datang mencari proposal untuk didanai, UMKM datang mencari campaign untuk
// diajukan. ExploreTabs (client) memilih tab default lewat GET /auth/me (umkm
// -> campaign, selain itu -> proposal) tapi TIDAK PERNAH menyembunyikan tab
// yang lain, supaya pengunjung anonim, termasuk juri lomba, melihat kedua
// sisi pasar ada tanpa harus masuk dulu. Lihat laporan untuk argumen penuh
// kenapa tab dipilih dibanding dua rute terpisah.
//
// Tanpa "use client" di sini: hanya ExploreTabs dan isinya (ProposalList,
// CampaignBrowseList) yang menyimpan state fetch dan retry, sesuai konvensi
// di .claude/skills/nextjs-app-conventions/SKILL.md.
//
// RHYTHM 3 (DESIGN.md): setiap elemen section memasang data-pola, dan
// tests/composition.test.tsx menolak dua pola berurutan yang sama DAN
// memeriksa bahwa pola itu benar sesuai struktur yang dirender. Empat
// section di bawah: naratif-kiri (satu kolom, tanpa grid), daftar-bernomor
// (<ol> sungguhan di tab yang aktif, lihat ProposalList/CampaignBrowseList),
// dua-kolom-asimetris (grid dua kolom tak setara, 1fr banding 2fr),
// lebar-penuh-cta (latar menembus tepi).
export default function ExplorePage() {
  return (
    <div className="flex flex-col">
      {/*
        Header dan nav Masuk/Daftar sebelumnya ditulis ulang di sini.
        Sekarang disediakan sekali oleh AppHeader di app/layout.tsx (Fase
        11, Task 11), jadi tidak diulang di tiap halaman.
      */}
      <section data-pola="naratif-kiri" className="mx-auto w-full max-w-measure px-space-3 py-space-6">
        <h1 className="text-page font-display text-ink">Jelajahi peluang di Modalink</h1>
        <p className="mt-space-3 text-body text-muted">
          Dua pintu masuk ke pasar yang sama. Baca proposal UMKM yang sudah lolos penilaian AI
          dan terbuka untuk didanai, atau lihat{" "}
          <span className="rounded-sm bg-accent-2 px-1 text-on-accent">campaign yang terbuka</span>{" "}
          untuk menerima proposal baru, lalu putuskan langkah Anda selanjutnya.
        </p>
      </section>

      <section data-pola="daftar-bernomor" className="w-full bg-panel px-space-3 py-space-6">
        <div className="mx-auto w-full max-w-[72rem]">
          <p className="inline-block rounded-sm bg-accent-2 px-space-2 py-space-1 text-label font-medium uppercase tracking-wide text-on-accent">
            Jelajahi
          </p>
          <h2 className="mt-space-2 text-section font-display text-ink">
            Proposal dan campaign yang terbuka
          </h2>
          <div className="mt-space-4">
            <ExploreTabs />
          </div>
        </div>
      </section>

      <section
        data-pola="dua-kolom-asimetris"
        className="mx-auto w-full max-w-[72rem] px-space-3 py-space-6"
      >
        <div className="grid gap-space-5 md:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
          <div>
            <p className="inline-block rounded-sm bg-accent-2 px-space-2 py-space-1 text-label font-medium uppercase tracking-wide text-on-accent">
              Alur dana
            </p>
            <h2 className="mt-space-2 text-section font-display text-ink">Bagaimana dananya sampai</h2>
          </div>
          <div className="flex max-w-measure flex-col gap-space-3 text-body text-muted">
            <p>
              Investor membuat campaign dengan dua tenggat: tenggat pengajuan proposal, dan tenggat
              pendanaan setelahnya. UMKM mengajukan proposal lengkap dengan rencana milestone sebelum
              tenggat pertama lewat. AI menilainya lebih dulu, dan proposal yang lolos ambang skor
              campaign baru terbuka untuk didanai di tab Proposal.
            </p>
            <p>
              Satu atau beberapa investor patungan mendanai proposal yang sama sebelum tenggat kedua
              lewat. Begitu dana terkumpul penuh, pencairannya berjalan bertahap: satu milestone
              setelah laporannya disetujui, lalu lanjut ke milestone berikutnya.
            </p>
          </div>
        </div>
      </section>

      <section
        data-pola="lebar-penuh-cta"
        className="w-full border-t border-line bg-panel px-space-3 py-space-6"
      >
        <div className="mx-auto flex max-w-measure flex-col items-start gap-space-3">
          <h2 className="text-section font-display text-ink">
            Punya usaha, atau dana untuk disalurkan?
          </h2>
          <p className="text-body text-muted">
            Daftar sebagai UMKM untuk mengajukan proposal, atau sebagai investor untuk mulai
            mendanai usaha lokal.
          </p>
          <Link
            href="/daftar"
            className="inline-flex min-h-[44px] items-center rounded-pill bg-accent px-space-5 py-space-2 text-body font-semibold text-on-accent"
          >
            Daftar sekarang
          </Link>
        </div>
      </section>
    </div>
  );
}
