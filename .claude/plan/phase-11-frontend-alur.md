# Fase 11. Halaman dan alur

**Hasil:** seluruh flow bisa dijalankan lewat browser, dari membuat campaign sampai milestone cair.
Sembilan route di bawah ada semua, dan setiap komponen punya halaman tempat ia dirender.

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

## Pembagian stream

Fase ini dikerjakan empat stream paralel di worktree terpisah. Pembagiannya mengikuti
batas halaman, bukan batas komponen, supaya dua stream tidak pernah menulis file yang sama.

| Stream | Task | Route yang dihasilkan |
| --- | --- | --- |
| A | 1 sampai 4 | `/proposal/[id]` |
| B | 5 sampai 6 | `/jelajah`, `/investor/campaign`, `/investor/campaign/baru`, `/investor/campaign/[id]` |
| C | 7 sampai 9 | `/umkm/beranda`, `/umkm/proposal/baru`, `/umkm/milestone/[id]/lapor` |
| D | 10 sampai 12 | `/investor/milestone`, `/` , dan e2e seluruh alur |

Stream D dikerjakan **terakhir**, bukan paralel: ia memasang header bersama dan penjaga
route di `layout.tsx`, lalu menguji seluruh alur end-to-end. Keduanya mustahil sebelum
route lain ada.

`components/ui/StatusBadge.tsx` dan `components/AppHeader.tsx` dipakai ketiga stream awal.
Keduanya dibuat lebih dulu di main sebelum stream dibuka, supaya tiga stream tidak
membuat tiga versi berbeda dari komponen yang sama.

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

---

### Task 1: Panel skor AI

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

### Task 2: Bilah funding dan form pledge

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

### Task 3: Daftar komentar dan vote komunitas

**Satu keputusan yang diambil di layar ini:** apakah pembaca lain menilai proposal ini layak,
dan apakah saya ikut menyuarakannya.

**Files:**
- Create: `frontend/components/DaftarKomentar.tsx`, `frontend/components/FormKomentar.tsx`
- Test: `frontend/tests/komentar.test.tsx`

**Endpoint yang dipakai:**

| Aksi | Endpoint |
| --- | --- |
| Muat komentar | `GET /proposals/{id}/comments` |
| Kirim komentar | `POST /proposals/{id}/comments` |
| Vote | `POST /proposals/{id}/vote` |
| Hapus komentar sendiri | `DELETE /comments/{id}` |

**Interfaces:**
- Produces: `<DaftarKomentar proposalId={...} />` dan `<FormKomentar proposalId={...} onKirim={...} />`.
  Task 4 merender keduanya di dalam `proposal/[id]/page.tsx`.

Baca `.claude/prd/05-feature-komunitas.md` untuk aturan siapa boleh berkomentar, siapa boleh
vote, dan satu akun berapa vote. Spec itu yang mengikat, bukan dugaan.

- [ ] **Step 1: Tulis test yang gagal**

Tiga test, dan masing-masing harus bisa merah karena alasan yang berbeda:

1. Komentar kosong tidak terkirim, dan tombol kirim menolak submit dengan pesan yang
   dibaca pengguna lewat `role="alert"`.
2. Tombol vote yang sudah dipakai akun ini tampil sebagai sudah-dipilih lewat
   `aria-pressed="true"`, bukan lewat warna saja. Warna sendirian tidak terbaca pembaca layar.
3. Tombol hapus hanya muncul pada komentar milik akun yang sedang masuk. Test ini harus
   memakai dua komentar dari dua penulis berbeda, supaya ia tidak lolos hanya karena
   semua komentar kebetulan milik satu orang.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `cd frontend && npm run test -- komentar`
Expected: ketiganya FAIL karena komponennya belum ada. Catat outputnya.

- [ ] **Step 3: Implementasi**

