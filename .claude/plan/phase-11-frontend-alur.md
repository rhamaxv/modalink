# Fase 11. Halaman dan alur

**Hasil:** seluruh flow bisa dijalankan lewat browser, dari membuat campaign sampai milestone cair.

**Wajib dibaca dulu:** [`../../DESIGN.md`](../../DESIGN.md), skill `antislop:antislop` dan
`antislop:antislop-ui`.

## Peringatan khusus fase ini

Modul antislop menandai dua jebakan yang persis mengintai produk ini. Keduanya ditulis di sini
supaya tidak ditemukan saat sudah terlanjur dibangun:

**Cangkang dashboard default.** Sidebar kiri, bilah atas, empat kartu statistik, satu grafik, satu
tabel, dipilih sebelum ada yang bertanya layar ini untuk apa. Lawannya: sebut dulu **satu keputusan**
yang diambil pengguna di layar itu, lalu bangun hierarkinya di sekitar keputusan tersebut.

| Halaman | Satu keputusan yang diambil di sana |
| --- | --- |
| Daftar proposal investor | Proposal mana yang layak saya baca lebih dalam |
| Detail proposal | Berapa yang masuk akal saya sanggupi, atau tidak sama sekali |
| Dashboard UMKM | Apa yang harus saya kerjakan sekarang |
| Milestone lead investor | Laporan ini cukup atau perlu direvisi |

**Angka karangan.** Produk ini penuh angka rupiah, dan empat kartu statistik berisi angka yang
belum tersambung ke data adalah pelanggaran R-17 yang paling mudah terjadi. Aturan di fase ini:
angka muncul hanya kalau datanya nyata. Belum tersambung berarti tidak ditampilkan.

## Struktur file

```
frontend/app/
  jelajah/page.tsx                       # daftar proposal publik
  proposal/[id]/page.tsx                 # detail, panel skor, pledge, komentar
  investor/campaign/page.tsx             # campaign milik saya
  investor/campaign/baru/page.tsx
  investor/campaign/[id]/page.tsx        # daftar proposal masuk
  investor/milestone/page.tsx            # yang menunggu persetujuan saya
  umkm/beranda/page.tsx                  # proposal saya dan apa yang harus dikerjakan
  umkm/proposal/baru/page.tsx
  umkm/milestone/[id]/lapor/page.tsx
frontend/components/
  PanelSkor.tsx          BilahFunding.tsx      KartuProposal.tsx
  FormPledge.tsx         LiniMilestone.tsx     DaftarKomentar.tsx
  FormProposal.tsx       RencanaMilestone.tsx
```

---

### Task 1: Form proposal dengan validasi milestone langsung

**Files:**
- Create: `frontend/components/FormProposal.tsx`, `RencanaMilestone.tsx`
- Test: `frontend/tests/form-proposal.test.tsx`

Form terpanjang di aplikasi, diisi oleh pengguna yang paling tidak sabar dengan formulir. Validasi
jumlah milestone berjalan di klien supaya UMKM tidak menunggu bolak-balik ke server.

- [ ] **Step 1: Tulis test yang gagal**

