import { API_BASE } from "./api";

export type CoverOwner = "proposals" | "campaigns";

// URL gambar sampul dibangun di klien dari id pemiliknya, bukan dikirim
// backend sebagai string. Backend mengirim `cover_updated_at` saja, dan satu
// field itu menjawab dua hal sekaligus: apakah sampulnya ADA (null berarti
// belum), dan versi mana yang berlaku.
//
// Versinya ikut ke query string, dan itu bukan hiasan: tanpa penanda versi,
// URL sampul tidak pernah berubah walau fotonya diganti, sehingga browser
// terus menyajikan foto lama sampai cachenya kedaluwarsa sendiri. Endpoint
// gambarnya memasang Cache-Control immutable justru karena URL-nya membawa
// versi ini.
export function coverUrl(
  owner: CoverOwner,
  id: string,
  coverUpdatedAt: string | null | undefined,
): string | null {
  if (!coverUpdatedAt) return null;
  const versi = Math.floor(new Date(coverUpdatedAt).getTime() / 1000);
  return `${API_BASE}/${owner}/${id}/cover?v=${versi}`;
}
