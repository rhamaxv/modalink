"use client";

import { useState } from "react";
import { Icon } from "@/components/icons/Icon";
import { ApiError, api } from "@/lib/api";

type TerminationPanelProps = {
  proposalId: string;
  /** Null berarti tidak ada pengajuan penghentian yang sedang berjalan. */
  terminationRequestedAt: string | null;
  /** True hanya untuk lead investor: hanya dia yang berwenang mengajukan. */
  bolehMengajukan: boolean;
  /** True untuk pemilik proposal, yang melihat panel ini sebagai peringatan. */
  akuUmkm: boolean;
  onBerubah: () => void;
};

// Tujuh hari, sama dengan HARI_JENDELA_JAWABAN di
// backend/app/domain/termination.py. Diulang di sini hanya untuk MENGHITUNG
// tanggal yang ditampilkan; yang menentukan tetap server.
const HARI_JENDELA = 7;

function batasJawaban(diajukan: string): string {
  const batas = new Date(diajukan);
  batas.setDate(batas.getDate() + HARI_JENDELA);
  return batas.toLocaleDateString("id-ID", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

// Penghentian proposal yang tahapnya macet.
//
// Panel ini adalah satu-satunya jalan keluar dari jalan buntu yang sebelumnya
// ada di produk ini: proposal yang dananya sudah penuh tapi UMKM-nya berhenti
// melapor menahan sisa dana selamanya, karena lead investor tidak bisa
// menyetujui (belum ada laporan) maupun menolak (menolak hanya sah untuk
// laporan yang masuk).
//
// Dirender untuk KEDUA pihak, dengan isi yang berbeda: lead investor melihat
// tombolnya, UMKM melihat peringatan beserta batas waktunya. Pengajuan yang
// hanya terlihat oleh satu pihak bukan jendela jawaban, melainkan hitung
// mundur yang disembunyikan dari orang yang harus menjawabnya.
export function TerminationPanel({
  proposalId,
  terminationRequestedAt,
  bolehMengajukan,
  akuUmkm,
  onBerubah,
}: TerminationPanelProps) {
  const [mengirim, setMengirim] = useState(false);
  const [galat, setGalat] = useState<string | null>(null);

  async function ajukan() {
    setGalat(null);
    setMengirim(true);
    try {
      await api.post(`/proposals/${proposalId}/terminate`);
      onBerubah();
    } catch (error) {
      // 409 di sini adalah penolakan yang SAH dan menjelaskan sesuatu
      // (tahapnya belum lewat tenggat), jadi pesannya diteruskan apa adanya.
      setGalat(
        error instanceof ApiError
          ? error.message
          : "Gagal mengajukan penghentian. Coba lagi sebentar lagi.",
      );
    } finally {
      setMengirim(false);
    }
  }

  if (terminationRequestedAt !== null) {
    return (
      <div className="flex flex-col gap-space-2 rounded-panel border border-warn bg-panel px-space-4 py-space-4">
        <p className="flex items-center gap-space-2 text-card-title font-semibold text-warn">
          <Icon name="alert" size={20} />
          Penghentian diajukan
        </p>
        <p className="max-w-measure text-body text-ink">
          {akuUmkm
            ? `Kirim laporan tahap berikutnya sebelum ${batasJawaban(terminationRequestedAt)}. Laporan yang masuk membatalkan penghentian ini dan pendanaan berlanjut seperti biasa.`
            : `Menunggu jawaban UMKM sampai ${batasJawaban(terminationRequestedAt)}. Kalau laporan masuk sebelum itu, penghentian batal dan pendanaan berlanjut.`}
        </p>
        <p className="max-w-measure text-label text-muted">
          Lewat batas itu tanpa laporan, sisa dana yang belum cair dikembalikan
          ke para pendana sesuai porsi masing-masing. Dana yang sudah cair tidak
          ditarik kembali.
        </p>
      </div>
    );
  }

  if (!bolehMengajukan) return null;

  return (
    <div className="flex flex-col gap-space-3 rounded-panel border border-line bg-panel px-space-4 py-space-4">
      <p className="text-card-title font-semibold text-ink">Tahap ini tidak berjalan?</p>
      <p className="max-w-measure text-body text-muted">
        Kalau UMKM berhenti mengirim laporan, Anda bisa mengajukan penghentian.
        UMKM diberi tujuh hari untuk tetap melapor; kalau tidak, sisa dana yang
        belum cair kembali ke para pendana sesuai porsi masing-masing.
      </p>
      {/* Bukan tombol beraksen: ini aksi yang menutup pendanaan, bukan aksi
          utama halaman. Aksen di halaman ini milik tombol pendanaan. */}
      <button
        type="button"
        onClick={ajukan}
        disabled={mengirim}
        className="inline-flex min-h-[44px] w-fit items-center gap-space-2 rounded-pill border border-line-strong px-space-4 text-body font-semibold text-ink transition-colors hover:bg-panel-raised disabled:cursor-not-allowed disabled:text-muted"
      >
        <Icon name="alert" size={18} />
        {mengirim ? "Mengajukan..." : "Ajukan penghentian"}
      </button>
      {galat && (
        <p role="alert" className="text-label text-danger">
          {galat}
        </p>
      )}
    </div>
  );
}
