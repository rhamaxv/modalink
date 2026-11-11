import { expect, test, type Browser, type Page } from "@playwright/test";

// Satu skenario, bukan dua puluh (brief Fase 11 Task 12): test ini
// menjalankan seluruh rantai Modalink lewat klik dan ketikan sungguhan,
// terhadap backend ASLI (bukan page.route() seperti e2e/proposal-detail.spec.ts
// dan e2e/auth-guard.spec.ts). Tujuannya membuktikan frontend dan backend
// sungguh menyambung, bukan hanya sama-sama konsisten dengan kontrak yang
// ditulis manusia secara independen.
//
// Tidak ada POST /internal/seed untuk dipakai: endpoint itu ada di
// 10-api-contract.md tapi tidak pernah diimplementasikan di
// backend/app/api/v1/internal.py (hanya clock/tick dan ledger ada). Jadi
// keempat akun demo di bawah didaftarkan lewat /daftar sungguhan sekali di
// beforeAll, bukan lewat seed yang tidak ada atau lewat panggilan API
// langsung yang menyamar sebagai klik (lihat laporan Fase 11 Task 12 untuk
// rincian kenapa ini diputuskan begini).
//
// Mode serial dipasang eksplisit: ketiga test di file ini berbagi state yang
// dibangun berurutan (satu proposal yang bergerak dari submitted sampai
// completed), dan playwright.config.ts menyalakan fullyParallel secara
// global untuk seluruh folder e2e/. Tanpa serial, Playwright bebas
// menyebar test-test ini ke worker berbeda, yang akan membuat beforeAll
// berjalan lebih dari sekali dengan akun acak yang berbeda-beda.
test.describe("alur penuh: dari campaign dibuat sampai milestone terakhir cair", () => {
  test.describe.configure({ mode: "serial" });

  // RUN_ID membuat setiap jalannya test ini memakai email dan judul yang
  // unik, supaya menjalankan ulang test ini terhadap database yang belum
  // direset (tidak dibersihkan di antara percobaan debug) tidak pernah
  // tabrakan dengan "email_terpakai" dari percobaan sebelumnya.
  const RUN_ID = Date.now().toString(36);

  const investorA = { email: `investor-a-${RUN_ID}@contoh.id`, password: "rahasia123", name: "Investor Satu" };
  const investorB = { email: `investor-b-${RUN_ID}@contoh.id`, password: "rahasia123", name: "Investor Dua" };
  const umkm = { email: `umkm-${RUN_ID}@contoh.id`, password: "rahasia123", name: "Pemilik Warung" };
  const warga = { email: `warga-${RUN_ID}@contoh.id`, password: "rahasia123", name: "Warga Sekitar" };

  const campaignTitle = `Kuliner Rakyat Nusantara ${RUN_ID}`;
  const businessName = `Kopi Rakyat Nusantara ${RUN_ID}`;

  // Diisi berurutan sepanjang test pertama berjalan, lalu dipakai ulang oleh
  // dua test berikutnya di file ini (mode serial menjamin urutannya).
  let campaignId = "";
  let proposalId = "";
  let milestone2Id = "";

  function tanggal(hariDariSekarang: number): string {
    const d = new Date();
    d.setDate(d.getDate() + hariDariSekarang);
    return d.toISOString().slice(0, 10);
  }

  async function daftarSebagai(
    page: Page,
    akun: { email: string; password: string; name: string },
    peran: "investor" | "umkm" | "community",
  ) {
    await page.goto("/daftar");
    await page.getByLabel("Nama").fill(akun.name);
    await page.getByLabel("Email").fill(akun.email);
    await page.getByLabel("Password").fill(akun.password);
    await page.getByLabel("Peran").selectOption(peran);
    await page.getByRole("button", { name: "Daftar" }).click();
    // SignUpForm mendaftar lalu auto-masuk dan mendorong ke "/" (lib/
    // components/SignUpForm.tsx); menunggu URL ini memastikan daftar
    // sungguhan selesai, bukan menebak lewat waktu tunggu tetap.
    await page.waitForURL((url) => url.pathname === "/");
  }

  // Dipakai berkali-kali untuk berganti akun di tengah skenario: menu
  // "Keluar" di AppHeader cuma menghapus token di klien (lib/auth.ts), jadi
  // keluar dulu sebelum masuk sebagai akun lain mencegah token lama ikut
  // terbawa ke permintaan berikutnya.
  // Token per akun, disimpan setelah login UI pertama yang sungguhan.
  //
  // Skenario ini berpindah akun sebelas kali, dan POST /auth/login dibatasi
  // 10 per menit per IP (app/middleware.py). Dijalankan utuh, spec ini
  // menabrak batasnya sendiri dan gagal dengan "Terlalu banyak permintaan"
  // yang tidak ada hubungannya dengan apa yang sedang diuji. Pagar itu benar
  // dan tidak boleh dilemahkan demi test.
  //
  // Jadi login lewat FORM tetap terjadi sekali untuk tiap akun -- alur masuk
  // sungguhan tetap diuji, termasuk oleh test keyboard di bawah file ini --
  // dan perpindahan berikutnya memulihkan token yang sudah didapat, persis
  // seperti sesi yang masih hidup di browser yang sama.
  const sesi = new Map<string, string>();

  async function masukSebagai(page: Page, akun: { email: string; password: string }) {
    await page.goto("/");
    const tombolKeluar = page.getByRole("button", { name: /keluar/i });
    if (await tombolKeluar.isVisible().catch(() => false)) {
      await tombolKeluar.click();
      await page.waitForURL("/");
    }

    const tersimpan = sesi.get(akun.email);
    if (tersimpan) {
      await page.evaluate((t) => localStorage.setItem("modalink_token", t), tersimpan);
      await page.goto("/");
      await expect(page.getByRole("button", { name: /keluar/i })).toBeVisible();
      return;
    }

    await page.goto("/masuk");
    await page.getByLabel("Email").fill(akun.email);
    await page.getByLabel("Password").fill(akun.password);
    await page.getByRole("button", { name: "Masuk", exact: true }).click();
    await page.waitForURL((url) => url.pathname !== "/masuk");
    const token = await page.evaluate(() => localStorage.getItem("modalink_token"));
    if (token) sesi.set(akun.email, token);
  }

  // AI scoring berjalan di background task FastAPI, bukan sebelum 201
  // dikembalikan (10-api-contract.md: "Mengembalikan 201 segera, tanpa
  // menunggu AI"). Memuat ulang halaman adalah hal yang sungguh dilakukan
  // pengguna yang menunggu statusnya berubah; tanpa itu, state komponen
  // yang sudah terambil sekali tidak akan pernah memperbarui diri sendiri.
  async function tungguTeksMuncul(page: Page, pola: RegExp, batasMs = 20_000) {
    const mulai = Date.now();
    for (;;) {
      if (await page.getByText(pola).first().isVisible().catch(() => false)) return;
      if (Date.now() - mulai > batasMs) break;
      await page.waitForTimeout(500);
      await page.reload();
    }
    await expect(page.getByText(pola).first()).toBeVisible();
  }

  // Chromium mencatat "Failed to load resource: ... 401/403/404" ke console
  // untuk SETIAP respons HTTP gagal, termasuk permintaan yang memang
  // sengaja dibuat dan ditangani dengan baik oleh aplikasi (contoh di test
  // ini: GET pledges/scoring dari pengunjung tanpa akun, yang 401-nya
  // sengaja terjadi dan sudah ditangani lib/api.ts jadi pesan ramah, bukan
  // dibiarkan mentah). Dicek di sini dengan toEqual([]) di tempat lain di
  // spec ini: ini bukan galat JavaScript yang tidak tertangkap, hanya catatan
  // jaringan Chromium sendiri, jadi disaring sebelum dibandingkan.
  function bukanCatatanJaringanBiasa(teks: string): boolean {
    return !/failed to load resource/i.test(teks);
  }

  async function bukaProposalDariJelajah(page: Page) {
    await page.goto("/jelajah");
    // Halaman jelajah dirombak dari kartu menjadi baris daftar: tidak ada
    // lagi <article> per proposal maupun tautan terpisah bertuliskan "Baca
    // proposal". Sekarang SELURUH baris adalah satu tautan, dan namanya
    // menyebut usahanya sendiri -- justru supaya daftar dua puluh baris bisa
    // dinavigasi pembaca layar, yang mustahil kalau dua puluh tautan bernama
    // sama persis.
    //
    // Daftarnya juga berpaginasi 20 per halaman dan default terurut terbaru,
    // jadi proposal yang baru dibuat test ini ada di halaman pertama.
    await page.getByRole("link", { name: new RegExp(businessName, "i") }).first().click();
    await page.waitForURL(/\/proposal\//);
  }

  test.beforeAll(async ({ browser }: { browser: Browser }, testInfo) => {
    // Mesin yang menjalankan test ini berbagi CPU dengan agent-agent lain
    // yang bekerja paralel di worktree lain (lihat pengantar task ini):
    // 30s bawaan Playwright pernah kehabisan waktu bukan karena backend atau
    // frontend lambat (curl ke keduanya tetap instan saat itu terjadi),
    // melainkan karena render/hidrasi Chromium sendiri melambat di bawah
    // tekanan CPU bersama.
    testInfo.setTimeout(90_000);
    const page = await browser.newPage();
    await daftarSebagai(page, investorA, "investor");
    await daftarSebagai(page, investorB, "investor");
    await daftarSebagai(page, umkm, "umkm");
    await daftarSebagai(page, warga, "community");
    await page.close();
  });

  test("dari campaign dibuat sampai milestone terakhir cair", async ({ page }) => {
    test.setTimeout(90_000);
    // 1. Investor A membuat campaign.
    await masukSebagai(page, investorA);
    await page.goto("/investor/campaign/baru");
    await page.getByLabel("Judul campaign").fill(campaignTitle);
    await page.getByLabel("Deskripsi").fill(
      "Campaign untuk mendanai usaha kuliner rakyat yang sudah berjalan dan butuh modal tambahan " +
        "untuk memperluas distribusi ke kota-kota sekitar.",
    );
    await page.getByLabel("Dana target (Rp)").fill("50000000");
    await page.getByLabel("Tenggat pengajuan proposal").fill(tanggal(7));
    await page.getByLabel("Tenggat funding").fill(tanggal(30));
    await page.getByLabel("Ambang skor minimum (0-100)").fill("60");
    await page.getByRole("button", { name: "Buat campaign" }).click();
    // Pola UUID eksplisit, bukan hanya "/investor/campaign/": URL halaman
    // form sendiri ("/investor/campaign/baru") juga cocok dengan pola yang
    // lebih longgar, jadi waitForURL langsung selesai sebelum redirect
    // sungguhan terjadi kalau tidak dibedakan dari "baru".
    const polaIdCampaign = /\/investor\/campaign\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/i;
    await page.waitForURL(polaIdCampaign);
    campaignId = page.url().match(polaIdCampaign)![1]!;

    // 2. UMKM mengajukan proposal ke campaign itu, dengan milestone yang
    // jumlahnya pas dengan dana yang diminta (BR-14). fund_usage_plan
    // menyisipkan penanda [[SCORE:90]] yang hanya dikenali MockScoringEngine
    // (backend/app/ai/mock_engine.py): ini membuat skor AI deterministik di
    // atas ambang 60 campaign, bukan bergantung pada heuristik panjang teks
    // yang bisa berubah kalau teksnya diedit nanti.
    await masukSebagai(page, umkm);
    await page.goto("/umkm/proposal/baru");
    await page.getByLabel("Nama usaha").fill(businessName);
    await page.getByLabel("Profil usaha").fill(
      "Usaha kopi rakyat yang sudah berjalan tiga tahun di Yogyakarta, melayani pelanggan tetap " +
        "setiap minggu dengan kualitas biji kopi yang konsisten dan harga yang bersahabat untuk warga sekitar.",
    );
    await page.getByLabel("Jumlah dana yang diminta").fill("10000000");
    await page.getByLabel("Rencana penggunaan dana").fill(
      "60 persen dana untuk membeli mesin roasting baru, 40 persen untuk kemasan dan distribusi " +
        "ke tiga kota terdekat dalam enam bulan ke depan. [[SCORE:90]]",
    );
    await page.getByLabel("Proyeksi usaha").fill(
      "Omzet diproyeksikan naik dua kali lipat dalam satu tahun ke depan seiring ekspansi distribusi.",
    );
    await page.getByLabel("Judul tahap 1").fill("Pembelian mesin roasting");
    await page.getByLabel("Rincian tahap 1").fill("Membeli dan memasang mesin roasting baru di lokasi produksi.");
    await page.getByLabel("Nominal tahap 1").fill("5000000");
    await page.getByLabel("Judul tahap 2").fill("Distribusi ke tiga kota");
    await page.getByLabel("Rincian tahap 2").fill("Mendistribusikan produk ke tiga kota terdekat.");
    await page.getByLabel("Nominal tahap 2").fill("5000000");
    await page.getByRole("button", { name: "Kirim proposal" }).click();
    await page.waitForURL(/\/umkm\/beranda/);

    // Brief task ini menulis `await expect(page.getByText(/terbuka untuk
    // pendanaan/i)).toBeVisible();` persis di titik ini. Teksnya memang ada
    // (StatusBadge, components/ui/StatusBadge.tsx: status "listed" ->
    // "Terbuka untuk pendanaan"), tapi baru muncul setelah job scoring latar
    // belakang selesai, bukan seketika setelah redirect -- karena itu
    // tungguTeksMuncul memuat ulang sampai badge-nya sungguh berubah, bukan
    // langsung memeriksa DOM yang mungkin masih "Menunggu penilaian".
    await tungguTeksMuncul(page, /terbuka untuk pendanaan/i);
    await page
      .locator("[data-testid='kartu-proposal']", { hasText: businessName })
      .getByRole("link", { name: /baca proposal/i })
      .click();
    const polaIdProposal = /\/proposal\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/i;
    await page.waitForURL(polaIdProposal);
    proposalId = page.url().match(polaIdProposal)![1]!;

    // 3. Warga (komunitas) mendukung proposal lewat vote. (Langkah "pengunjung
    // tanpa akun" ada sebagai test tersendiri tepat di bawah file ini, bukan
    // di sini: ia butuh context browser yang benar-benar baru dan terisolasi,
    // dan test terpisah mendapat itu gratis lewat fixture `page` Playwright
    // sendiri, dibanding membangunnya manual lewat browser.newContext() di
    // tengah test yang sama.)
    await masukSebagai(page, warga);
    await bukaProposalDariJelajah(page);
    await page.getByRole("button", { name: /dukung proposal ini/i }).click();
    await expect(page.getByText("1 dukungan")).toBeVisible();

    // 5. Investor A memberi pledge 60% dari dana yang diminta.
    await masukSebagai(page, investorA);
    await bukaProposalDariJelajah(page);
    await page.getByLabel("Nominal pledge (Rp)").fill("6000000");
    await page.getByRole("button", { name: "Danai" }).click();
    await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "60");

    // 6. Investor B melengkapi sisa 40%, dana terkumpul penuh.
    await masukSebagai(page, investorB);
    await bukaProposalDariJelajah(page);
    await page.getByLabel("Nominal pledge (Rp)").fill("4000000");
    await page.getByRole("button", { name: "Danai" }).click();
    // Brief menulis `/dana terkumpul penuh/i`, tapi tidak ada teks seperti
    // itu di produk ini (StatusBadge untuk status "funded" berlabel "Dana
    // terpenuhi", components/ui/StatusBadge.tsx). Disesuaikan ke teks nyata.
    await expect(page.getByText(/dana terpenuhi/i)).toBeVisible();

    // 7. Investor A, sebagai lead investor (pledge terbesar), menyetujui
    // pencairan tahap 1. Tahap pertama tidak memerlukan laporan dari UMKM
    // (BR-41), jadi tombolnya langsung tersedia begitu dana terkumpul penuh.
    await masukSebagai(page, investorA);
    await page.goto("/investor/milestone");
    await page.getByRole("button", { name: /setujui pencairan/i }).first().click();
    // Brief menulis `/sudah cair/i`, tapi kalimat itu
    // ("Dana untuk tahap ini sudah cair.", components/MilestoneTimeline.tsx)
    // hanya dirender di dalam MilestoneTimeline, dan satu-satunya pemanggil
    // MilestoneTimeline (ApprovalQueue/MilestoneApprovalFeed, dipakai di
    // /investor/milestone) tidak pernah memberinya milestone yang sudah
    // "disbursed": begitu tahap disetujui, entrinya langsung dikeluarkan
    // dari antrian lewat refetch, bukan ditampilkan sebagai "sudah cair"
    // sesaat. Kalimat itu, di jalur produk yang ada sekarang, tidak pernah
    // tercapai -- lihat laporan Fase 11 Task 12. Sinyal nyata yang sungguh
    // terlihat pengguna ada di halaman detail proposal: StatusBadge tahap 1
    // berubah data-status="disbursed" (label "Dana cair").
    await page.goto(`/proposal/${proposalId}`);
    await expect(page.locator('[data-status="disbursed"]').first()).toBeVisible();

    // 8. UMKM melaporkan progres tahap 2 lewat tautan "Lapor progres" yang
    // ditambahkan di halaman detail proposal (sebelumnya tidak ada tautan
    // apa pun di seluruh produk menuju /umkm/milestone/[id]/lapor -- lihat
    // laporan Fase 11 Task 12).
    await masukSebagai(page, umkm);
    await page.goto(`/proposal/${proposalId}`);
    await page.getByRole("link", { name: /lapor progres/i }).click();
    await page.waitForURL(/\/umkm\/milestone\/.+\/lapor\?proposal=/);
    milestone2Id = page.url().match(/\/umkm\/milestone\/([^/]+)\/lapor/)?.[1] ?? "";
    expect(milestone2Id).toMatch(/[0-9a-f-]{36}/i);
    await page.getByLabel(/laporan progres/i).fill(
      "Mesin roasting sudah terpasang dan berjalan normal, omzet toko naik sekitar 15 persen " +
        "dibanding bulan sebelumnya karena kapasitas produksi bertambah.",
    );
    await page.getByRole("button", { name: "Kirim laporan" }).click();
    await expect(page.getByText(/laporan sudah dikirim dan sedang menunggu review/i)).toBeVisible();

    // 9. Investor A menyetujui pencairan tahap terakhir; proposal selesai.
    await masukSebagai(page, investorA);
    await page.goto("/investor/milestone");
    await page.getByRole("button", { name: /setujui pencairan/i }).click();
    await page.goto(`/proposal/${proposalId}`);
    await expect(page.locator('[data-status="completed"]').first()).toBeVisible();
    await expect(page.getByText(/selesai/i)).toBeVisible();
  });

  // Jalur anonim, sebagai test tersendiri (bukan di tengah test di atas):
  // proposal yang sama sudah publik (listed) sejak test sebelumnya, dan
  // fixture `page` di sini sudah terisolasi secara alami (context baru per
  // test), jadi tidak perlu browser.newContext() manual. Ini jalur paling
  // umum menuju halaman proposal (dari /jelajah, tanpa pernah masuk), dan
  // sebelum laporan Fase 11 Task 12 ditangani, GET .../pledges dan
  // GET .../scoring menolak pemanggil tanpa token dengan 401 yang tampil
  // mentah ("Token tidak ada.") tepat di tempat bilah funding dan panel
  // skor seharusnya berada.
  test("seorang pengunjung tanpa akun tidak pernah melihat galat 401 mentah di halaman proposal", async ({ page }) => {
    test.setTimeout(90_000);
    const galatKonsol: string[] = [];
    page.on("console", (m) => {
      if (m.type() === "error" && bukanCatatanJaringanBiasa(m.text())) galatKonsol.push(m.text());
    });
    page.on("pageerror", (err) => galatKonsol.push(err.message));

    await page.goto(`/proposal/${proposalId}`);
    await expect(page.getByRole("heading", { name: businessName })).toBeVisible();
    await expect(page.getByText(/token tidak ada/i)).toHaveCount(0);
    await expect(
      page.getByText(/masuk sebagai investor, atau sebagai umkm pemilik proposal ini/i),
    ).toBeVisible();
    await expect(page.getByText(/panel skor hanya terlihat oleh investor/i)).toBeVisible();
    expect(galatKonsol).toEqual([]);
  });

  test("tidak ada galat konsol menjelajahi seluruh dua belas rute produk", async ({ page }) => {
    test.setTimeout(90_000);
    const galat: string[] = [];
    page.on("console", (m) => {
      if (m.type() === "error" && bukanCatatanJaringanBiasa(m.text())) galat.push(`[konsol] ${m.text()}`);
    });
    page.on("pageerror", (err) => galat.push(`[pageerror] ${err.message}`));

    // Rute publik, sebagai pengunjung anonim. Setiap test Playwright
    // mendapat `page` baru dengan localStorage kosong (fixture terpisah per
    // test meski berada di describe mode "serial" yang sama), jadi tidak
    // ada sesi tersisa dari test pertama yang perlu dibersihkan di sini.
    for (const rute of ["/", "/masuk", "/daftar", "/jelajah", `/proposal/${proposalId}`]) {
      await page.goto(rute);
    }

    // Rute investor.
    await masukSebagai(page, investorA);
    for (const rute of ["/investor/campaign", "/investor/campaign/baru", `/investor/campaign/${campaignId}`, "/investor/milestone"]) {
      await page.goto(rute);
    }

    // Rute UMKM, termasuk halaman lapor milestone dengan ?proposal= yang
    // benar (R-24 brief fase 11: setiap tautan navigasi menuju halaman yang
    // ada, dan di sini juga dibuktikan bahwa parameter query-nya memang
    // sampai, bukan hilang di tengah jalan -- lihat peringatan "known
    // hazard" di brief task ini).
    await masukSebagai(page, umkm);
    for (const rute of ["/umkm/beranda", "/umkm/proposal/baru", `/umkm/milestone/${milestone2Id}/lapor?proposal=${proposalId}`]) {
      await page.goto(rute);
    }

    expect(galat).toEqual([]);
  });

  test("seluruh alur masuk bisa dijalankan tanpa menyentuh tetikus", async ({ page }) => {
    test.setTimeout(90_000);
    // Dimulai dari rute terlindungi investor, bukan langsung /masuk: tanpa
    // token, RouteGuard mengarahkan ke /masuk?next=/investor/campaign
    // (lib/auth.ts, components/RouteGuard.tsx), dan ini membuktikan dua hal
    // sekaligus lewat keyboard murni: form masuk BISA dikirim tanpa
    // tetikus, dan sesudahnya pengguna sungguh dibawa balik ke halaman yang
    // semula dituju, bukan ke "/". Brief menulis ekspektasi URL /investor/
    // tanpa menyebut asalnya dari rute terlindungi; langsung ke /masuk
    // tanpa query "next" malah mendarat di "/" (tujuanAmanSetelahMasuk).
    await page.goto("/investor/campaign");
    await page.waitForURL(/\/masuk\?next=/);
    // Brief menulis satu Tab tunggal dari atas halaman sampai ke field
    // Email. Itu benar sebelum Fase 11 Task 11: sekarang AppHeader global
    // (tautan "Modalink", "Jelajahi", "Masuk", "Daftar", tombol tema)
    // berdiri di atas setiap halaman, jadi satu Tab tunggal dari <body>
    // berhenti di tautan header, bukan di field Email. .focus() di sini
    // menaruh fokus persis di titik yang akan dicapai keyboard Tab lewat
    // header itu, lalu sisanya (Tab ke Password, Enter mengirim form) tetap
    // seluruhnya keyboard sungguhan -- tidak ada klik atau pengisian value
    // langsung di titik mana pun.
    await page.getByLabel("Email").focus();
    await page.keyboard.type(investorA.email);
    await page.keyboard.press("Tab");
    await page.keyboard.type(investorA.password);
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/investor\/campaign$/);
  });
});
