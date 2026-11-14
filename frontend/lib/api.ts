import { getToken } from "./token";

// Default relatif, bukan URL absolut: di produksi frontend dan backend berada
// di balik proxy yang sama, dan di dev `NEXT_PUBLIC_API_URL` menimpanya ke
// origin backend. Lihat .claude/prd/10-api-contract.md untuk bentuk error.
//
// `||`, bukan `??`, dan bedanya mematikan di produksi: Docker build arg yang
// dibiarkan kosong menghasilkan string kosong, bukan undefined, dan `??` hanya
// jatuh ke default untuk undefined. Dibangun begitu, seluruh request kehilangan
// prefiks /api/v1 dan 404, sementara setiap container melaporkan dirinya sehat.
const BASIS = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

// Diekspor untuk lib/cover.ts, yang menyusun URL gambar sendiri alih-alih
// lewat fetch: <img src> tidak melewati helper api di bawah sama sekali, tapi
// ia tetap harus menunjuk basis yang sama persis.
export const API_BASE = BASIS;

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly detail: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function headerPermintaan(): HeadersInit {
  const header: Record<string, string> = { "Content-Type": "application/json" };
  // getToken() dari lib/token.ts, bukan localStorage.getItem mentah: modul
  // itu menolak token kosong dan literal "undefined" (bug fase 10 yang
  // menulis String(undefined) saat login gagal diam-diam). Sebelum ini,
  // fungsi ambilToken() di sini membaca localStorage langsung tanpa pagar
  // itu, jadi token rusak tetap terkirim sebagai "Bearer undefined" di
  // setiap permintaan walau header AppHeader sudah benar menunjukkan "Masuk"
  // (lihat laporan Fase 11 Task 12).
  const token = getToken();
  if (token) header.Authorization = `Bearer ${token}`;
  return header;
}