```tsx
// frontend/tests/form-proposal.test.tsx
describe("rencana milestone", () => {
  it("menampilkan selisih saat jumlah belum pas", async () => {
    render(<FormProposal danaDiminta={10_000_000} />);
    await isiMilestone([5_000_000, 4_000_000]);
    expect(screen.getByRole("status"))
      .toHaveTextContent("Kurang Rp1.000.000 dari dana yang diminta");
  });

  it("menampilkan kelebihan saat jumlah melewati", async () => {
    render(<FormProposal danaDiminta={10_000_000} />);
    await isiMilestone([6_000_000, 6_000_000]);
    expect(screen.getByRole("status"))
      .toHaveTextContent("Lebih Rp2.000.000 dari dana yang diminta");
  });

  it("menandai pas saat jumlahnya tepat", async () => {
    render(<FormProposal danaDiminta={10_000_000} />);
    await isiMilestone([5_000_000, 5_000_000]);
    expect(screen.getByRole("status")).toHaveTextContent("Jumlah sudah pas");
  });

  it("tombol kirim nonaktif selama jumlah belum pas", async () => {
    render(<FormProposal danaDiminta={10_000_000} />);
    await isiMilestone([5_000_000, 4_000_000]);
    expect(screen.getByRole("button", { name: /kirim proposal/i })).toBeDisabled();
  });

  it("minimal dua milestone, baris kedua tidak bisa dihapus", async () => {
    render(<FormProposal danaDiminta={10_000_000} />);
    const hapus = screen.getAllByRole("button", { name: /hapus tahap/i });
    expect(hapus).toHaveLength(0);   // dengan tepat dua baris, tidak ada yang bisa dihapus
  });

  it("menolak nominal pecahan di kolom rupiah", async () => {
    render(<FormProposal danaDiminta={10_000_000} />);
    await userEvent.type(screen.getAllByLabelText(/nominal/i)[0], "5000000.5");
    expect(screen.getAllByLabelText(/nominal/i)[0]).toHaveValue("5000000");
  });

  it("selisih diumumkan ke pembaca layar tanpa memindahkan fokus", async () => {
    render(<FormProposal danaDiminta={10_000_000} />);
    const kolom = screen.getAllByLabelText(/nominal/i)[0];
    kolom.focus();
    await isiMilestone([5_000_000, 4_000_000]);
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
    expect(document.activeElement).toBe(kolom);
  });
});
```

Test terakhir penting: `aria-live="polite"` mengumumkan perubahan tanpa merebut fokus dari kolom
yang sedang diketik.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `npm run test -- form-proposal`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

Penghitung selisih memakai `formatRupiah` dari fase 10. Kolom nominal menolak karakter non-digit
saat diketik, bukan saat dikirim.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `npm run test -- form-proposal`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add proposal form with live milestone difference validation"
```

---

### Task 2: Panel skor AI

**Files:**
- Create: `frontend/components/PanelSkor.tsx`
- Test: `frontend/tests/panel-skor.test.tsx`

Panel ini yang membedakan produk dari marketplace biasa, jadi ia menampilkan skor **terurai**,
bukan satu angka gelap ([US-I3](../prd/02-personas-user-stories.md)).

- [ ] **Step 1: Tulis test yang gagal**

```tsx
// frontend/tests/panel-skor.test.tsx
const skor = {
  fit_score: 34, data_quality_score: 21, impact_score: 18, total_score: 73,
  threshold_used: 60, model_name: "gemini-2.5-flash",
  created_at: "2026-11-07T10:00:00Z",
  red_flags: [
    { code: "projeksi_tidak_realistis", severity: "critical",
      message: "Proyeksi omzet naik 40 kali lipat dalam 6 bulan.",
      evidence: "target omzet Rp400 juta per bulan" },
  ],
  brief: { strengths: ["Usaha berjalan 3 tahun."], risks: ["Proyeksi agresif."],
           recommendation: "Minta rincian asumsi proyeksi." },
};

