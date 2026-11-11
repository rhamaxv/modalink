import { expect, test, type Page } from "@playwright/test";

// Pelengkap e2e/alur-penuh.spec.ts, bukan pengulangannya.
//
// Berkas itu membuktikan jalur BAHAGIA menyambung dari ujung ke ujung: satu
// campaign, satu proposal, satu pendana, semuanya berhasil. Berkas ini
// menjalankan yang berantakan, karena di situlah bug sungguhan hidup:
//
//   - dua UMKM bersaing di campaign yang sama, salah satunya ditolak AI
//   - pledge yang melebihi sisa dana
//   - pledge yang dibatalkan setelah proposal sempat penuh
//   - penyaring, pengurutan, dan hitungan di halaman jelajah terhadap data
//     yang baru saja dibuat test ini sendiri
//   - batas peran: siapa TIDAK boleh melakukan apa
//
// Semuanya lewat klik dan ketikan sungguhan terhadap backend asli.
test.describe("alur pasar: dua UMKM bersaing, satu dibatalkan, dua tahap cair", () => {
  test.describe.configure({ mode: "serial" });

  const RUN = Date.now().toString(36);

  // Akun demo yang sudah disemai dipakai ulang, bukan didaftarkan baru.
  //
  // Alasannya ditemukan oleh test ini sendiri: POST /auth/register dibatasi
  // 5 per menit per IP (app/middleware.py), dan beforeAll yang mendaftarkan
  // lima akun sekaligus langsung menabrak batas itu -- pagar yang memang
  // benar, dan test yang harus hidup di dalamnya, bukan sebaliknya. Memakai
  // akun demo juga berarti alur ini menguji akun yang SUNGGUH dipakai juri.
  const DEMO = "Demo#Modalink2026";
  const investorA = { email: "investor1@demo.example.com", password: DEMO, name: "Hendra Wijaya (Demo)" };
  const investorB = { email: "investor2@demo.example.com", password: DEMO, name: "Siti Rahayu (Demo)" };
  const umkmLolos = { email: "umkm3@demo.example.com", password: DEMO, name: "Eka Nurhayati (Demo)" };
  const umkmDitolak = { email: "umkm4@demo.example.com", password: DEMO, name: "Rizki Pratama (Demo)" };
  // Satu-satunya akun yang didaftarkan: peran komunitas tidak ikut disemai.
  const warga = { email: `pasar-warga-${RUN}@contoh.id`, password: "rahasia123", name: "Warga Sekitar" };

  const judulCampaign = `Kerajinan Tenun Nusantara ${RUN}`;
  const usahaLolos = `Tenun Ikat Sumba ${RUN}`;
  const usahaDitolak = `Warung Tanpa Rencana ${RUN}`;

  let idCampaign = "";
  let idProposal = "";

  // Satu BrowserContext per pelaku, masing-masing masuk sekali saja.
  //
  // Versi pertama spec ini memakai satu halaman bersama dan keluar-masuk
  // akun di tiap langkah, dan itu menabrak rate limiter login (10 per menit
  // per IP, app/middleware.py) begitu dijalankan berurutan dengan
  // alur-penuh.spec.ts. Pagar itu benar dan tidak boleh dilemahkan demi
  // test. Lagipula bentuk ini lebih mirip kejadian sungguhan: empat orang
  // berbeda di browser masing-masing, bukan satu orang yang login dan
  // logout lima belas kali dalam dua menit.
  const halaman: Record<string, Page> = {};

  // PNG 1x1 sungguhan, dipakai menguji unggah sampul lewat input berkas
  // sungguhan. Bukan berkas karangan: ia benar-benar bisa dibuka, dan
  // byte awalnya itulah yang diperiksa server (services/cover.py).
  const PNG = Buffer.from(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000" +
      "01f15c4890000000a49444154789c6300010000050001" +
      "0d0a2db40000000049454e44ae426082",
    "hex",
  );

  function tanggal(tambahHari: number): string {
    const d = new Date();
    d.setDate(d.getDate() + tambahHari);
    return d.toISOString().slice(0, 10);
  }


  // Rate limiter backend membatasi pendaftaran 5 per menit dan login 10 per
  // menit per IP (app/middleware.py). Dua spec alur panjang di folder ini
  // berjalan berurutan dalam menit yang sama dan bersama-sama melewatinya.
  // Pagarnya benar dan tidak boleh dilemahkan demi test, jadi yang menunggu
  // adalah test-nya, persis seperti yang dilakukan pengguna sungguhan.
  async function tungguKalauDibatasi(page: Page): Promise<boolean> {
    const dibatasi = page.getByText(/terlalu banyak permintaan/i);
    if (!(await dibatasi.isVisible().catch(() => false))) return false;
    await page.waitForTimeout(61_000);
    return true;
  }

  async function daftar(page: Page, akun: { email: string; password: string; name: string }, peran: string) {
    await page.goto("/daftar");
    await page.getByLabel("Nama").fill(akun.name);
    await page.getByLabel("Email").fill(akun.email);
    await page.getByLabel("Password").fill(akun.password);
    await page.getByLabel("Peran").selectOption(peran);
    await page.getByRole("button", { name: "Daftar" }).click();
    if (await tungguKalauDibatasi(page)) {
      await page.getByRole("button", { name: "Daftar" }).click();
    }
    await page.waitForURL((url) => url.pathname === "/");
  }

  async function masuk(page: Page, akun: { email: string; password: string }) {
    await page.goto("/");
    const keluar = page.getByRole("button", { name: /keluar/i });
    if (await keluar.isVisible().catch(() => false)) {
      await keluar.click();
      await page.waitForURL("/");
    }
    await page.goto("/masuk");
    await page.getByLabel("Email").fill(akun.email);
    await page.getByLabel("Password").fill(akun.password);
    await page.getByRole("button", { name: "Masuk", exact: true }).click();
    if (await tungguKalauDibatasi(page)) {
      await page.getByRole("button", { name: "Masuk", exact: true }).click();
    }
    await page.waitForURL((url) => url.pathname !== "/masuk");
  }

  // Scoring berjalan sebagai background task, jadi statusnya berubah setelah
  // 201 dikembalikan. Memuat ulang adalah yang sungguh dilakukan pengguna
  // yang menunggu.
  async function tungguTeks(page: Page, pola: RegExp, batasMs = 25_000) {
    const mulai = Date.now();
    for (;;) {
      if (await page.getByText(pola).first().isVisible().catch(() => false)) return;
      if (Date.now() - mulai > batasMs) break;
      await page.waitForTimeout(500);
      await page.reload();
    }
    await expect(page.getByText(pola).first()).toBeVisible();
  }

  async function isiProposal(
    page: Page,
    nama: string,
    nominal: string,
    skor: number,
    tahap: [string, string],
  ) {
    await page.goto("/umkm/proposal/baru");
    await page.getByLabel("Nama usaha").fill(nama);
    await page.getByLabel("Profil usaha").fill(
      `${nama} adalah usaha rumahan yang sudah berjalan beberapa tahun dan melayani pelanggan ` +
        "tetap setiap minggu dengan kualitas yang konsisten dan harga yang terjangkau warga sekitar.",
    );
    await page.getByLabel("Jumlah dana yang diminta").fill(nominal);
    // [[SCORE:n]] hanya dikenali MockScoringEngine, jadi skornya deterministik
    // dan test ini tidak bergantung pada heuristik panjang teks.
    await page.getByLabel("Rencana penggunaan dana").fill(
      `Dana dipakai untuk menambah peralatan produksi dan memperluas distribusi ke kota ` +
        `terdekat dalam enam bulan ke depan. [[SCORE:${skor}]]`,
    );
    await page.getByLabel("Proyeksi usaha").fill(
      "Omzet diproyeksikan naik bertahap setiap kuartal seiring bertambahnya kapasitas produksi.",
    );
    await page.getByLabel("Judul tahap 1").fill("Peralatan produksi");
    await page.getByLabel("Rincian tahap 1").fill("Membeli peralatan produksi dan memasangnya di lokasi usaha.");
    await page.getByLabel("Nominal tahap 1").fill(tahap[0]);
    await page.getByLabel("Judul tahap 2").fill("Distribusi");
    await page.getByLabel("Rincian tahap 2").fill("Mendistribusikan produk ke kota terdekat.");
    await page.getByLabel("Nominal tahap 2").fill(tahap[1]);
    await page.getByRole("button", { name: "Kirim proposal" }).click();
    await page.waitForURL(/\/umkm\/beranda/);
  }

  test.beforeAll(async ({ browser }, testInfo) => {
    testInfo.setTimeout(400_000);
    const aktor: [string, { email: string; password: string; name: string }, boolean][] = [
      ["investorA", investorA, false],
      ["investorB", investorB, false],
      ["umkmLolos", umkmLolos, false],
      ["umkmDitolak", umkmDitolak, false],
      ["warga", warga, true],
    ];
    for (const [nama, akun, perluDaftar] of aktor) {
      const ctx = await browser.newContext();
      const page = await ctx.newPage();
      if (perluDaftar) await daftar(page, akun, "community");
      else await masuk(page, akun);
      halaman[nama] = page;
    }
  });

  test.afterAll(async () => {
    for (const page of Object.values(halaman)) await page.context().close();
  });

  test("investor membuat campaign, memasang sampulnya, dan campaign itu muncul di jelajah", async () => {
    test.setTimeout(120_000);
    const inv = halaman.investorA!;
    await inv.goto("/investor/campaign/baru");
    await inv.getByLabel("Judul campaign").fill(judulCampaign);
    await inv.getByLabel("Deskripsi").fill(
      "Campaign untuk mendanai perajin tenun ikat yang sudah berproduksi dan butuh modal untuk " +
        "menambah alat tenun serta memperluas pemasaran ke luar daerah.",
    );
    await inv.getByLabel("Sektor").selectOption("kerajinan");
    await inv.getByLabel("Dana target (Rp)").fill("50000000");
    await inv.getByLabel("Tenggat pengajuan proposal").fill(tanggal(7));
    await inv.getByLabel("Tenggat funding").fill(tanggal(30));
    await inv.getByLabel("Ambang skor minimum (0-100)").fill("60");
    await inv.getByRole("button", { name: "Buat campaign" }).click();

    const pola = /\/investor\/campaign\/([0-9a-f-]{36})$/i;
    await inv.waitForURL(pola);
    idCampaign = inv.url().match(pola)![1]!;

    // Unggah sampul lewat input berkas sungguhan.
    await expect(inv.getByRole("heading", { name: "Foto sampul" })).toBeVisible();
    await inv.setInputFiles('input[type="file"]', {
      name: "sampul.png",
      mimeType: "image/png",
      buffer: PNG,
    });
    await expect(inv.getByRole("button", { name: /hapus foto/i })).toBeVisible({ timeout: 20_000 });

    // Campaign baru harus bisa ditemukan publik lewat penyaring sektornya.
    await inv.goto("/jelajah");
    await inv.getByRole("tab", { name: /campaign/i }).click();
    // Dipersempit ke panel yang sedang terlihat: kedua panel tab tetap
    // terpasang di DOM supaya berpindah tab tidak memicu fetch ulang, jadi
    // ada dua select berlabel "Sektor". Yang tersembunyi memakai display:none
    // sehingga pembaca layar mengabaikannya; locator berbasis DOM tidak.
    const panel = inv.getByRole("tabpanel");
    await panel.getByLabel("Sektor").selectOption("kerajinan");
    await expect(inv.getByRole("link", { name: new RegExp(judulCampaign, "i") })).toBeVisible();

    // Dan TIDAK muncul di sektor lain: penyaringnya harus benar-benar
    // menyaring, bukan sekadar mengubah label.
    await panel.getByLabel("Sektor").selectOption("kuliner");
    await expect(inv.getByRole("link", { name: new RegExp(judulCampaign, "i") })).toHaveCount(0);
  });

  test("dua UMKM mengajukan, yang skornya di bawah ambang ditolak dan tidak pernah tampil publik", async () => {
    test.setTimeout(150_000);

    const lolos = halaman.umkmLolos!;
    await isiProposal(lolos, usahaLolos, "10000000", 90, ["6000000", "4000000"]);
    await tungguTeks(lolos, /terbuka untuk pendanaan/i);

    const ditolak = halaman.umkmDitolak!;
    await isiProposal(ditolak, usahaDitolak, "8000000", 40, ["4000000", "4000000"]);
    await tungguTeks(ditolak, /tidak lolos penilaian/i);
    // Pemiliknya sendiri tetap melihat proposalnya yang ditolak.
    // Dipersempit ke sel tabelnya: nama usaha yang sama juga muncul di
    // dalam kalimat daftar periksa ("Profil usaha X terisi."), jadi
    // pencocokan teks polos menemukan dua elemen.
    await expect(ditolak.getByRole("cell", { name: usahaDitolak })).toBeVisible();

    // Publik tidak: GET /proposals hanya mengirim listed ke atas.
    const w = halaman.warga!;
    await w.goto("/jelajah");
    await expect(w.getByRole("link", { name: new RegExp(usahaLolos, "i") })).toBeVisible();
    await expect(w.getByRole("link", { name: new RegExp(usahaDitolak, "i") })).toHaveCount(0);

    // Warga mendukung proposal yang lolos.
    await w.getByRole("link", { name: new RegExp(usahaLolos, "i") }).first().click();
    await w.waitForURL(/\/proposal\//);
    idProposal = w.url().split("/proposal/")[1]!.split("?")[0]!;
    await w.getByRole("button", { name: /dukung proposal ini/i }).click();
    await expect(w.getByText("1 dukungan")).toBeVisible();
  });

  test("nominal yang melebihi sisa dicegat sebelum dikirim, dan pesannya menyebut sisanya", async () => {
    test.setTimeout(120_000);

    const a = halaman.investorA!;
    await a.goto(`/proposal/${idProposal}`);
    await a.getByLabel("Nominal pledge (Rp)").fill("6000000");
    await a.getByRole("button", { name: /danai/i }).click();
    await expect(a.getByText(/sisa Rp4\.000\.000/i)).toBeVisible({ timeout: 20_000 });

    const b = halaman.investorB!;
    await b.goto(`/proposal/${idProposal}`);
    // Sisa tinggal 4 juta. Nominal yang melebihi sisa dicegat di klien
    // SEBELUM dikirim: tombolnya dinonaktifkan, bukan permintaan yang
    // dilempar lalu ditolak 409. Yang dijaga di sini adalah pesannya
    // menyebut ANGKA sisanya; tanpa itu investor menghadapi tombol mati dan
    // harus menebak berapa yang boleh dimasukkan.
    await b.getByLabel("Nominal pledge (Rp)").fill("5000000");
    await expect(b.getByText(/sisa dana yang dibutuhkan tinggal/i)).toContainText("4.000.000");
    await expect(b.getByRole("button", { name: /danai/i })).toBeDisabled();

    // Nominal yang muat diterima, tapi proposalnya BELUM penuh: pembatalan
    // diuji di test berikutnya, dan kontrak melarangnya begitu proposal
    // funded (409), jadi urutannya memang harus begini.
    await b.getByLabel("Nominal pledge (Rp)").fill("2000000");
    await b.getByRole("button", { name: /danai/i }).click();
    await expect(b.getByText(/sisa Rp2\.000\.000/i)).toBeVisible({ timeout: 20_000 });
  });

  test("investor bisa membatalkan pledge-nya sendiri selama proposal belum penuh", async () => {
    test.setTimeout(120_000);

    // Endpoint DELETE /pledges/{id} sudah ada di kontrak dan di backend sejak
    // lama, tapi sampai alur ini dijalankan tidak ada SATU PUN jalan ke sana
    // dari antarmuka: investor yang salah memasukkan nominal tidak punya cara
    // membatalkannya sendiri.
    const b = halaman.investorB!;
    await b.goto(`/proposal/${idProposal}`);
    await b.getByRole("button", { name: /^batalkan$/i }).first().click();
    // Ditunggu lewat SISA-nya, bukan lewat nominal terkumpul: "Rp6.000.000"
    // sudah tertulis di layar sebelum pembatalan sebagai nominal pendana
    // ke-1, jadi menunggu teks itu lolos seketika dan langkah berikutnya
    // mengisi nominal ketika sisa masih angka lama.
    await expect(b.getByText(/sisa Rp4\.000\.000/i)).toBeVisible({ timeout: 20_000 });
    await expect(b.getByText(/pendana ke-2/i)).toHaveCount(0);

    // Pembatalan mengembalikan sisa, jadi 4 juta kini muat dan proposal penuh.
    await b.getByLabel("Nominal pledge (Rp)").fill("4000000");
    await b.getByRole("button", { name: /danai/i }).click();
    await tungguTeks(b, /dana terpenuhi/i);

    // Dan begitu penuh, tombol batalkan tidak ditawarkan lagi: kontrak
    // membalas 409 untuk proposal yang sudah funded.
    await expect(b.getByRole("button", { name: /^batalkan$/i })).toHaveCount(0);
  });

  test("pledge milik investor lain tidak pernah bisa dibatalkan dari layar ini", async () => {
    test.setTimeout(90_000);
    // Investor A melihat kedua pledge, tapi identitas pemberi dana lain
    // disamarkan backend, jadi tidak ada yang bisa dikenali apalagi
    // dibatalkan. Proposal juga sudah penuh di titik ini.
    const a = halaman.investorA!;
    await a.goto(`/proposal/${idProposal}`);
    await expect(a.getByText(/pendana ke-/i).first()).toBeVisible();
    await expect(a.getByRole("button", { name: /^batalkan$/i })).toHaveCount(0);
  });

  test("tahap 1 cair tanpa laporan, tahap 2 butuh laporan dulu, keduanya disetujui lead investor", async () => {
    test.setTimeout(180_000);

    // BR-41: milestone seq=1 TIDAK memerlukan laporan progres, tapi tetap
    // butuh persetujuan lead investor sebelum cair. Jadi urutannya memang
    // berbeda antara tahap pertama dan tahap sesudahnya, dan alur ini
    // menjalankan keduanya apa adanya, bukan memaksa keduanya seragam.
    const a = halaman.investorA!;
    await a.goto("/investor/milestone");
    await a.getByRole("button", { name: /setujui/i }).first().click();
    await expect(a.getByRole("button", { name: /setujui/i })).toHaveCount(0, { timeout: 25_000 });

    // Tahap 2 baru muncul sebagai "perlu keputusan" setelah UMKM melapor.
    const u = halaman.umkmLolos!;
    await u.goto(`/proposal/${idProposal}`);
    await u.getByRole("link", { name: /lapor progres/i }).first().click();
    await u.waitForURL(/\/lapor/);
    await u.getByLabel(/laporan progres/i).fill(
      "Tahap kedua sudah selesai dikerjakan sesuai rencana, dengan bukti pembelian dan foto " +
        "kegiatan yang sudah disimpan oleh pemilik usaha.",
    );
    await u.getByRole("button", { name: /kirim laporan/i }).click();
    // Halaman ini TIDAK berpindah setelah laporan terkirim: ia tetap di
    // tempat dan berganti ke keadaan menunggu review.
    await expect(u.getByText(/menunggu review lead investor/i)).toBeVisible({ timeout: 25_000 });

    await a.goto("/investor/milestone");
    await a.getByRole("button", { name: /setujui/i }).first().click();
    await expect(a.getByRole("button", { name: /setujui/i })).toHaveCount(0, { timeout: 25_000 });

    // Kedua tahap cair berarti seluruh dana sudah sampai ke UMKM.
    await a.goto(`/proposal/${idProposal}`);
    await tungguTeks(a, /selesai/i);
  });

  test("batas peran ditegakkan di layar, bukan hanya di server", async () => {
    test.setTimeout(90_000);

    // UMKM tidak pernah ditawari form pendanaan.
    const u = halaman.umkmLolos!;
    await u.goto(`/proposal/${idProposal}`);
    await expect(u.getByLabel("Nominal pledge (Rp)")).toHaveCount(0);

    // Investor tidak punya jalan ke form pengajuan proposal.
    const a = halaman.investorA!;
    await a.goto("/umkm/proposal/baru");
    await expect(a.getByRole("button", { name: "Kirim proposal" })).toHaveCount(0);

    // Komunitas tidak punya keduanya, tapi tetap bisa mendukung.
    const w = halaman.warga!;
    await w.goto(`/proposal/${idProposal}`);
    await expect(w.getByLabel("Nominal pledge (Rp)")).toHaveCount(0);
    await expect(
      w.getByRole("button", { name: /dukung proposal ini|dukungan anda tercatat/i }),
    ).toHaveCount(1);
  });
});
