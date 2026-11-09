# Fase 10. Fondasi frontend

**Hasil:** Next.js berjalan dengan token dari `DESIGN.md`, api client yang menangani bentuk error
seragam, login, dan toggle tema terang/gelap yang **keduanya benar**.

**Wajib dibaca sebelum menulis baris pertama:** [`../../DESIGN.md`](../../DESIGN.md), lalu muat
skill `antislop:antislop`, `antislop:antislop-ui`, `antislop:antislop-human`,
`antislop:antislop-layoutmobile`.

**Design Read yang berlaku:** platform pendanaan UMKM untuk dua audiens, bahasa visual editorial
dan naratif, dial **ENERGY 2 / RHYTHM 3 / MOTION 2**.

## Struktur file

```
frontend/
  app/
    layout.tsx            # html, tema, font, skip link
    globals.css           # token dari DESIGN.md sebagai CSS variable
    (auth)/masuk/page.tsx
    (auth)/daftar/page.tsx
    page.tsx              # landing
  components/
    ui/Tombol.tsx
    ui/Kolom.tsx          # input + label + pesan error terhubung
    ui/Amount.tsx         # rupiah tabular, motif identitas
    ui/BilahProgres.tsx
    ui/LencanaStatus.tsx
    ui/KeadaanKosong.tsx
    ui/KeadaanMuat.tsx
    ui/KeadaanGalat.tsx
    SakelarTema.tsx
  lib/
    api.ts                # fetch wrapper, menerjemahkan bentuk error
    money.ts              # format rupiah, persentase progres
    status.ts             # label dan varian lencana per status
  tests/                  # vitest
  e2e/                    # playwright
```

Perhatikan: `KeadaanKosong`, `KeadaanMuat`, dan `KeadaanGalat` dibuat **di fase fondasi**, bukan
belakangan. Ketiganya bagian dari desain, bukan bonus ([R-27](../../DESIGN.md)).

---

### Task 1: Token design sebagai CSS variable

**Files:**
- Create: `frontend/app/globals.css`, `frontend/app/layout.tsx`, `frontend/tailwind.config.ts`
- Test: `frontend/tests/token.test.ts`

- [ ] **Step 1: Tulis test yang gagal**

```ts
// frontend/tests/token.test.ts
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const css = readFileSync("app/globals.css", "utf8");

describe("token design", () => {
  it("mendefinisikan seluruh token dari DESIGN.md", () => {
    for (const token of ["--ink", "--paper", "--surface", "--muted",
                         "--line", "--accent", "--ok", "--warn", "--danger"]) {
      expect(css).toContain(`${token}:`);
    }
  });

  it("mendefinisikan ulang token untuk mode gelap", () => {
    expect(css).toMatch(/\[data-theme=['"]dark['"]\]/);
  });

  it("memakai nilai hex persis seperti di DESIGN.md", () => {
    expect(css).toContain("#FFC94A");   // accent
    expect(css).toContain("#FBF9F4");   // paper terang
    expect(css).toContain("#141310");   // paper gelap
  });

  it("tidak memuat warna gradien biru ke ungu", () => {
    // R-01: palet berasal dari DESIGN.md, bukan dari default model.
    expect(css.toLowerCase()).not.toMatch(/linear-gradient\([^)]*#?(6366f1|8b5cf6|a855f7)/);
  });
});
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `cd frontend && npm run test -- token`
Expected: FAIL, berkas `app/globals.css` belum ada

- [ ] **Step 3: Implementasi minimal**

```css
/* frontend/app/globals.css */
:root {
  --ink: #1A1917;
  --paper: #FBF9F4;
  --surface: #F3EFE6;
  --muted: #5C574E;
  --line: #DCD5C7;
  --accent: #FFC94A;
  --ok: #2F6B3A;
  --warn: #A3561F;
  --danger: #A32C1F;

  --radius-kecil: 4px;   /* input, lencana */
  --radius-kartu: 8px;
  --radius-panel: 12px;

  --ruang-1: 4px;  --ruang-2: 8px;  --ruang-3: 16px;
  --ruang-4: 24px; --ruang-5: 40px; --ruang-6: 64px; --ruang-7: 96px;

  --lebar-baca: 66ch;
}

[data-theme="dark"] {
  --ink: #F2EEE6;
  --paper: #141310;
  --surface: #201E19;
  --muted: #A8A196;
  --line: #36332B;
  --ok: #7FCB8C;
  --warn: #E8A765;
  --danger: #F08C7E;
  /* --accent tetap #FFC94A di kedua tema; teks di atasnya selalu gelap. */
}

