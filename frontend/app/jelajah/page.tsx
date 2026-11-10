import type { Metadata } from "next";
import Link from "next/link";
import { ProposalList } from "@/components/ProposalCard";

export const metadata: Metadata = {
  title: "Jelajahi proposal - Modalink",
};

// Keputusan di layar ini: proposal mana yang layak dibaca lebih dalam. Tanpa
// "use client" di sini: hanya ProposalList (di ProposalCard.tsx) yang
// menyimpan state fetch dan retry, sesuai konvensi di
// .claude/skills/nextjs-app-conventions/SKILL.md.
//
// RHYTHM 3 (DESIGN.md): setiap elemen section memasang data-pola, dan
// tests/composition.test.tsx menolak dua pola berurutan yang sama DAN
// memeriksa bahwa pola itu benar sesuai struktur yang dirender (bukan
// sekadar label yang dipercaya begitu saja: audit desain menemukan satu
// section pernah berlabel "dua-kolom-asimetris" padahal sebenarnya satu
// kolom). Empat section di bawah: naratif-kiri (satu kolom, tanpa grid),
// daftar-bernomor (<ol> sungguhan, lihat ProposalList), dua-kolom-asimetris
// (grid dua kolom tak setara, 1fr banding 2fr), lebar-penuh-cta (latar
// menembus tepi).
export default function ExplorePage() {
  return (
    <div className="flex flex-col">
      {/*
        Header dan nav Masuk/Daftar sebelumnya ditulis ulang di sini.
        Sekarang disediakan sekali oleh AppHeader di app/layout.tsx (Fase
        11, Task 11), jadi tidak diulang di tiap halaman.
      */}
      <section data-pola="naratif-kiri" className="mx-auto w-full max-w-measure px-space-3 py-space-6">
        <h1 className="text-page font-display text-ink">Jelajahi proposal UMKM</h1>
        <p className="mt-space-3 text-body text-muted">
          Setiap proposal di bawah sudah lolos penilaian AI dan terbuka untuk didanai. Baca
          ceritanya, lalu putuskan mana yang layak Anda dalami lebih jauh.
        </p>
      </section>

      <section data-pola="daftar-bernomor" className="w-full bg-panel px-space-3 py-space-6">
        <div className="mx-auto w-full max-w-[72rem]">
          <h2 className="text-section font-display text-ink">Proposal yang terbuka untuk didanai</h2>
          <div className="mt-space-4">
            <ProposalList />
          </div>
        </div>
      </section>

      <section
        data-pola="dua-kolom-asimetris"
        className="mx-auto w-full max-w-[72rem] px-space-3 py-space-6"
      >
        <div className="grid gap-space-5 md:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
          <h2 className="text-section font-display text-ink">Bagaimana dananya sampai</h2>
          <div className="flex max-w-measure flex-col gap-space-3 text-body text-muted">
            <p>
              UMKM mengajukan proposal lengkap dengan rencana milestone. AI menilainya lebih
              dulu, dan proposal yang lolos ambang skor campaign baru terbuka untuk didanai di
              sini.
            </p>
            <p>
              Satu atau beberapa investor patungan mendanai proposal yang sama. Begitu dana
              terkumpul penuh, pencairannya berjalan bertahap: satu milestone setelah laporannya
              disetujui, lalu lanjut ke milestone berikutnya.
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