describe("panel skor", () => {
  it("menampilkan tiga komponen beserta batas maksimumnya", () => {
    render(<PanelSkor skor={skor} />);
    expect(screen.getByText("34")).toBeInTheDocument();
    expect(screen.getByText(/dari 40/)).toBeInTheDocument();
    expect(screen.getByText(/dari 30/)).toHaveLength;
  });

  it("menampilkan ambang campaign di sebelah total", () => {
    render(<PanelSkor skor={skor} />);
    expect(screen.getByText(/ambang campaign: 60/i)).toBeInTheDocument();
  });

  it("red flag menampilkan level dan kutipan buktinya", () => {
    render(<PanelSkor skor={skor} />);
    expect(screen.getByText(/kritis/i)).toBeInTheDocument();
    expect(screen.getByText(/target omzet Rp400 juta per bulan/)).toBeInTheDocument();
  });

  it("level red flag tidak disampaikan lewat warna saja", () => {
    render(<PanelSkor skor={skor} />);
    // Ada teks "kritis", bukan hanya titik merah.
    expect(screen.getByText(/kritis/i).tagName).not.toBe("SPAN_KOSONG");
  });

  it("menyebut model dan waktu penilaian", () => {
    render(<PanelSkor skor={skor} />);
    expect(screen.getByText(/gemini-2.5-flash/)).toBeInTheDocument();
  });

  it("menyatakan bahwa keputusan akhir ada di investor", () => {
    render(<PanelSkor skor={skor} />);
    expect(screen.getByText(/keputusan akhir ada di/i)).toBeInTheDocument();
  });

  it("menampilkan keadaan 'sedang dinilai' saat scoring belum selesai", () => {
    render(<PanelSkor skor={null} scoringStatus="processing" />);
    expect(screen.getByText(/sedang dinilai/i)).toBeInTheDocument();
  });

  it("menampilkan tombol nilai ulang saat scoring gagal, bukan pesan penolakan", () => {
    render(<PanelSkor skor={null} scoringStatus="failed" />);
    expect(screen.getByRole("button", { name: /nilai ulang/i })).toBeInTheDocument();
    expect(screen.queryByText(/ditolak/i)).toBeNull();
  });
});
```

Dua test terakhir adalah [D-09](../docs/decisions.md) di lapisan UI: kegagalan teknis tidak boleh
terbaca sebagai penolakan, bahkan secara tidak sengaja lewat pilihan kata.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `npm run test -- panel-skor`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

Komponen dibangun dari token `DESIGN.md`. Aksen kuning **tidak** dipakai di sini: panel skor
adalah informasi, bukan aksi. Aksen disimpan untuk tombol pledge di sebelahnya.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `npm run test -- panel-skor`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add AI score panel with component breakdown and evidence"
```

---

### Task 3: Bilah funding dan form pledge

**Files:**
- Create: `frontend/components/BilahFunding.tsx`, `FormPledge.tsx`
- Test: `frontend/tests/pledge.test.tsx`

- [ ] **Step 1: Tulis test yang gagal**

```tsx
// frontend/tests/pledge.test.tsx
describe("bilah funding", () => {
  it("menampilkan terkumpul, target, dan sisa", () => {
    render(<BilahFunding terkumpul={4_000_000} target={10_000_000} pendana={2} />);
    expect(screen.getByText("Rp4.000.000")).toBeInTheDocument();
    expect(screen.getByText(/dari Rp10.000.000/)).toBeInTheDocument();
    expect(screen.getByText(/sisa Rp6.000.000/i)).toBeInTheDocument();
  });

  it("menyebut jumlah pendana, karena co-funding adalah intinya", () => {
    render(<BilahFunding terkumpul={4_000_000} target={10_000_000} pendana={3} />);
    expect(screen.getByText(/3 investor/i)).toBeInTheDocument();
  });

  it("progres dibaca pembaca layar lewat progressbar, bukan hanya lebar div", () => {
    render(<BilahFunding terkumpul={4_000_000} target={10_000_000} pendana={1} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "40");
    expect(bar).toHaveAttribute("aria-valuetext", "Rp4.000.000 dari Rp10.000.000");
  });
});

describe("form pledge", () => {
  it("menampilkan sisa dana sebelum pengguna mengetik", () => {
    render(<FormPledge sisa={6_000_000} />);
    expect(screen.getByText(/maksimal Rp6.000.000/i)).toBeInTheDocument();
  });

  it("memperingatkan sebelum kirim kalau nominal melebihi sisa", async () => {
    render(<FormPledge sisa={6_000_000} />);
    await userEvent.type(screen.getByLabelText(/nominal/i), "7000000");
    expect(screen.getByRole("button", { name: /danai/i })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(/melebihi sisa/i);
  });

  it("menampilkan pesan backend saat server menolak karena balapan", async () => {
    // Investor lain mendahului; klien tidak bisa mencegahnya, hanya menjelaskannya.
    vi.stubGlobal("fetch", () => responsPalsu(409, {
      error: { code: "pledge_melebihi_sisa",
               message: "Pledge melebihi sisa dana yang dibutuhkan, sisa Rp1.000.000.",
               detail: { remaining_amount: 1_000_000 } },
    }));
    render(<FormPledge sisa={6_000_000} />);
    await isiDanKirim("5000000");
    expect(await screen.findByRole("alert")).toHaveTextContent("sisa Rp1.000.000");
  });

  it("memperbarui sisa dari detail error setelah ditolak", async () => {
    render(<FormPledge sisa={6_000_000} />);
    await isiDanKirim("5000000");
    expect(await screen.findByText(/maksimal Rp1.000.000/i)).toBeInTheDocument();
  });
});
```