body { background: var(--paper); color: var(--ink); }

/* Angka rupiah sejajar per digit di seluruh tabel. */
.tabular { font-variant-numeric: tabular-nums; }

:focus-visible {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `npm run test -- token`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/globals.css frontend/tailwind.config.ts
git commit -m "feat: add design tokens as CSS variables"
```

---

### Task 2: Format rupiah dan progres

**Files:**
- Create: `frontend/lib/money.ts`, `frontend/components/ui/Amount.tsx`
- Test: `frontend/tests/money.test.ts`

`Amount` adalah motif identitas produk ini: nominal rupiah selalu besar, tabular, dengan label
kecil di atasnya ([DESIGN.md](../../DESIGN.md)).

- [ ] **Step 1: Tulis test yang gagal**

```ts
// frontend/tests/money.test.ts
import { describe, expect, it } from "vitest";
import { formatRupiah, persenProgres } from "@/lib/money";

describe("formatRupiah", () => {
  it("memakai titik sebagai pemisah ribuan", () => {
    expect(formatRupiah(5_000_000)).toBe("Rp5.000.000");
    expect(formatRupiah(750)).toBe("Rp750");
  });

  it("nol tetap ditampilkan, bukan string kosong", () => {
    expect(formatRupiah(0)).toBe("Rp0");
  });

  it("menolak nilai bukan integer alih-alih membulatkan diam-diam", () => {
    expect(() => formatRupiah(1_000_000.5)).toThrow();
    expect(() => formatRupiah(Number.NaN)).toThrow();
  });
});

describe("persenProgres", () => {
  it("menghitung persentase bulat", () => {
    expect(persenProgres(4_000_000, 10_000_000)).toBe(40);
  });

  it("tepat penuh menghasilkan 100, bukan 99", () => {
    expect(persenProgres(10_000_000, 10_000_000)).toBe(100);
  });

  it("hampir penuh tidak dibulatkan menjadi 100", () => {
    // 99,99% harus terbaca 99, karena 100% berarti funded.
    expect(persenProgres(9_999_000, 10_000_000)).toBe(99);
  });

  it("target nol tidak menghasilkan NaN", () => {
    expect(persenProgres(0, 0)).toBe(0);
  });
});
```

Test "hampir penuh" adalah alasan `Math.floor` dipakai, bukan `Math.round`. Bar yang menunjukkan
100% pada proposal yang belum `funded` adalah kebohongan kecil yang merusak kepercayaan.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `npm run test -- money`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

```ts
// frontend/lib/money.ts
export function formatRupiah(nominal: number): string {
  if (!Number.isInteger(nominal)) {
    throw new TypeError("Nominal rupiah harus bilangan bulat.");
  }
  return `Rp${nominal.toLocaleString("id-ID")}`;
}

export function persenProgres(terkumpul: number, target: number): number {
  if (target <= 0) return 0;
  // floor, bukan round: 99,9% tidak boleh terbaca 100% pada proposal yang belum funded.
  return Math.min(Math.floor((terkumpul / target) * 100), 100);
}
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `npm run test -- money`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add rupiah formatting and funding progress helpers"
```

---

### Task 3: Api client dan bentuk error

**Files:**
- Create: `frontend/lib/api.ts`
- Test: `frontend/tests/api.test.ts`

**Interfaces:**
- Produces: `api.get/post/patch/del`, kelas `ApiError` dengan `code`, `message`, `detail`, `status`.

- [ ] **Step 1: Tulis test yang gagal**

```ts
// frontend/tests/api.test.ts
import { describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/lib/api";

function responsPalsu(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

describe("api client", () => {
  it("menerjemahkan bentuk error backend menjadi ApiError", async () => {
    vi.stubGlobal("fetch", () => responsPalsu(409, {
      error: { code: "pledge_melebihi_sisa",
               message: "Pledge melebihi sisa dana yang dibutuhkan, sisa Rp3.000.000.",
               detail: { remaining_amount: 3_000_000 } },
    }));

    await expect(api.post("/pledges", {})).rejects.toMatchObject({
      code: "pledge_melebihi_sisa",
      status: 409,
      detail: { remaining_amount: 3_000_000 },
    });
  });

  it("respons error tanpa bentuk yang dikenal tetap jadi ApiError", async () => {
    vi.stubGlobal("fetch", () => responsPalsu(502, "<html>Bad Gateway</html>"));
    await expect(api.get("/apa-saja")).rejects.toBeInstanceOf(ApiError);
  });

  it("jaringan putus menghasilkan pesan yang bisa dibaca pengguna", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new TypeError("Failed to fetch")));
    await expect(api.get("/apa-saja")).rejects.toMatchObject({
      code: "jaringan_bermasalah",
    });
  });
});
```

Test kedua dan ketiga menangkap kasus yang sering dilupakan: gateway yang mengembalikan HTML, dan
koneksi yang putus. Keduanya harus berakhir sebagai pesan berbahasa Indonesia di layar, bukan
sebagai `undefined` di tengah komponen.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `npm run test -- api`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

```ts
// frontend/lib/api.ts
export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly detail: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

