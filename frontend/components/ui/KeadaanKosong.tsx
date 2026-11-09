type AksiKeadaanKosong = {
  label: string;
  onClick: () => void;
};

type KeadaanKosongProps = {
  /** Kalimat yang menjelaskan kenapa tampilan ini kosong, bukan label hampa. */
  sebab: string;
  /** Satu aksi yang mengisi kekosongan ini. Opsional: tidak semua layar kosong punya aksi lanjutan. */
  aksi?: AksiKeadaanKosong;
};

// R-27: keadaan kosong adalah bagian dari desain, bukan "Tidak ada data". Ia
// wajib menyebut sebab kekosongan dan satu aksi yang membuatnya terisi.
export function KeadaanKosong({ sebab, aksi }: KeadaanKosongProps) {
  return (
    <div className="flex flex-col items-start gap-ruang-3 rounded-kartu border border-line bg-surface px-ruang-4 py-ruang-5 text-left">
      <p className="max-w-baca text-sm text-muted">{sebab}</p>
      {aksi && (
        <button
          type="button"
          onClick={aksi.onClick}
          className="min-h-[44px] rounded-kecil bg-accent px-ruang-3 py-ruang-2 text-sm font-semibold text-ink"
        >
          {aksi.label}
        </button>
      )}
    </div>
  );
}