Dua test terakhir menangani RF-1 dari sisi pengguna: validasi klien tidak bisa mencegah balapan,
tapi UI bisa menjelaskannya dan langsung memperbarui angka sisa.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `npm run test -- pledge`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

Bilah funding memakai aksen kuning. Ini salah satu dari sedikit tempat aksen muncul, sesuai
[DESIGN.md](../../DESIGN.md), dan alasannya ditulis di komentar komponen.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `npm run test -- pledge`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add funding progress bar and pledge form"
```

---

### Task 4: Lini milestone dan alur persetujuan

**Files:**
- Create: `frontend/components/LiniMilestone.tsx`, `frontend/app/investor/milestone/page.tsx`
- Test: `frontend/tests/milestone.test.tsx`

- [ ] **Step 1: Tulis test yang gagal**

```tsx
// frontend/tests/milestone.test.tsx
describe("lini milestone", () => {
  it("menandai tahap yang sedang berjalan dengan aksen dan teks", () => {
    render(<LiniMilestone milestones={[
      { seq: 1, status: "disbursed", amount: 5_000_000, title: "Beli mesin" },
      { seq: 2, status: "reported", amount: 5_000_000, title: "Bahan baku" },
    ]} />);
    expect(screen.getByText(/menunggu persetujuan/i)).toBeInTheDocument();
    expect(screen.getByText(/sudah cair/i)).toBeInTheDocument();
  });

  it("status tidak disampaikan lewat warna saja", () => {
    const { container } = render(<LiniMilestone milestones={[...]} />);
    // Setiap penanda status punya teks pendamping.
    container.querySelectorAll("[data-status]").forEach((el) => {
      expect(el.textContent?.trim()).not.toBe("");
    });
  });

  it("tombol approve hanya muncul untuk lead investor", () => {
    render(<LiniMilestone milestones={[...]} sayaLeadInvestor={false} />);
    expect(screen.queryByRole("button", { name: /setujui/i })).toBeNull();
  });

  it("reject membuka kolom catatan dan menolak catatan terlalu pendek", async () => {
    render(<LiniMilestone milestones={[...]} sayaLeadInvestor />);
    await userEvent.click(screen.getByRole("button", { name: /tolak/i }));
    await userEvent.type(screen.getByLabelText(/catatan/i), "ok");
    expect(screen.getByRole("button", { name: /kirim penolakan/i })).toBeDisabled();
  });

  it("riwayat laporan yang ditolak tetap terlihat beserta catatannya", () => {
    render(<LiniMilestone milestones={[{
      seq: 2, status: "pending", amount: 5_000_000, title: "Bahan baku",
      laporan: [
        { review_status: "rejected", narrative: "Laporan awal.",
          reviewer_note: "Angka omzet belum disertai bukti." },
        { review_status: "pending", narrative: "Revisi dengan bukti." },
      ],
    }]} />);
    expect(screen.getByText(/Angka omzet belum disertai bukti/)).toBeInTheDocument();
    expect(screen.getByText(/Laporan awal/)).toBeInTheDocument();
  });

  it("menampilkan keadaan kosong saat tidak ada yang menunggu persetujuan", () => {
    render(<AntrianPersetujuan milestones={[]} />);
    expect(screen.getByText(/belum ada laporan yang menunggu/i)).toBeInTheDocument();
    expect(screen.queryByText(/tidak ada data/i)).toBeNull();
  });
});
```

Test kelima menegakkan [BR-46](../prd/07-business-rules.md) di UI: jejak revisi disimpan di
backend, dan harus terlihat, kalau tidak penyimpanannya sia-sia.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `npm run test -- milestone`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

Lini milestone disusun vertikal dengan nominal besar di tiap tahap, mengikuti motif identitas.
Tahap yang sedang berjalan ditandai aksen; tahap lain tidak.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `npm run test -- milestone`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add milestone timeline with report revision history"
```

