import type { SVGProps } from "react";

/**
 * Lambang Modalink: dua mata rantai yang saling mengait pada diagonal
 * menanjak.
 *
 * Dua mata, bukan tiga atau lima: ada tepat dua sisi yang disambungkan
 * produk ini, yang mendanai dan yang didanai. Diagonalnya menanjak karena
 * dana di sini bergerak naik bertahap per milestone, bukan cair sekaligus.
 * Mata atas memakai warna aksen karena ia menandai tahap yang sedang cair;
 * mata bawah netral, yaitu modal yang sudah terkumpul dan menunggu.
 *
 * Kaitnya dibuat dari dua persilangan dengan urutan tumpuk yang berlawanan:
 * di kiri-atas mata aksen lewat di depan, di kanan-bawah mata bawah
 * digambar ulang lewat clipPath sehingga ia yang di depan. Tanpa pembalikan
 * itu keduanya hanya dua kotak bertumpuk, dan kata "link" pada nama produk
 * tidak pernah benar-benar terbentuk.
 *
 * Mata bawah memakai currentColor supaya satu berkas ini bekerja di tema
 * gelap maupun terang tanpa versi kedua. Warna aksen dikunci karena ia
 * memang tidak pernah berbalik antar-tema; lihat tests/accent-contrast.test.ts.
 */
export function Logo({ title, ...props }: SVGProps<SVGSVGElement> & { title?: string }) {
  // id unik per instance tidak diperlukan: hanya ada satu logo per halaman,
  // dan clipPath yang sama dipakai ulang tanpa masalah bila toh ada dua.
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      aria-hidden={title ? undefined : true}
      role={title ? "img" : undefined}
      {...props}
    >
      {title && <title>{title}</title>}
      <defs>
        <clipPath id="modalink-kait">
          <rect x="30" y="28" width="12" height="14" />
        </clipPath>
      </defs>
      <g strokeWidth="7">
        <rect x="11" y="27" width="26" height="26" rx="9" stroke="currentColor" />
        <rect x="27" y="11" width="26" height="26" rx="9" stroke="var(--accent)" />
        <rect
          x="11"
          y="27"
          width="26"
          height="26"
          rx="9"
          stroke="currentColor"
          clipPath="url(#modalink-kait)"
        />
      </g>
    </svg>
  );
}