Daftar komentar memakai `EmptyState`, `LoadingState`, dan `ErrorState` yang sudah ada dari
fase 10. Empty state-nya menyebut penyebab dan satu aksi: belum ada yang berkomentar, dan
tombolnya mengarahkan ke form di bawahnya.

Batasan design dari `DESIGN.md` yang paling mudah dilanggar di layar ini:

- Komentar adalah **teks naratif**, jadi lebarnya dibatasi `max-w-measure`. Bukan selebar layar.
- Vote **bukan** tempat aksen kuning. Aksen di halaman detail proposal sudah dipakai bilah
  funding dan tombol pledge. Vote memakai `--ink` dan `--line`.
- Tidak ada avatar hasil karangan, tidak ada foto profil default, tidak ada emoji. Nama
  penulis ditulis sebagai teks.
- Jumlah vote dan jumlah komentar adalah angka, jadi `tabular-nums`.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `cd frontend && npm run test -- komentar && npx tsc --noEmit && npm run lint`

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add community comments and voting on a proposal"
```

---

### Task 4: Halaman detail proposal

Layar terpenting di produk ini. Ia menampung empat komponen sekaligus, dan ialah satu-satunya
tempat uang berpindah dari sisi pengguna.

**Satu keputusan yang diambil di layar ini:** berapa yang masuk akal saya sanggupi, atau tidak
sama sekali.

**Files:**
- Create: `frontend/app/proposal/[id]/page.tsx`
- Test: `frontend/tests/proposal-detail.test.tsx`
- Test: `frontend/e2e/proposal-detail.spec.ts`

**Endpoint yang dipakai:**

| Bagian halaman | Endpoint |
| --- | --- |
| Identitas dan isi proposal | `GET /proposals/{id}` |
| Panel skor AI | `GET /proposals/{id}/scoring` |
| Bilah funding dan daftar pemberi dana | `GET /proposals/{id}/pledges` |
| Milestone yang direncanakan | `GET /proposals/{id}/milestones` |
| Komentar dan vote | `GET /proposals/{id}/comments` |
| Pledge | `POST /proposals/{id}/pledges` |
| Batalkan pledge sendiri | `DELETE /pledges/{id}` |

**Interfaces:**
- Consumes: `PanelSkor` (Task 1), `BilahFunding` dan `FormPledge` (Task 2),
  `DaftarKomentar` dan `FormKomentar` (Task 3), `LiniMilestone` (Task 10, boleh menyusul).
- Produces: route `/proposal/[id]`, yang dirujuk `KartuProposal` di Task 5.

**Urutan di halaman, dan kenapa urutannya begitu:**

1. Nominal yang diminta, besar dan tabular, dengan label kecil di atasnya. Ini motif
   identitas dari `DESIGN.md`: produk ini tentang uang yang berpindah, jadi angkanya
   dibaca lebih dulu.
2. Bilah funding, karena pertanyaan pertama investor adalah berapa yang sudah terkumpul.
3. Cerita usaha dan rencana pemakaian dana, dibatasi `max-w-measure` karena ini teks naratif.
4. Panel skor AI, lengkap dengan red flag dan evidence-nya.
5. Form pledge.
6. Milestone yang direncanakan.
7. Komentar.

**RHYTHM 3 berlaku di sini dan diuji.** Tujuh blok berurutan tidak boleh berpola sama.
Variasi yang tersedia menurut `DESIGN.md`: lebar penuh lawan terbatas, rata kiri lawan
tengah, satu kolom lawan dua kolom asimetris, dengan rule horizontal lawan tanpa.

- [ ] **Step 1: Tulis test yang gagal**

Empat test, masing-masing menyasar satu kegagalan nyata:

1. Proposal yang belum selesai di-scoring menampilkan panel skor dalam keadaan menunggu,
   bukan panel kosong dan bukan angka nol. Nol adalah skor yang sah, jadi menampilkan nol
   untuk "belum dinilai" adalah kebohongan pada pengguna.
2. Proposal yang sudah `funded` tidak menampilkan form pledge sama sekali, dan menyebut
   alasannya. Tombol yang pasti ditolak server adalah kontrol tanpa perilaku nyata.
3. Pledge yang melebihi sisa dana menampilkan pesan dari server apa adanya, termasuk sisa
   nominalnya, bukan pesan generik. Backend mengembalikan `409` dengan sisa itu (D-11).
4. Akun UMKM yang membuka proposalnya sendiri tidak melihat form pledge, dan melihat
   panel skornya. Akun investor melihat keduanya. Test ini harus memakai dua peran berbeda,
   supaya ia tidak lolos hanya karena satu peran kebetulan dipakai di semua kasus.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `cd frontend && npm run test -- proposal-detail`
Expected: keempatnya FAIL. Catat outputnya.

- [ ] **Step 3: Implementasi**

Setiap bagian punya tiga keadaannya sendiri, dan itu bagian dari design, bukan tambahan:
panel skor bisa menunggu, bilah funding bisa gagal dimuat, komentar bisa kosong. Satu
bagian gagal tidak boleh menjatuhkan seluruh halaman.

Anggaran aksen `DESIGN.md` di layar ini **tepat tiga** dan sudah penuh: bilah funding,
tombol pledge, dan penanda tahap milestone yang sedang berjalan. Tidak ada aksen keempat.

Angka rupiah di mana pun di halaman ini wajib `tabular-nums` dan diformat lewat
`lib/money.ts`. Tidak ada pemformatan rupiah yang ditulis ulang di tempat lain.

- [ ] **Step 4: Pagar RHYTHM 3**

```ts
// frontend/tests/proposal-detail.test.tsx, test tambahan
// Dua section berurutan tidak boleh berbagi pola komposisi yang sama.
// Pagar ini membaca atribut data-pola yang dipasang tiap section.
```

Pasang `data-pola` pada tiap section halaman dengan nilai yang menyebut polanya, lalu
assert tidak ada dua nilai bersebelahan yang sama. Buktikan pagar ini bisa merah dengan
menyamakan dua section berurutan, jalankan, lihat gagal, lalu pulihkan.

- [ ] **Step 5: Jalankan semuanya**

Run: `cd frontend && npm run test && npx tsc --noEmit && npm run lint && npm run build`

`npm run build` wajib ikut, bukan hanya `tsc`: kelas Tailwind yang salah nama tidak membuat
TypeScript mengeluh sama sekali, ia hanya menghasilkan halaman tanpa gaya.

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: add the proposal detail page with scoring, funding and pledging"
```