async function minta<T>(metode: string, jalur: string, body?: unknown): Promise<T> {
  let respons: Response;
  try {
    respons = await fetch(`${BASIS}${jalur}`, { method: metode, headers, body: ... });
  } catch {
    throw new ApiError("jaringan_bermasalah",
      "Koneksi ke server bermasalah. Periksa jaringan lalu coba lagi.", 0);
  }

  if (!respons.ok) {
    // Gateway dan proxy bisa membalas HTML, bukan bentuk error kita.
    const isi = await respons.json().catch(() => null);
    const e = isi?.error;
    throw new ApiError(
      e?.code ?? "galat_tak_dikenal",
      e?.message ?? "Terjadi kesalahan di server. Coba lagi sebentar lagi.",
      respons.status,
      e?.detail ?? {},
    );
  }
  return respons.status === 204 ? (undefined as T) : respons.json();
}
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `npm run test -- api`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add api client that maps the uniform error envelope"
```

---

### Task 4: Tiga keadaan layar data

**Files:**
- Create: `frontend/components/ui/KeadaanKosong.tsx`, `KeadaanMuat.tsx`, `KeadaanGalat.tsx`
- Test: `frontend/tests/keadaan.test.tsx`

- [ ] **Step 1: Tulis test yang gagal**

```tsx
// frontend/tests/keadaan.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { KeadaanGalat, KeadaanKosong } from "@/components/ui";

describe("keadaan kosong", () => {
  it("menyebut sebabnya dan satu aksi berikutnya", () => {
    render(<KeadaanKosong
      sebab="Belum ada proposal masuk ke campaign ini."
      aksi={{ label: "Bagikan tautan campaign", onClick: () => {} }} />);
    expect(screen.getByText(/Belum ada proposal masuk/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Bagikan tautan campaign/ }))
      .toBeInTheDocument();
  });

  it("tidak pernah menampilkan teks 'Tidak ada data'", () => {
    // R-27: keadaan kosong harus menyebut sebab dan aksi, bukan label hampa.
    render(<KeadaanKosong sebab="Belum ada pledge." />);
    expect(screen.queryByText(/tidak ada data/i)).toBeNull();
  });
});

