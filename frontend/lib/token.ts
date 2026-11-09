// Satu-satunya tempat yang tahu kunci localStorage tempat token disimpan dan
// apa artinya "token sah". Dipisah dari lib/auth.ts supaya lib/api.ts (yang
// butuh kunci yang sama untuk header Authorization) tidak perlu mengimpor
// lib/auth.ts, yang sebaliknya mengimpor `api` dari lib/api.ts -- mengimpor
// langsung dari sana akan membuat dua modul saling mengimpor satu sama lain.
const TOKEN_KEY = "modalink_token";

// "undefined" pernah benar-benar tersimpan di localStorage karena bug di
// fase 10 (kode lama menulis String(undefined) saat login gagal diam-diam).
// Token semacam itu harus diperlakukan sama dengan tidak ada token sama
// sekali, bukan dikirim ke server dan membuat seluruh permintaan berikutnya
// membawa header Authorization yang tidak valid (lihat laporan Fase 11 Task
// 12: lib/api.ts dulu membaca localStorage mentah tanpa pagar ini sama
// sekali, jadi bug lama itu bisa terulang lewat jalur lain).
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