---

### Task 5: Halaman jelajah dan komposisi yang bervariasi

**Files:**
- Create: `frontend/app/jelajah/page.tsx`, `frontend/components/KartuProposal.tsx`
- Test: `frontend/tests/komposisi.test.tsx`

Dial **RHYTHM 3** berarti tidak boleh ada dua section berpola sama. Ini diuji, bukan diserahkan
ke ingatan.

- [ ] **Step 1: Tulis test yang gagal**

```tsx
// frontend/tests/komposisi.test.tsx
import { readFileSync } from "node:fs";

describe("RHYTHM 3 di landing page", () => {
  it("tidak ada dua section berurutan dengan pola komposisi yang sama", () => {
    const sumber = readFileSync("app/jelajah/page.tsx", "utf8");
    const pola = [...sumber.matchAll(/data-pola="([a-z-]+)"/g)].map((m) => m[1]);
    expect(pola.length).toBeGreaterThanOrEqual(4);
    pola.forEach((p, i) => {
      if (i > 0) expect(p).not.toBe(pola[i - 1]);
    });
  });

  it("setiap section menyatakan polanya secara eksplisit", () => {
    const sumber = readFileSync("app/jelajah/page.tsx", "utf8");
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

### Task 6: Halaman campaign milik investor

Tiga route sekaligus, karena ketiganya satu alur: melihat campaign saya, membuat yang baru,
lalu membaca proposal yang masuk ke salah satunya.

**Satu keputusan per layar:**

| Route | Keputusan |
| --- | --- |
| `investor/campaign` | Campaign mana yang perlu saya urus sekarang |
| `investor/campaign/baru` | Kriteria apa yang saya pasang untuk proposal yang masuk |
| `investor/campaign/[id]` | Proposal mana yang layak saya baca lebih dalam |

**Files:**
- Create: `frontend/app/investor/campaign/page.tsx`
- Create: `frontend/app/investor/campaign/baru/page.tsx`
- Create: `frontend/app/investor/campaign/[id]/page.tsx`
- Create: `frontend/components/FormCampaign.tsx`
- Test: `frontend/tests/campaign-pages.test.tsx`

**Endpoint yang dipakai:**

| Aksi | Endpoint |
| --- | --- |
| Campaign saya | `GET /campaigns` |
| Buat campaign | `POST /campaigns` |
| Ubah campaign | `PATCH /campaigns/{id}` |
| Tutup campaign manual | `POST /campaigns/{id}/close` |
| Proposal yang masuk | `GET /campaigns/{id}/proposals` |

**Interfaces:**
- Consumes: `KartuProposal` (Task 5), `Field` dan tiga komponen keadaan dari fase 10.
- Produces: route `/investor/campaign/[id]`, yang dirujuk Task 8 saat UMKM mengajukan proposal.

Baca `.claude/prd/03-feature-investor.md` untuk field campaign yang wajib dan aturan
`score_threshold`, dan `.claude/prd/08-state-machines.md` untuk transisi campaign
(`open` ke `closed`). Spec itu yang mengikat.

- [ ] **Step 1: Tulis test yang gagal**

Empat test:

1. Campaign dengan dua tenggat menampilkan keduanya dengan label yang membedakannya:
   tenggat pengajuan dan tenggat funding (D-16). Satu tenggat saja adalah cacat, bukan
   penyederhanaan.
2. Tombol tutup manual meminta konfirmasi sebelum memanggil server, dan konfirmasinya
   **bukan** `window.confirm`. Dialog bawaan browser memblokir seluruh event dan tidak
   bisa diuji; pakai elemen di halaman.
3. Campaign yang sudah `closed` tidak menampilkan tombol tutup, dan menyebut alasannya.
4. Form campaign menolak `score_threshold` di luar jangkauan yang dipatok spec, dengan
   pesan yang dibaca pengguna, sebelum request dikirim. Validasi yang hanya mengandalkan
   server membuat pengguna menunggu untuk kesalahan yang bisa diketahui saat itu juga.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `cd frontend && npm run test -- campaign-pages`
Expected: keempatnya FAIL. Catat outputnya.

- [ ] **Step 3: Implementasi**

Peringatan fase ini berlaku penuh di sini: **jangan bangun cangkang dashboard default.**
Tidak ada sidebar, tidak ada empat kartu statistik, tidak ada grafik. Daftar campaign
adalah daftar, dan tiap barisnya menjawab satu pertanyaan: apa yang perlu saya urus.

**Angka karangan dilarang.** Kalau sebuah angka belum tersambung ke data nyata, ia tidak
ditampilkan. Kartu statistik berisi angka hias adalah pelanggaran R-17 yang paling mudah
terjadi di layar seperti ini.

Form campaign memakai `Field` dari fase 10 untuk setiap input, supaya `htmlFor`,
`aria-describedby`, dan `aria-invalid` tidak perlu diingat ulang per field.

- [ ] **Step 4: Jalankan semuanya**

Run: `cd frontend && npm run test && npx tsc --noEmit && npm run lint && npm run build`

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add investor campaign list, creation and proposal inbox"
```