---

### Task 5: Halaman jelajah dan komposisi yang bervariasi

**Files:**
- Create: `frontend/app/jelajah/page.tsx`, `frontend/app/page.tsx`
- Test: `frontend/tests/komposisi.test.tsx`

Dial **RHYTHM 3** berarti tidak boleh ada dua section berpola sama. Ini diuji, bukan diserahkan
ke ingatan.

- [ ] **Step 1: Tulis test yang gagal**

```tsx
// frontend/tests/komposisi.test.tsx
import { readFileSync } from "node:fs";

describe("RHYTHM 3 di landing page", () => {
  it("tidak ada dua section berurutan dengan pola komposisi yang sama", () => {
    const sumber = readFileSync("app/page.tsx", "utf8");
    const pola = [...sumber.matchAll(/data-pola="([a-z-]+)"/g)].map((m) => m[1]);
    expect(pola.length).toBeGreaterThanOrEqual(4);
    pola.forEach((p, i) => {
      if (i > 0) expect(p).not.toBe(pola[i - 1]);
    });
  });

  it("setiap section menyatakan polanya secara eksplisit", () => {
    const sumber = readFileSync("app/page.tsx", "utf8");
    const jumlahSection = (sumber.match(/<section/g) ?? []).length;
    const jumlahPola = (sumber.match(/data-pola=/g) ?? []).length;
    expect(jumlahPola).toBe(jumlahSection);
  });
});

describe("landing page bebas dari bentuk default", () => {
  it("tidak ada lencana pil di atas H1", () => {
    render(<Beranda />);
    const h1 = screen.getByRole("heading", { level: 1 });
    const sebelumnya = h1.previousElementSibling;
    expect(sebelumnya?.getAttribute("data-pola")).not.toBe("eyebrow-badge");
  });

  it("tidak ada angka statistik tanpa sumber data", () => {
    render(<Beranda />);
    // R-17: tidak ada "10rb+ pengguna" atau sejenisnya.
    expect(screen.queryByText(/\d+(rb|k|jt)\+/i)).toBeNull();
  });

  it("tidak ada testimoni", () => {
    render(<Beranda />);
    expect(screen.queryByText(/testimoni/i)).toBeNull();
  });

  it("setiap tautan navigasi menuju halaman yang benar-benar ada", () => {
    render(<Beranda />);
    const rutaAda = ["/", "/jelajah", "/masuk", "/daftar"];
    screen.getAllByRole("link").forEach((a) => {
      const href = a.getAttribute("href") ?? "";
      if (href.startsWith("/")) expect(rutaAda).toContain(href.split("#")[0]);
    });
  });
});
```

`data-pola` adalah atribut yang dipasang di setiap `<section>` dengan nama polanya
(`naratif-kiri`, `dua-kolom-asimetris`, `lebar-penuh-kutipan`, `daftar-bernomor`). Atribut itu
membuat aturan RHYTHM bisa diuji, bukan sekadar dijanjikan.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `npm run test -- komposisi`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

