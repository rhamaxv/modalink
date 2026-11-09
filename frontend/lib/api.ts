// Default relatif, bukan URL absolut: di produksi frontend dan backend berada
// di balik proxy yang sama, dan di dev `NEXT_PUBLIC_API_URL` menimpanya ke
// origin backend. Lihat .claude/prd/10-api-contract.md untuk bentuk error.
//
// `||`, bukan `??`, dan bedanya mematikan di produksi: Docker build arg yang
// dibiarkan kosong menghasilkan string kosong, bukan undefined, dan `??` hanya
// jatuh ke default untuk undefined. Dibangun begitu, seluruh request kehilangan
// prefiks /api/v1 dan 404, sementara setiap container melaporkan dirinya sehat.
const BASIS = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

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

// Token ditulis oleh alur login (fase berikutnya). Dibungkus try/catch karena
// localStorage tidak tersedia saat komponen ini dirender di server.
function ambilToken(): string | null {
  try {
    return localStorage.getItem("modalink_token");
  } catch {
    return null;
  }
}

function headerPermintaan(): HeadersInit {
  const header: Record<string, string> = { "Content-Type": "application/json" };
  const token = ambilToken();
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

export const api = {
  get: <T>(jalur: string) => minta<T>("GET", jalur),
  post: <T>(jalur: string, body?: unknown) => minta<T>("POST", jalur, body),
  patch: <T>(jalur: string, body?: unknown) => minta<T>("PATCH", jalur, body),
  del: <T>(jalur: string) => minta<T>("DELETE", jalur),
};