---

### Task 7: Form proposal dengan validasi milestone langsung

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

### Task 8: Beranda UMKM dan pengajuan proposal

**Satu keputusan per layar:**

| Route | Keputusan |
| --- | --- |
| `umkm/beranda` | Apa yang harus saya kerjakan sekarang |
| `umkm/proposal/baru` | Apakah pengajuan saya sudah cukup untuk dinilai |

**Files:**
- Create: `frontend/app/umkm/beranda/page.tsx`
- Create: `frontend/app/umkm/proposal/baru/page.tsx`
- Test: `frontend/tests/umkm-pages.test.tsx`

**Endpoint yang dipakai:**

| Aksi | Endpoint |
| --- | --- |
| Proposal saya | `GET /proposals/mine` |
| Campaign yang masih terbuka | `GET /campaigns` |
| Ajukan proposal | `POST /campaigns/{id}/proposals` |
| Skor proposal saya | `GET /proposals/{id}/scoring` |
| Minta nilai ulang | `POST /proposals/{id}/rescore` |

**Interfaces:**
- Consumes: `FormProposal` dan `RencanaMilestone` (Task 7), `PanelSkor` (Task 1),
  `KartuProposal` (Task 5), komponen keadaan fase 10.
- Produces: route `/umkm/beranda`, tujuan redirect setelah pengajuan berhasil.

