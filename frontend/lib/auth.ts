import { api } from "./api";

export type Role = "investor" | "umkm" | "community";

export type CurrentUser = {
  id: string;
  email: string;
  name: string;
  role: Role;
  created_at: string;
};

const TOKEN_KEY = "modalink_token";

// "undefined" pernah benar-benar tersimpan di localStorage karena bug di
// fase 10 (kode lama menulis String(undefined) saat login gagal diam-diam).
// Token semacam itu harus diperlakukan sama dengan tidak ada token sama
// sekali, bukan dikirim ke server dan membuat seluruh halaman menampilkan
// galat 401 yang membingungkan.
function tokenSah(token: string | null): token is string {
  return typeof token === "string" && token.length > 0 && token !== "undefined";
}

export function getToken(): string | null {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    return tokenSah(token) ? token : null;
  } catch {
    return null;
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Tidak ada localStorage untuk dibersihkan; tidak ada yang perlu dilakukan.
  }
}

/** Alias baca: menghapus token adalah seluruh pekerjaan "keluar" di sisi klien. */
export function signOut(): void {
  clearToken();
}

// Dipakai AppHeader dan setiap penjaga route. Mengembalikan null untuk tiga
// kasus yang harus ditangani sama, bukan dibedakan: tidak ada token, token
// rusak ("undefined"), dan token yang ditolak server (kedaluwarsa atau
// memang tidak sah). Ketiganya berarti "dianggap belum masuk", bukan
// membuat aplikasi macet.
export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  if (!getToken()) return null;
  try {
    return await api.get<CurrentUser>("/auth/me");
  } catch {
    return null;
  }
}

// Dipakai SignInForm untuk kembali ke halaman yang semula dituju setelah
// masuk. Hanya path relatif satu-garis-miring yang diterima: "//host" adalah
// URL protokol-relatif yang bisa mengarah ke domain lain (open redirect).
export function tujuanAmanSetelahMasuk(tujuan: string | null): string {
  if (tujuan && /^\/(?!\/)/.test(tujuan)) return tujuan;
  return "/";
}
