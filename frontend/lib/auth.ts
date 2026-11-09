import { api } from "./api";
import { clearToken, getToken } from "./token";

export type Role = "investor" | "umkm" | "community";

export type CurrentUser = {
  id: string;
  email: string;
  name: string;
  role: Role;
  created_at: string;
};

// getToken/clearToken sekarang didefinisikan di lib/token.ts, bukan di sini:
// lib/api.ts juga butuh pagar "token sah" yang sama persis untuk header
// Authorization (laporan Fase 11 Task 12), dan mengimpornya langsung dari
// modul ini akan membuat lib/api.ts dan lib/auth.ts saling mengimpor. Re-ekspor
// di sini supaya pemanggil yang sudah ada (AppHeader, dll.) tidak perlu berubah.
export { clearToken, getToken };

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