Baca `.claude/prd/04-feature-umkm.md` untuk field proposal yang wajib dan panjang minimum
`fund_usage_plan`, dan `.claude/prd/11-ai-scoring-spec.md` untuk apa yang ditampilkan saat
scoring gagal secara teknis. **Kegagalan teknis bukan penolakan** (D-09), dan halaman ini
tidak boleh menampilkannya seolah proposalnya ditolak.

- [ ] **Step 1: Tulis test yang gagal**

Lima test:

1. Beranda yang belum punya proposal menampilkan empty state dengan satu aksi yang
   mengarah ke pengajuan, dan menyebut penyebabnya. Bukan "Tidak ada data".
2. Proposal yang scoring-nya gagal secara teknis menampilkan tombol nilai ulang dan
   **tidak** menampilkan kata yang berarti ditolak. Ini D-09, dan salah di sini berarti
   memberi tahu pemilik usaha bahwa usahanya ditolak padahal yang gagal adalah mesinnya.
3. Proposal yang sudah dinilai menampilkan skornya lewat `PanelSkor`, termasuk red flag.
4. Pengajuan ke campaign yang tenggat pengajuannya sudah lewat tidak bisa dikirim, dan
   menyebut alasannya sebelum request dikirim.
5. `fund_usage_plan` yang lebih pendek dari minimum spec ditolak dengan pesan yang
   menyebut berapa karakter lagi yang dibutuhkan, bukan pesan generik.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `cd frontend && npm run test -- umkm-pages`
Expected: kelimanya FAIL. Catat outputnya.

- [ ] **Step 3: Implementasi**

Beranda UMKM adalah layar yang paling mudah jatuh jadi cangkang dashboard default. Lawannya
ada di `DESIGN.md`: sebut dulu satu keputusan, lalu bangun hierarki di sekitarnya. Di sini
keputusannya "apa yang harus saya kerjakan sekarang", jadi yang paling atas adalah hal yang
menunggu tindakan pemilik usaha, bukan ringkasan angka.

Formulir pengajuan panjang, dan itu alasan `DESIGN.md` memilih sans humanis. Lebar baris
teks naratif dibatasi, tapi form dan tabel boleh lebih lebar.

- [ ] **Step 4: Jalankan semuanya**