describe("keadaan galat", () => {
  it("menyebut penyebab dan menyediakan tombol coba lagi", () => {
    const coba = vi.fn();
    render(<KeadaanGalat pesan="Koneksi ke server bermasalah." onCobaLagi={coba} />);
    expect(screen.getByText(/Koneksi ke server bermasalah/)).toBeInTheDocument();
    screen.getByRole("button", { name: /Coba lagi/ }).click();
    expect(coba).toHaveBeenCalledOnce();
  });

  it("mengumumkan dirinya ke pembaca layar", () => {
    render(<KeadaanGalat pesan="Gagal memuat." onCobaLagi={() => {}} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `npm run test -- keadaan`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

Komponen ditulis sesuai test. `KeadaanGalat` memakai `role="alert"`. `KeadaanMuat` memesan ruang
dengan tinggi yang sama dengan konten sungguhan, supaya layout tidak melompat saat data datang.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `npm run test -- keadaan`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add empty, loading and error state components"
```

---

### Task 5: Toggle tema yang kedua modenya benar

**Files:**
- Create: `frontend/components/SakelarTema.tsx`
- Test: `frontend/tests/tema.test.tsx`, `frontend/e2e/tema.spec.ts`

- [ ] **Step 1: Tulis test yang gagal**

```tsx
// frontend/tests/tema.test.tsx
describe("sakelar tema", () => {
  it("mengubah data-theme di elemen html", async () => {
    render(<SakelarTema />);
    await userEvent.click(screen.getByRole("button", { name: /tema/i }));
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("bisa dioperasikan dengan keyboard", async () => {
    render(<SakelarTema />);
    await userEvent.tab();
    await userEvent.keyboard("{Enter}");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("menyimpan pilihan dan memulihkannya", () => {
    localStorage.setItem("tema", "dark");
    render(<SakelarTema />);
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
```

```ts
// frontend/e2e/tema.spec.ts
import { expect, test } from "@playwright/test";

test("kedua tema punya kontras yang memadai dan layout yang utuh", async ({ page }) => {
  await page.goto("/");
  for (const tema of ["light", "dark"]) {
    await page.evaluate((t) => { document.documentElement.dataset.theme = t; }, tema);

    // Tidak ada scroll horizontal di lebar ponsel (R-03).
    await page.setViewportSize({ width: 375, height: 800 });
    const lebarGulir = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(lebarGulir).toBeLessThanOrEqual(375);

    // Latar body benar-benar berubah, bukan hanya variabelnya.
    const latar = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor);
    expect(latar).not.toBe("rgba(0, 0, 0, 0)");
  }
});
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `npm run test -- tema && npx playwright test tema`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

Sakelar adalah `<button>` sungguhan dengan `aria-pressed`, bukan `<div>` yang diberi `onClick`.
Skrip inline kecil di `layout.tsx` membaca `localStorage` sebelum render pertama, supaya tidak ada
kedipan tema.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `npm run test -- tema && npx playwright test tema`
Expected: PASS

- [ ] **Step 5: Verifikasi kontras di kedua tema**

Jalankan pemeriksa kontras antislop untuk setiap pasangan token yang benar-benar dipakai di
halaman. Nilai yang sudah diukur ada di [DESIGN.md](../../DESIGN.md); yang perlu diperiksa adalah
pasangan baru yang muncul saat membangun.

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: add working light and dark theme switch"
```

---

### Task 6: Halaman masuk dan daftar

**Files:**
- Create: `frontend/app/(auth)/masuk/page.tsx`, `frontend/app/(auth)/daftar/page.tsx`, `frontend/components/ui/Kolom.tsx`
- Test: `frontend/tests/form-auth.test.tsx`

- [ ] **Step 1: Tulis test yang gagal**

```tsx
// frontend/tests/form-auth.test.tsx
describe("form masuk", () => {
  it("setiap kolom punya label yang terhubung", () => {
    render(<FormMasuk />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("pesan error terhubung ke kolomnya lewat aria-describedby", async () => {
    render(<FormMasuk />);
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));
    const kolom = screen.getByLabelText(/email/i);
    const idPesan = kolom.getAttribute("aria-describedby");
    expect(idPesan).toBeTruthy();
    expect(document.getElementById(idPesan!)).toHaveTextContent(/email/i);
  });

  it("menampilkan pesan dari backend apa adanya, bukan pesan generik", async () => {
    vi.stubGlobal("fetch", () => responsPalsu(401, {
      error: { code: "kredensial_salah", message: "Email atau password salah." },
    }));
    render(<FormMasuk />);
    await isiDanKirim();
    expect(await screen.findByRole("alert"))
      .toHaveTextContent("Email atau password salah.");
  });

  it("tombol kirim nonaktif selama permintaan berjalan", async () => {
    render(<FormMasuk />);
    await isiDanKirim();
    expect(screen.getByRole("button", { name: /masuk/i })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `npm run test -- form-auth`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

`Kolom.tsx` menggabungkan `<label htmlFor>`, `<input id aria-describedby aria-invalid>`, dan
`<p id role="alert">`. Satu komponen, dipakai setiap form di seluruh aplikasi, sehingga
aksesibilitas form tidak bergantung pada ingatan.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `npm run test -- form-auth`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add accessible sign in and sign up pages"
```

## Gerbang keluar fase 10, Delivery Gate antislop

Selain `make test-fe` dan `make check` hijau, jalankan Delivery Gate dan sertakan laporannya.
Yang paling relevan untuk fase ini:

- [ ] R-03 tidak ada scroll horizontal di 320px, 375px, dan 768px
- [ ] R-21 dan R-34 kedua tema berfungsi penuh, diperiksa satu per satu
- [ ] R-25 seluruh pasangan warna yang dipakai sudah diukur dan lolos AA
- [ ] R-26 setiap tombol punya perilaku nyata, tidak ada kontrol mati
- [ ] R-27 ketiga keadaan layar data ada dan menyebut sebab serta aksi
- [ ] R-32 seluruh UI bisa dioperasikan keyboard, indikator fokus terlihat
- [ ] R-35 aplikasi benar-benar dijalankan, setiap kontrol diklik, hasilnya dicatat satu per satu
- [ ] R-37 arah visual berasal dari `DESIGN.md`, bukan dari default model
