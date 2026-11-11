import type { Metadata } from "next";
import { KycForm } from "@/components/KycForm";

export const metadata: Metadata = {
  title: "Verifikasi identitas - Modalink",
};

// Halaman ini sengaja tanpa "use client": hanya KycForm yang menyimpan state
// dan memanggil api, sama seperti pola app/investor/campaign/baru/page.tsx.
//
// Pernyataan bahwa verifikasinya simulasi TIDAK ditulis di sini, melainkan di
// dalam KycForm. Alasannya bukan selera: pernyataan itu harus tetap terbaca
// di ketiga keadaan muat, termasuk saat status verifikasi gagal dimuat dan
// yang tampil di layar hanyalah tombol coba lagi. Menaruhnya di halaman
// membuatnya terpisah dari komponen yang keadaannya berganti, dan satu-satunya
// kalimat yang tidak boleh hilang adalah justru kalimat itu.
export default function VerifikasiIdentitasPage() {
  return (
    <div className="mx-auto flex max-w-measure flex-col gap-space-5 px-space-3 py-space-6">
      <div>
        <h1 className="font-display text-page text-ink">Verifikasi identitas</h1>
        <p className="mt-space-3 text-body text-muted">
          Pengajuan ini mencatat identitas pemilik akun dan satu rekening tujuan pencairan dana.
        </p>
      </div>
      <KycForm />
    </div>
  );
}