Run: `cd frontend && npm run test && npx tsc --noEmit && npm run lint && npm run build`

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add the UMKM home page and proposal submission flow"
```

---

### Task 9: Pelaporan milestone oleh UMKM

**Satu keputusan yang diambil di layar ini:** apakah laporan saya sudah cukup untuk diajukan.

**Files:**
- Create: `frontend/app/umkm/milestone/[id]/lapor/page.tsx`
- Test: `frontend/tests/milestone-lapor.test.tsx`

**Endpoint yang dipakai:**

| Aksi | Endpoint |
| --- | --- |
| Milestone proposal saya | `GET /proposals/{id}/milestones` |
| Kirim laporan | `POST /milestones/{id}/reports` |

**Interfaces:**
- Consumes: `Field` dan komponen keadaan fase 10, `LiniMilestone` (Task 10, boleh menyusul).
- Produces: route `/umkm/milestone/[id]/lapor`.

Baca `.claude/prd/07-business-rules.md` BR-40 sampai BR-48 dan `.claude/docs/decisions.md`
D-13. Dua aturan yang paling mudah salah di layar ini:

- **Milestone pertama tidak butuh laporan, tapi tetap butuh persetujuan** (D-13). Halaman
  ini tidak boleh meminta laporan untuk milestone pertama, dan tidak boleh menyiratkan
  bahwa tanpa laporan ia cair sendiri.
- Milestone berikutnya hanya boleh dilaporkan kalau yang sebelumnya sudah cair. Prasyarat
  itu ditampilkan sebagai alasan, bukan sebagai tombol mati tanpa penjelasan.

- [ ] **Step 1: Tulis test yang gagal**

Tiga test:

1. Milestone pertama tidak menampilkan form laporan, dan menyebut bahwa ia hanya menunggu
   persetujuan. Test ini harus memeriksa `seq=1` dan `seq=2` sekaligus, supaya ia tidak
   lolos hanya karena kebetulan semua milestone diperlakukan sama.
2. Milestone yang prasyaratnya belum terpenuhi menampilkan penyebabnya, dan form-nya tidak
   bisa dikirim.
3. Laporan yang sudah dikirim dan sedang menunggu review tidak bisa dikirim ulang, dan
   menyebut statusnya.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `cd frontend && npm run test -- milestone-lapor`
Expected: ketiganya FAIL. Catat outputnya.

- [ ] **Step 3: Implementasi**

Status yang perlu tindakan memakai `--warn` sesuai `DESIGN.md`, bukan aksen kuning. Aksen
di layar ini hanya boleh dipakai penanda tahap yang sedang berjalan.

- [ ] **Step 4: Jalankan semuanya**

Run: `cd frontend && npm run test && npx tsc --noEmit && npm run lint && npm run build`

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add milestone reporting for UMKM owners"
```

---

### Task 10: Lini milestone dan alur persetujuan

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

### Task 11: Header bersama, penjaga auth, dan landing page

Task penjahitan. Ia dikerjakan setelah route lain ada, karena ia yang menyambungkan semuanya
dan tidak bisa diuji sebelum ada yang disambungkan.

**Files:**
- Create: `frontend/components/AppHeader.tsx`, `frontend/components/NavPeran.tsx`
- Create: `frontend/lib/auth.ts`
- Modify: `frontend/app/layout.tsx`, `frontend/app/page.tsx`
- Test: `frontend/tests/header-auth.test.tsx`, `frontend/e2e/auth-guard.spec.ts`

**Endpoint yang dipakai:** `GET /auth/me` untuk mengetahui peran akun yang sedang masuk.

**Interfaces:**
- Consumes: `ThemeToggle` (fase 10), `lib/api.ts`.
- Produces: `AppHeader` yang dirender di `layout.tsx` sehingga muncul di seluruh route,
  dan `lib/auth.ts` yang mengekspos peran akun untuk setiap halaman yang perlu membedakannya.

**Tiga hal yang task ini selesaikan:**

1. **`ThemeToggle` baru ada di satu halaman.** Sampai sekarang ia hanya dirender di `/`, jadi
   siapa pun yang membuka halaman lain langsung tidak bisa mengubah tema di sana. Begitu
   header ini ada, ia hadir di seluruh route, dan ini pula alasan temuan itu ditunda ke sini
   alih-alih ditambal per halaman.
