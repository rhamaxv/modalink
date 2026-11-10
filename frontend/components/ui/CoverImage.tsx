import { Icon, type IconName } from "@/components/icons/Icon";
import { coverUrl, type CoverOwner } from "@/lib/cover";

type CoverImageProps = {
  owner: CoverOwner;
  id: string;
  /** Null berarti pemiliknya belum mengunggah foto. */
  coverUpdatedAt: string | null | undefined;
  /** Nama usaha atau judul campaign, dipakai menyusun teks alternatif. */
  nama: string;
  /** Ikon sektor untuk sampul cadangan. Tanpa ini dipakai ikon gambar biasa. */
  sectorIcon?: IconName;
  /** thumb: kotak kecil di baris daftar. banner: pita lebar di halaman detail. */
  ukuran?: "thumb" | "card" | "banner";
};

const KELAS: Record<NonNullable<CoverImageProps["ukuran"]>, string> = {
  thumb: "h-14 w-14 rounded-sm",
  card: "aspect-[3/2] w-full rounded-card",
    // max-h selain rasio: pada layar 1440px, rasio 3:1 saja menghasilkan
  // banner setinggi 480px, dan itu mendorong nominal serta progres pendanaan
  // mendekati lipatan. Rasio mengatur bentuknya di layar sempit, max-h
  // menahan tingginya di layar lebar.
  banner: "aspect-[3/1] max-h-[18rem] w-full rounded-panel",
};

const UKURAN_IKON: Record<NonNullable<CoverImageProps["ukuran"]>, number> = {
  thumb: 22,
  card: 40,
  banner: 56,
};

// Foto sampul, beserta keadaan "belum ada foto" yang DIRANCANG, bukan gambar
// rusak.
//
// Ini bagian yang paling mudah dilewatkan ketika fitur unggah ditambahkan:
// sebagian besar usaha tidak akan pernah mengunggah apa pun, jadi keadaan
// kosong adalah keadaan yang PALING SERING terlihat, bukan kasus pinggiran.
// Sampul cadangan memakai ikon sektornya sendiri, sehingga baris tanpa foto
// tetap punya bentuk dan tetap bisa dibedakan satu sama lain.
export function CoverImage({
  owner,
  id,
  coverUpdatedAt,
  nama,
  sectorIcon,
  ukuran = "card",
}: CoverImageProps) {
  const src = coverUrl(owner, id, coverUpdatedAt);
  const dasar = `${KELAS[ukuran]} shrink-0 overflow-hidden border border-line`;

  if (src === null) {
    return (
      // aria-hidden: sampul cadangan tidak membawa informasi apa pun yang
      // belum ada sebagai teks di sebelahnya. Mengumumkan "tidak ada foto"
      // ke pembaca layar hanya menambah kebisingan.
      <span
        aria-hidden="true"
        className={`${dasar} flex items-center justify-center bg-panel-raised text-muted`}
      >
        <Icon name={sectorIcon ?? "image"} size={UKURAN_IKON[ukuran]} />
      </span>
    );
  }

  return (
    // <img> biasa, bukan next/image: sumbernya endpoint API yang membalas
    // byte dari database, bukan berkas statis yang bisa dioptimalkan Next
    // saat build, dan mengaktifkan optimizer untuk URL itu berarti menambah
    // satu lapisan cache lagi di atas cache yang sudah diurus kunci versi.
    //
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={`Foto sampul ${nama}`}
      loading="lazy"
      decoding="async"
      className={`${dasar} bg-panel-raised object-cover`}
    />
  );
}
