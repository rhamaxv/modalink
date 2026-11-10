"use client";

import { useId, useRef, useState } from "react";
import { CoverImage } from "@/components/ui/CoverImage";
import { Icon, type IconName } from "@/components/icons/Icon";
import { ApiError, api } from "@/lib/api";
import type { CoverOwner } from "@/lib/cover";

// Batas yang sama dengan server (backend/app/services/cover.py
// MAX_COVER_BYTES). Diulang di sini BUKAN sebagai pengganti pemeriksaan
// server, melainkan supaya pengguna tahu sebelum menunggu unggahan 20 MB
// berjalan sampai selesai lalu ditolak. Server tetap yang menentukan.
const MAKS_BAIT = 1_572_864;
const TIPE_DITERIMA = ["image/jpeg", "image/png", "image/webp"];

type CoverUploadProps = {
  owner: CoverOwner;
  id: string;
  nama: string;
  coverUpdatedAt: string | null;
  sectorIcon?: IconName;
  /** Dipanggil setelah unggah atau hapus berhasil, supaya halaman memuat
   * ulang datanya dan sampul baru benar-benar terlihat. */
  onBerubah: () => void;
};

type Keadaan = { status: "diam" } | { status: "mengirim" } | { status: "galat"; pesan: string };

export function CoverUpload({
  owner,
  id,
  nama,
  coverUpdatedAt,
  sectorIcon,
  onBerubah,
}: CoverUploadProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [keadaan, setKeadaan] = useState<Keadaan>({ status: "diam" });

  async function pilih(berkas: File | undefined) {
    if (!berkas) return;
    // Dicek di sini lebih dulu supaya pesannya menyebut berkas YANG INI,
    // bukan menunggu unggahan selesai untuk mengatakan hal yang sama.
    if (!TIPE_DITERIMA.includes(berkas.type)) {
      setKeadaan({ status: "galat", pesan: "Foto harus berformat JPG, PNG, atau WebP." });
      return;
    }
    if (berkas.size > MAKS_BAIT) {
      setKeadaan({ status: "galat", pesan: "Ukuran foto maksimal 1,5 MB." });
      return;
    }
    setKeadaan({ status: "mengirim" });
    try {
      await api.unggah(`/${owner}/${id}/cover`, berkas);
      setKeadaan({ status: "diam" });
      onBerubah();
    } catch (error) {
      setKeadaan({
        status: "galat",
        pesan:
          error instanceof ApiError
            ? error.message
            : "Gagal mengunggah foto. Coba lagi sebentar lagi.",
      });
    } finally {
      // Dikosongkan supaya memilih berkas yang SAMA dua kali berturut-turut
      // tetap memicu onChange: tanpa ini, mencoba ulang setelah gagal tidak
      // melakukan apa pun dan terlihat seperti tombol yang rusak.
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function hapus() {
    setKeadaan({ status: "mengirim" });
    try {
      await api.del(`/${owner}/${id}/cover`);
      setKeadaan({ status: "diam" });
      onBerubah();
    } catch (error) {
      setKeadaan({
        status: "galat",
        pesan:
          error instanceof ApiError
            ? error.message
            : "Gagal menghapus foto. Coba lagi sebentar lagi.",
      });
    }
  }

  const mengirim = keadaan.status === "mengirim";

  return (
    <div className="flex flex-col gap-space-3">
      <div className="flex flex-wrap items-center gap-space-4">
        {/* Dibungkus pembatas lebar: kelas "card" memakai w-full, dan di
            dalam panel selebar halaman itu menghasilkan pratinjau setinggi
            750px, jauh lebih besar daripada sampul yang sesungguhnya tampil
            di mana pun. */}
        <span className="w-full max-w-[18rem]">
          <CoverImage
            owner={owner}
            id={id}
            coverUpdatedAt={coverUpdatedAt}
            nama={nama}
            sectorIcon={sectorIcon}
            ukuran="card"
          />
        </span>
        <div className="flex max-w-measure flex-col gap-space-2">
          <p className="text-body text-muted">
            {coverUpdatedAt === null
              ? "Belum ada foto sampul. Tanpa foto, usaha Anda tetap tampil memakai lambang sektornya."
              : "Foto sampul sudah terpasang. Mengunggah foto baru akan menggantikannya."}
          </p>
          <div className="flex flex-wrap items-center gap-space-2">
            {/*
              Input berkas disembunyikan secara visual, bukan dibuang: label
              di bawahnya yang terlihat, dan label itu memang MENGAKTIFKAN
              input ini saat diklik maupun saat ditekan dari keyboard. Kelas
              peer-focus-visible memindahkan cincin fokus ke label, karena
              yang terlihat pengguna adalah label, bukan input yang
              disembunyikan.
            */}
            <input
              ref={inputRef}
              id={inputId}
              type="file"
              accept={TIPE_DITERIMA.join(",")}
              disabled={mengirim}
              onChange={(event) => pilih(event.target.files?.[0])}
              className="peer sr-only"
            />
            <label
              htmlFor={inputId}
              className="inline-flex min-h-[44px] cursor-pointer items-center gap-space-2 rounded-pill border border-line-strong px-space-4 text-body font-semibold text-ink transition-colors hover:bg-panel-raised peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-ink peer-disabled:cursor-not-allowed peer-disabled:text-muted"
            >
              <Icon name="upload" size={18} />
              {coverUpdatedAt === null ? "Unggah foto" : "Ganti foto"}
            </label>
            {coverUpdatedAt !== null && (
              <button
                type="button"
                onClick={hapus}
                disabled={mengirim}
                className="inline-flex min-h-[44px] items-center rounded-pill px-space-3 text-body font-medium text-muted underline underline-offset-2 transition-colors hover:text-ink disabled:cursor-not-allowed"
              >
                Hapus foto
              </button>
            )}
          </div>
          <p className="text-label text-muted">JPG, PNG, atau WebP. Maksimal 1,5 MB.</p>
        </div>
      </div>
      {mengirim && (
        <p role="status" aria-live="polite" className="text-label text-muted">
          Mengunggah foto...
        </p>
      )}
      {keadaan.status === "galat" && (
        <p role="alert" className="text-label text-danger">
          {keadaan.pesan}
        </p>
      )}
    </div>
  );
}