2. **Tidak ada penjaga route.** Investor bisa membuka halaman UMKM dan sebaliknya, dan akun
   yang belum masuk bisa membuka halaman yang butuh token. Server menolaknya dengan 401, tapi
   pengguna melihat halaman rusak alih-alih diarahkan.
3. **Landing page masih sementara.** `app/page.tsx` sekarang berisi placeholder jujur yang
   dibuat hanya supaya `next build` bisa jalan untuk pertama kali.

- [ ] **Step 1: Tulis test yang gagal**

Enam test:

1. Header tampil di setiap route, dan `ThemeToggle` di dalamnya. Test ini merender tiga
   route berbeda, bukan satu, supaya ia tidak lolos karena kebetulan.
2. Akun belum masuk yang membuka route terlindungi diarahkan ke `/masuk`, dan setelah masuk
   dibawa kembali ke halaman yang semula dituju. Membuang tujuan asal membuat pengguna
   mengulang navigasinya.
3. Akun investor yang membuka route UMKM mendapat **404, bukan 403.** Ini mengikuti pola
   yang sudah dipakai backend: 403 memberi tahu bahwa sumber dayanya ada.
4. Nav menampilkan tautan yang berbeda untuk investor dan untuk UMKM, dan **tidak ada satu
   pun tautan yang mengarah ke route yang tidak ada.** Navigasi mati adalah cacat (R-24).
5. Keluar dari akun menghapus token dan mengarahkan ke `/`. Setelah itu route terlindungi
   kembali mengarahkan ke `/masuk`.
6. Token yang tidak sah di localStorage tidak membuat aplikasi macet: ia diperlakukan sama
   dengan belum masuk. Nilai `"undefined"` yang pernah tersimpan karena bug fase 10 adalah
   kasus nyata yang harus lewat test ini.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `cd frontend && npm run test -- header-auth`
Expected: keenamnya FAIL. Catat outputnya.

- [ ] **Step 3: Pagar navigasi mati**

```ts
// frontend/tests/header-auth.test.tsx, test tambahan
// Setiap href di nav harus cocok dengan satu route yang benar-benar ada di app/.
// Pagar ini membaca daftar route dari filesystem, bukan dari daftar yang ditulis tangan,
// supaya route yang dihapus ikut tertangkap.
```

Kumpulkan route dari `app/**/page.tsx` lewat filesystem, lalu assert setiap `href` di nav
cocok dengan salah satunya. Buktikan pagar ini bisa merah dengan menambahkan satu tautan
ke route karangan, jalankan, lihat gagal, lalu pulihkan.

- [ ] **Step 4: Landing page sungguhan**

Ganti placeholder `app/page.tsx`. `DESIGN.md` memberi landing page dial ENERGY 2, jadi ia
punya karakter kuat, sementara dashboard tetap tenang.

Yang **tidak boleh** ada di halaman ini, dan masing-masing adalah aturan tertulis:

- Angka statistik, testimoni, dan baris logo. Produk ini tidak punya satu pun, dan
  mengarangnya melanggar aturan lomba sekaligus R-18 dan R-36.
- Badge kapsul di atas H1, titik status hias, ikon sparkle atau robot.
- Gradien biru ke ungu, grid latar, bayangan di setiap komponen.
- H1 berisi nama merek. Nama produk sudah ada di header; H1 menyampaikan apa yang produk
  ini lakukan.

**RHYTHM 3 diuji di halaman ini.** Tidak boleh ada dua section berurutan berpola sama.
Pakai pola `data-pola` yang sama dengan Task 4, dan pagar yang sama.

- [ ] **Step 5: Jalankan semuanya**

Run: `cd frontend && npm run test && npx tsc --noEmit && npm run lint && npm run build && npx playwright test`

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: add the shared header, route guards and the real landing page"
```

---

### Task 12: End-to-end Playwright

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

---

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