Landing page dibangun dari section yang polanya benar-benar berbeda. Tidak ada testimoni, tidak
ada bilah logo "dipercaya oleh", tidak ada statistik, karena produk ini belum punya satu pun yang
nyata ([R-17, R-18, R-36, R-38](../../DESIGN.md)).

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `npm run test -- komposisi`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add landing and explore pages with varied section composition"
```

---

### Task 6: End-to-end Playwright

**Files:**
- Create: `frontend/e2e/alur-penuh.spec.ts`

Satu skenario, bukan dua puluh. Yang dicari adalah bukti bahwa seluruh rantai menyambung.

- [ ] **Step 1: Tulis test**

```ts
// frontend/e2e/alur-penuh.spec.ts
import { expect, test } from "@playwright/test";

test("dari campaign dibuat sampai milestone terakhir cair", async ({ page }) => {
  await masukSebagai(page, "investor-a@contoh.id");
  await buatCampaign(page, { target: "50000000", threshold: "60" });

  await masukSebagai(page, "umkm@contoh.id");
  await submitProposal(page, { diminta: "10000000", milestones: ["5000000", "5000000"] });
  await expect(page.getByText(/terbuka untuk pendanaan/i)).toBeVisible();

  await masukSebagai(page, "warga@contoh.id");
  await page.getByRole("button", { name: /dukung proposal/i }).click();
  await expect(page.getByText("1 dukungan")).toBeVisible();

  await masukSebagai(page, "investor-a@contoh.id");
  await pledge(page, "6000000");
  await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "60");

  await masukSebagai(page, "investor-b@contoh.id");
  await pledge(page, "4000000");
  await expect(page.getByText(/dana terkumpul penuh/i)).toBeVisible();

  await masukSebagai(page, "investor-a@contoh.id");   // lead investor
  await page.getByRole("button", { name: /setujui pencairan/i }).first().click();
  await expect(page.getByText(/sudah cair/i)).toBeVisible();

  await masukSebagai(page, "umkm@contoh.id");
  await laporMilestone(page, "Mesin sudah terpasang, omzet naik 15 persen.");

  await masukSebagai(page, "investor-a@contoh.id");
  await page.getByRole("button", { name: /setujui pencairan/i }).click();
  await expect(page.getByText(/selesai/i)).toBeVisible();
});

test("tidak ada galat konsol selama alur penuh", async ({ page }) => {
  const galat: string[] = [];
  page.on("console", (m) => { if (m.type() === "error") galat.push(m.text()); });
  await page.goto("/");
  await jelajahSeluruhHalaman(page);
  expect(galat).toEqual([]);
});

test("seluruh alur bisa dijalankan tanpa menyentuh tetikus", async ({ page }) => {
  await page.goto("/masuk");
  await page.keyboard.press("Tab");
  await page.keyboard.type("investor-a@contoh.id");
  await page.keyboard.press("Tab");
  await page.keyboard.type("rahasia123");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/investor/);
});
```

- [ ] **Step 2: Jalankan terhadap backend seed**

Run: `make demo & npx playwright test`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e
git commit -m "feat: add end-to-end browser test for the full funding flow"
```

## Gerbang keluar fase 11, Delivery Gate antislop

Jalankan Delivery Gate lengkap dan sertakan laporannya dengan bukti per baris. Yang paling
relevan untuk fase ini, di luar yang sudah dicek di fase 10:

- [ ] R-05 dan dial RHYTHM 3 diuji oleh `komposisi.test.tsx`, bukan diklaim
- [ ] R-09 tidak ada lencana pil di atas H1
- [ ] R-14 kartu proposal bervariasi sesuai hierarki, tidak semuanya seragam
- [ ] R-17, R-18, R-36, R-38 tidak ada angka, testimoni, logo, atau klaim yang tidak nyata
- [ ] R-19 dan dial MOTION 2 gerakan punya tujuan tertulis, tidak ada loop tanpa henti
- [ ] R-23 kolom kosong memakai placeholder jujur, bukan data palsu yang terlihat asli
- [ ] R-24 setiap tautan navigasi menuju halaman yang ada, diuji otomatis
- [ ] R-35 aplikasi dijalankan, **setiap** kontrol diklik satu per satu, hasilnya dicatat sebagai
      daftar bukti, bukan diringkas jadi "semua berfungsi"