async function minta<T>(metode: string, jalur: string, body?: unknown): Promise<T> {
  let respons: Response;
  try {
    respons = await fetch(`${BASIS}${jalur}`, {
      method: metode,
      headers: headerPermintaan(),
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      "jaringan_bermasalah",
      "Koneksi ke server bermasalah. Periksa jaringan lalu coba lagi.",
      0,
    );
  }

  if (!respons.ok) {
    // Gateway dan proxy bisa membalas HTML, bukan bentuk error kita.
    const isi: unknown = await respons.json().catch(() => null);
    const e = (isi as { error?: Record<string, unknown> } | null)?.error;
    throw new ApiError(
      typeof e?.code === "string" ? e.code : "galat_tak_dikenal",
      typeof e?.message === "string" ? e.message : "Terjadi kesalahan di server. Coba lagi sebentar lagi.",
      respons.status,
      (e?.detail as Record<string, unknown>) ?? {},
    );
  }
  return respons.status === 204 ? (undefined as T) : respons.json();
}

// Unggahan multipart tidak bisa lewat `minta` di atas, dan bukan sekadar
// karena bodinya berbeda: `minta` selalu memasang Content-Type
// application/json, sedangkan untuk FormData header itu HARUS dibiarkan
// kosong supaya browser menuliskannya sendiri lengkap dengan boundary.
// Menyetelnya sendiri membuat server tidak bisa memisahkan bagian-bagiannya
// dan unggahan gagal dengan galat yang jauh dari sebabnya.
async function unggah(jalur: string, berkas: File): Promise<void> {
  const form = new FormData();
  form.append("file", berkas);
  const header: Record<string, string> = {};
  const token = getToken();
  if (token) header.Authorization = `Bearer ${token}`;

  let respons: Response;
  try {
    respons = await fetch(`${BASIS}${jalur}`, { method: "PUT", headers: header, body: form });
  } catch {
    throw new ApiError(
      "jaringan_bermasalah",
      "Koneksi ke server bermasalah. Periksa jaringan lalu coba lagi.",
      0,
    );
  }
  if (!respons.ok) {
    const isi: unknown = await respons.json().catch(() => null);
    const e = (isi as { error?: Record<string, unknown> } | null)?.error;
    throw new ApiError(
      typeof e?.code === "string" ? e.code : "galat_tak_dikenal",
      typeof e?.message === "string"
        ? e.message
        : "Terjadi kesalahan di server. Coba lagi sebentar lagi.",
      respons.status,
    );
  }
}

// Pengajuan proposal: satu bagian JSON dan satu bagian berkas dalam satu
// permintaan. Terpisah dari `unggah` di atas karena bentuknya memang beda --
// metodenya POST, bagiannya dua, dan ia mengembalikan proposal yang baru
// dibuat alih-alih 204 -- tapi alasan ia tidak lewat `minta` sama persis:
// Content-Type untuk FormData harus ditulis browser sendiri beserta
// boundary-nya.
async function kirimProposal<T>(
  jalur: string,
  muatan: unknown,
  dokumen: File,
): Promise<T> {
  const form = new FormData();
  // Bagian JSON dikirim sebagai string, bukan sebagai beberapa field form
  // terpisah: milestone adalah daftar objek, dan memecahnya menjadi
  // milestones[0][amount] dan seterusnya berarti menulis ulang aturan
  // validasi Pydantic di sisi klien.
  form.append("payload", JSON.stringify(muatan));
  form.append("document", dokumen, dokumen.name);

  const header: Record<string, string> = {};
  const token = getToken();
  if (token) header.Authorization = `Bearer ${token}`;

  let respons: Response;
  try {
    respons = await fetch(`${BASIS}${jalur}`, { method: "POST", headers: header, body: form });
  } catch {
    throw new ApiError(
      "jaringan_bermasalah",
      "Koneksi ke server bermasalah. Periksa jaringan lalu coba lagi.",
      0,
    );
  }
  if (!respons.ok) {
    const isi: unknown = await respons.json().catch(() => null);
    const e = (isi as { error?: Record<string, unknown> } | null)?.error;
    throw new ApiError(
      typeof e?.code === "string" ? e.code : "galat_tak_dikenal",
      typeof e?.message === "string"
        ? e.message
        : "Terjadi kesalahan di server. Coba lagi sebentar lagi.",
      respons.status,
      (e?.detail as Record<string, unknown>) ?? {},
    );
  }
  return respons.json();
}

export const api = {
  get: <T>(jalur: string) => minta<T>("GET", jalur),
  unggah,
  kirimProposal,
  post: <T>(jalur: string, body?: unknown) => minta<T>("POST", jalur, body),
  patch: <T>(jalur: string, body?: unknown) => minta<T>("PATCH", jalur, body),
  del: <T>(jalur: string) => minta<T>("DELETE", jalur),
};

// `minta<T>` di atas mengembalikan `respons.json()` yang dipaksa ke tipe T
// lewat generic, tanpa memeriksa bentuknya sungguh cocok (lihat laporan Fase
// 11 Task 12: dua halaman mengira endpoint daftar mengembalikan array
// mentah, padahal backend selalu membungkusnya { items: [...] }; keduanya
// lolos tsc dan test unit karena mock masing-masing menebak bentuk yang sama
// salahnya, lalu gagal di browser sungguhan dengan TypeError yang jauh dari
// baris fetch-nya sendiri). Dipakai di titik pemanggilan endpoint daftar
// sebagai pagar tipis: kalau field "items" tidak ada, pemanggil tahu lewat
// ApiError yang jelas, bukan lewat .find/.map yang melempar beberapa baris
// kemudian tanpa menyebut endpoint mana yang salah bentuk.
export function daftarDariRespons<T>(data: unknown, jalur: string): T[] {
  const items = (data as { items?: unknown } | null)?.items;
  if (!Array.isArray(items)) {
    throw new ApiError(
      "bentuk_respons_tidak_terduga",
      `Bentuk respons dari ${jalur} tidak sesuai yang diharapkan: field "items" tidak ditemukan.`,
      0,
    );
  }
  return items as T[];
}
