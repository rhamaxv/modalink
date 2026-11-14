import { readFileSync } from "node:fs";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ExplorePage from "@/app/jelajah/page";
import Beranda from "@/app/page";

// Dipakai oleh dua halaman (jelajah dan landing): tidak boleh ada dua
// <section> berurutan dengan data-pola yang sama (RHYTHM 3, DESIGN.md). Ini
// pagar yang murah dan masih berguna, tapi sendirian ia tidak membuktikan
// labelnya BENAR, cuma bahwa labelnya BERBEDA dari tetangganya. Pagar kedua
// di bawah ("matches what is actually rendered") memeriksa struktur yang
// sungguh dirender, karena audit desain pernah menemukan satu section
// berlabel "dua-kolom-asimetris" yang sebenarnya satu kolom.
// `minimalSection` adalah parameter, bukan 4 yang dipatok untuk semua
// halaman, dan itu memperbaiki pagar yang salah.
//
// RHYTHM 3 di DESIGN.md melarang dua pola komposisi berurutan yang sama. Ia
// tidak pernah menuntut jumlah section minimum. Angka 4 di sini ditulis
// untuk halaman landing lalu diterapkan apa adanya ke halaman jelajah, dan
// di sanalah ia merugikan: halaman INDEKS tidak punya empat gagasan
// komposisi untuk diceritakan, ia punya satu daftar. Memaksanya tetap
// berjumlah empat adalah alasan halaman itu sempat punya hero setinggi
// 62vh, dua kartu pintu masuk, dan esai alur dana sebelum baris pertama
// datanya. Dua tetap jadi batas bawah yang masuk akal: dengan satu pola,
// aturan "tidak boleh sama dengan tetangganya" tidak menguji apa pun.
function checkPolaBerurutanBerbeda(sourcePath: string, minimalSection = 2) {
  const source = readFileSync(sourcePath, "utf8");
  const patterns = [...source.matchAll(/data-pola="([a-z-]+)"/g)].map((m) => m[1]);
  expect(patterns.length).toBeGreaterThanOrEqual(minimalSection);
  patterns.forEach((pattern, i) => {
    if (i > 0) expect(pattern).not.toBe(patterns[i - 1]);
  });
}

function checkSetiapSectionBerpola(sourcePath: string) {
  const source = readFileSync(sourcePath, "utf8");
  const sectionCount = (source.match(/<section/g) ?? []).length;
  const patternCount = (source.match(/data-pola=/g) ?? []).length;
  expect(patternCount).toBe(sectionCount);
}

// ProposalList (dalam ProposalCard.tsx) memanggil fetch begitu ia dipasang,
// dan sekarang FeaturedProposalHighlight di halaman landing juga begitu.
// Tes di bawah ini hanya menyoroti struktur halaman (RHYTHM, H1, navigasi),
// bukan isi daftar proposal, jadi fetch distub supaya tidak pernah
// benar-benar memanggil jaringan dan tidak menyisakan rejection tak tertangani.
function stubEmptyFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 }), {
          status: 200,
        }),
      ),
    ),
  );
}

function stubFetchWithProposals() {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            total: 2,
            page: 1,
            page_size: 20,
            items: [
              {
                id: "p1",
                campaign_id: "c1",
                umkm_id: "u1",
                business_name: "Kopi Senja",
                business_summary:
                  "Usaha kopi rumahan yang sudah berjalan tiga tahun dan ingin memperluas kapasitas produksi.",
                requested_amount: 25_000_000,
                collected_amount: 5_000_000,
                status: "listed",
                scoring_status: "done",
                lead_investor_id: null,
                funded_at: null,
                created_at: "2026-01-01T00:00:00Z",
              },
              {
                id: "p2",
                campaign_id: "c1",
                umkm_id: "u2",
                business_name: "Batik Lereng",
                business_summary: "Usaha batik tulis.",
                requested_amount: 15_000_000,
                collected_amount: 9_000_000,
                status: "partially_funded",
                scoring_status: "done",
                lead_investor_id: "inv1",
                funded_at: null,
                created_at: "2025-12-01T00:00:00Z",
              },
            ],
          }),
          { status: 200 },
        ),
      ),
    ),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RHYTHM 3 on the explore page", () => {
  it("has no two consecutive sections sharing the same composition pattern", () => {
    checkPolaBerurutanBerbeda("app/jelajah/page.tsx");
  });

  it("gives every section an explicit pattern attribute", () => {
    checkSetiapSectionBerpola("app/jelajah/page.tsx");
  });
});

describe("RHYTHM 3 on the landing page", () => {
  it("has no two consecutive sections sharing the same composition pattern", () => {
    checkPolaBerurutanBerbeda("app/page.tsx", 4);
  });

  it("gives every section an explicit pattern attribute", () => {
    checkSetiapSectionBerpola("app/page.tsx");
  });

  it("proves the guard actually fails when two consecutive sections share a pattern", () => {
    // Pembuktian bahwa pagar ini bisa merah: dua pola identik berurutan
    // yang disuntikkan langsung ke string sumber, bukan ke file sungguhan,
    // supaya tidak perlu menulis-lalu-memulihkan app/page.tsx di tengah test run.
    const palsu = `
      <section data-pola="naratif-kiri">a</section>
      <section data-pola="naratif-kiri">b</section>
      <section data-pola="daftar-bernomor">c</section>
      <section data-pola="dua-kolom-setara">d</section>
    `;
    const patterns = [...palsu.matchAll(/data-pola="([a-z-]+)"/g)].map((m) => m[1]);
    expect(() => {
      patterns.forEach((pattern, i) => {
        if (i > 0) expect(pattern).not.toBe(patterns[i - 1]);
      });
    }).toThrow();
  });
});

// Pagar kedua, lebih kuat: membaca DOM yang sungguh dirender React (bukan
// regex di atas string sumber) dan memeriksa bahwa struktur section benar
// mengikuti apa yang namanya klaim. Satu label yang tidak cocok dengan
// strukturnya sungguhan harus membuat test ini merah, bukan membiarkannya
// lolos karena authornya "percaya" labelnya sudah benar.
function findSectionByPola(container: HTMLElement, pola: string): HTMLElement {
  const el = container.querySelector<HTMLElement>(`[data-pola="${pola}"]`);
  if (!el) throw new Error(`Section berpola "${pola}" tidak ditemukan di DOM yang dirender.`);
  return el;
}

function gridInfo(section: HTMLElement): { el: HTMLElement; childCount: number; raw: string } | null {
  const el = section.querySelector<HTMLElement>('[class*="grid-cols"]');
  if (!el) return null;
  return { el, childCount: el.children.length, raw: el.className };
}

function expectSingleColumnNarrative(section: HTMLElement) {
  expect(
    section.querySelector('[class*="grid-cols"]'),
    "pola naratif-kiri tidak boleh memuat grid berkolom: itu bukan narasi satu kolom lagi",
  ).toBeNull();
}

// Dua kolom SELEBAR SAMA: memakai utility literal Tailwind "grid-cols-2"
// (bukan template kustom), dan benar-benar punya dua anak langsung, bukan
// satu kolom yang menumpuk begitu grid-nya tidak pernah aktif.
function expectEqualTwoColumn(section: HTMLElement) {
  const grid = gridInfo(section);
  expect(grid, "pola dua-kolom-setara harus memuat elemen ber-grid-cols").not.toBeNull();
  expect(grid!.raw).toMatch(/\bgrid-cols-2\b/);
  expect(grid!.childCount, "grid dua-kolom-setara harus punya dua anak langsung, bukan satu").toBe(2);
}

// Dua kolom TAK SETARA: template grid-cols-[...] kustom dengan dua pecahan
// yang BERBEDA, dan dua anak langsung sungguhan. Ini pagar yang langsung
// menyasar bug yang ditemukan audit desain: section berlabel asimetris yang
// di DOM sebenarnya satu kolom (grid tidak pernah aktif), atau dua kolom
// yang pecahannya diam-diam sama sehingga bukan asimetris.
function expectAsymmetricTwoColumn(section: HTMLElement) {
  const grid = gridInfo(section);
  expect(grid, "pola dua-kolom-asimetris harus memuat elemen ber-grid-cols").not.toBeNull();
  expect(
    grid!.childCount,
    "grid dua-kolom-asimetris harus punya dua anak langsung: ini persis bug yang ditemukan audit, section asimetris yang sebenarnya satu kolom",
  ).toBe(2);
  const cocok = /grid-cols-\[([^\]]+)\]/.exec(grid!.raw);
  expect(cocok, "pola dua-kolom-asimetris harus memakai template grid kustom, bukan grid-cols-2 yang setara").not.toBeNull();
  const pecahan = (cocok?.[1] ?? "").split("_");
  expect(pecahan, "template grid kustom harus punya dua pecahan kolom").toHaveLength(2);
  expect(pecahan[0], "kedua pecahan kolom sama: ini bukan asimetris, cuma menyamar").not.toBe(pecahan[1]);
}

function expectRealNumberedList(section: HTMLElement) {
  const ol = section.querySelector("ol");
  expect(ol, "pola daftar-bernomor harus memuat elemen <ol> sungguhan, bukan <div> yang kebetulan tampil bernomor").not.toBeNull();
  expect(ol!.querySelectorAll("li").length).toBeGreaterThanOrEqual(2);
}

function expectFullBleedWithOneAction(section: HTMLElement) {
  expect(
    section.className,
    "pola lebar-penuh-cta tidak boleh dibatasi max-w pada <section> itu sendiri: itu artinya latarnya tidak menembus tepi",
  ).not.toMatch(/\bmax-w-/);
  // Satu ajakan bertindak, apa pun variannya. Versi sebelumnya menuntut satu
  // aksi BERAKSEN di section ini, dan itu menempatkan satu-satunya momen aksen
  // halaman di bawah lipatan sementara layar pertama tidak punya warna sama
  // sekali. Anggaran aksen diperiksa di tingkat halaman, bukan di sini.
  expect(section.querySelectorAll("a[href], button").length).toBe(1);
}

// DESIGN.md menjatah AKSI berlatar aksen, bukan warna secara umum, dan
// bedanya menentukan. Versi pertama pagar ini menghitung setiap `.bg-accent`
// di halaman lalu menuntut tepat satu, termasuk bilah funding dan penanda
// tahap yang sama sekali bukan aksi. Akibatnya halaman penuh berakhir dengan
// satu momen warna saja, dan pemilik project menyebutnya datar dua kali.
//
// Yang dijaga di sini adalah hierarki tindakan: dua tombol lime di satu layar
// berarti tidak ada yang menandai keputusan utama. Penanda dan teks beraksen
// tidak dibatasi pagar ini.
function expectExactlyOneAccentAction(container: HTMLElement) {
  const aksi = [...container.querySelectorAll("a[href], button")].filter((el) =>
    el.className.split(" ").includes("bg-accent"),
  );
  expect(
    aksi.length,
    `halaman ini punya ${aksi.length} aksi berlatar aksen; DESIGN.md menghendaki tepat satu`,
  ).toBe(1);
}

// Sisi sebaliknya, dan ia yang hilang selama ini: halaman tanpa warna sama
// sekali juga melanggar arah. Diukur pada DOM yang dirender, bukan pada
// sumber, supaya kelas yang tidak pernah aktif tidak ikut terhitung.
function expectPageIsNotColourless(container: HTMLElement) {
  const KELAS_WARNA = [
    "bg-accent", "bg-accent-2", "text-accent-text", "text-accent-2-text",
    "border-accent", "text-ok", "text-warn", "text-danger",
  ];
  const momen = [...container.querySelectorAll<HTMLElement>("*")].filter((el) => {
    const kelas = el.className?.split?.(" ") ?? [];
    return KELAS_WARNA.some((k) => kelas.includes(k));
  });
  expect(
    momen.length,
    `halaman ini hanya punya ${momen.length} momen warna; satu halaman penuh yang nyaris monokrom adalah keluhan yang memicu arah visual ini ditulis ulang`,
  ).toBeGreaterThanOrEqual(3);
}

describe("RHYTHM 3 patterns match what is actually rendered, not just their label", () => {
  it("the explore page leads with a compact heading, not a composition that delays the list", async () => {
    // Halaman indeks: judulnya satu kolom tanpa grid, dan tidak memesan
    // tinggi layar. Pagar ini menggantikan pagar lama yang menuntut hero
    // dua kolom asimetris di sini, dan hero itulah yang membuat daftar
    // datanya mulai di bawah lipatan.
    stubEmptyFetch();
    const { container } = render(<ExplorePage />);
    const judul = findSectionByPola(container, "judul-dan-kendali");
    expectSingleColumnNarrative(judul);
    expect(judul.className, "judul halaman indeks tidak boleh memesan tinggi layar").not.toMatch(
      /min-h-\[/,
    );
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
  });

  it("daftar-bernomor on the explore page is a real <ol>, matching the numbered badge each card already shows", async () => {
    stubFetchWithProposals();
    render(<ExplorePage />);
    await screen.findByText("Kopi Senja");
    expectRealNumberedList(findSectionByPola(document.body, "daftar-bernomor"));
  });

  it("puts the list above the closing bar, not below it", async () => {
    // Urutan ini yang membedakan halaman indeks dari halaman pendaratan:
    // ajakan mendaftar datang SETELAH pengunjung melihat ada sesuatu yang
    // layak, bukan sebelum daftarnya sempat terbaca.
    stubEmptyFetch();
    const { container } = render(<ExplorePage />);
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
    const pola = [...container.querySelectorAll("[data-pola]")].map((el) =>
      el.getAttribute("data-pola"),
    );
    expect(pola.indexOf("daftar-bernomor")).toBeLessThan(pola.indexOf("lebar-penuh-cta"));
  });

  it("lebar-penuh-cta on the explore page bleeds full width with exactly one action", async () => {
    stubEmptyFetch();
    const { container } = render(<ExplorePage />);
    expectFullBleedWithOneAction(findSectionByPola(container, "lebar-penuh-cta"));
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
  });

  it("kiri-dinding-sampul on the landing page truly renders two columns (narrative, then the cover wall)", async () => {
    stubEmptyFetch();
    const { container } = render(<Beranda />);
    expectAsymmetricTwoColumn(findSectionByPola(container, "kiri-dinding-sampul"));
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
  });

  it("fills the hero with real businesses and their covers, not one stacked label block", async () => {
    // Menggantikan pagar lama yang menuntut satu nominal berukuran hero di
    // kolom kanan. Blok itu (FeaturedProposalHighlight) dibuang atas
    // permintaan pemilik project, dan premis DESIGN.md yang melahirkannya
    // sudah berubah: saat arah visual ditulis, produk ini tidak punya gambar
    // apa pun, jadi ruang tempat foto bekerja di referensi diisi uang. UMKM
    // sekarang bisa mengunggah foto sampul, jadi ruang itu diisi usaha
    // sungguhan. Nominalnya tidak hilang, ia pindah ke tiap kotak.
    stubFetchWithProposals();
    const { container } = render(<Beranda />);
    await screen.findByText("Kopi Senja");

    const hero = findSectionByPola(container, "kiri-dinding-sampul");
    const tautan = [...hero.querySelectorAll("a[href]")].filter((a) =>
      a.getAttribute("href")?.startsWith("/proposal/"),
    );
    expect(tautan.length, "hero harus memuat beberapa usaha, bukan satu").toBeGreaterThan(1);
    // Tiap kotak tetap menyebut nominalnya.
    expect(screen.getByText(/Rp25\.000\.000 dicari/)).toBeInTheDocument();
  });

  it("gives a business with no uploaded photo a shape instead of a broken image", async () => {
    // Keadaan yang paling sering terlihat, bukan kasus pinggiran: sebagian
    // besar usaha tidak akan pernah mengunggah apa pun.
    stubFetchWithProposals();
    const { container } = render(<Beranda />);
    await screen.findByText("Kopi Senja");
    const hero = findSectionByPola(container, "kiri-dinding-sampul");
    expect(hero.querySelectorAll("img").length, "stub ini tidak punya sampul").toBe(0);
    expect(hero.querySelectorAll("svg").length).toBeGreaterThan(0);
  });

  it("daftar-bernomor on the landing page is a real <ol>, not a <div> with number-shaped spans", async () => {
    stubEmptyFetch();
    const { container } = render(<Beranda />);
    expectRealNumberedList(findSectionByPola(container, "daftar-bernomor"));
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
  });

  it("dua-kolom-setara on the landing page truly renders two equally-wide columns", async () => {
    stubEmptyFetch();
    const { container } = render(<Beranda />);
    expectEqualTwoColumn(findSectionByPola(container, "dua-kolom-setara"));
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
  });

  it("lebar-penuh-cta on the landing page bleeds full width with exactly one action", async () => {
    stubEmptyFetch();
    const { container } = render(<Beranda />);
    expectFullBleedWithOneAction(findSectionByPola(container, "lebar-penuh-cta"));
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
  });

  it("spends exactly one accent action across the whole landing page, and spends it above the fold", async () => {
    stubEmptyFetch();
    const { container } = render(<Beranda />);
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
    expectExactlyOneAccentAction(container);
    expectPageIsNotColourless(container);

    // Dan ia ada di section pertama. Aksen yang dibelanjakan di bawah lipatan
    // membuat layar pertama tanpa warna, keluhan yang memicu perubahan ini.
    const pertama = container.querySelector("section");
    expect(pertama?.querySelectorAll(".bg-accent").length).toBe(1);
  });
});

describe("the rendered-structure guard can actually fail, proven on fabricated markup", () => {
  // R-35 di skill testing-and-regression: sebuah pagar yang hanya dinalar,
  // belum pernah dibuktikan merah, bukan pagar yang terverifikasi. Di bawah
  // ini bukan merender halaman sungguhan (yang sekarang sudah benar), tapi
  // menyuntikkan markup palsu yang MENIRU persis bug yang ditemukan audit
  // desain, untuk membuktikan fungsi pemeriksanya sendiri bisa gagal.
  it("fails a section labelled asymmetric when its two fractions are secretly equal", () => {
    const palsu = document.createElement("section");
    palsu.innerHTML =
      '<div class="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)]"><span>a</span><span>b</span></div>';
    expect(() => expectAsymmetricTwoColumn(palsu)).toThrow();
  });

  it("fails a section labelled asymmetric two-column when it is actually a single column (the exact audit bug)", () => {
    const palsu = document.createElement("section");
    palsu.innerHTML = '<div class="flex flex-col"><span>a</span><span>b</span></div>';
    expect(() => expectAsymmetricTwoColumn(palsu)).toThrow();
  });

  it("fails a section labelled equal two-column when there is no grid-cols-2 at all", () => {
    const palsu = document.createElement("section");
    palsu.innerHTML = '<div class="flex flex-col"><span>a</span><span>b</span></div>';
    expect(() => expectEqualTwoColumn(palsu)).toThrow();
  });

  it("fails a section labelled daftar-bernomor when it has no real <ol>", () => {
    const palsu = document.createElement("section");
    palsu.innerHTML = '<div class="flex flex-col"><div>1</div><div>2</div></div>';
    expect(() => expectRealNumberedList(palsu)).toThrow();
  });

  it("fails a section labelled lebar-penuh-cta when it is capped by max-w on the section itself", () => {
    const palsu = document.createElement("section");
    palsu.className = "max-w-measure";
    palsu.innerHTML = '<button class="bg-accent">x</button>';
    expect(() => expectFullBleedWithOneAction(palsu)).toThrow();
  });

  it("fails a section labelled lebar-penuh-cta when it has more than one accent action", () => {
    const palsu = document.createElement("section");
    palsu.innerHTML = '<button class="bg-accent">x</button><button class="bg-accent">y</button>';
    expect(() => expectFullBleedWithOneAction(palsu)).toThrow();
  });
});

describe("explore page is free of default AI-slop shapes", () => {
  it("has no eyebrow pill badge above the H1", () => {
    stubEmptyFetch();
    render(<ExplorePage />);
    const h1 = screen.getByRole("heading", { level: 1 });
    const previousSibling = h1.previousElementSibling;
    expect(previousSibling?.getAttribute("data-pola")).not.toBe("eyebrow-badge");
  });

  it("has no statistic with no real data source", () => {
    stubEmptyFetch();
    render(<ExplorePage />);
    // R-17: tidak ada "10rb+ pengguna" atau sejenisnya.
    expect(screen.queryByText(/\d+(rb|k|jt)\+/i)).toBeNull();
  });

  it("has no testimonial", () => {
    stubEmptyFetch();
    render(<ExplorePage />);
    expect(screen.queryByText(/testimoni/i)).toBeNull();
  });

  it("links every navigation item to a route that actually exists", () => {
    stubEmptyFetch();
    render(<ExplorePage />);
    const staticRoutes = ["/", "/jelajah", "/masuk", "/daftar"];
    screen.getAllByRole("link").forEach((a) => {
      const href = a.getAttribute("href") ?? "";
      if (!href.startsWith("/")) return;
      const path = href.split("#")[0] ?? href;
      // Rute detail proposal dibangun stream lain di worktree lain
      // (brief f11-b), tapi rutenya nyata: menautkannya dari sini sah.
      const isProposalDetailRoute = /^\/proposal\/[^/]+$/.test(path);
      expect(staticRoutes.includes(path) || isProposalDetailRoute).toBe(true);
    });
  });
});

describe("landing page is free of default AI-slop shapes", () => {
  it("has no eyebrow pill badge above the H1", async () => {
    stubEmptyFetch();
    render(<Beranda />);
    const h1 = screen.getByRole("heading", { level: 1 });
    const previousSibling = h1.previousElementSibling;
    expect(previousSibling).toBeNull();
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
  });

  it("does not use the product name as the H1", () => {
    stubEmptyFetch();
    render(<Beranda />);
    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1.textContent?.trim().toLowerCase()).not.toBe("modalink");
  });

  it("has no statistic with no real data source", async () => {
    stubEmptyFetch();
    render(<Beranda />);
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
    expect(screen.queryByText(/\d+(rb|k|jt)\+/i)).toBeNull();
  });

  it("has no testimonial", async () => {
    stubEmptyFetch();
    render(<Beranda />);
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
    expect(screen.queryByText(/testimoni/i)).toBeNull();
  });

  it("has no em dash in its copy", () => {
    const source = readFileSync("app/page.tsx", "utf8");
    const textBlocks = [...source.matchAll(/>([^<>{}]*)</g)].map((m) => m[1]);
    textBlocks.forEach((text) => expect(text).not.toContain("—"));
  });

  it("links every navigation item to a route that actually exists", async () => {
    stubEmptyFetch();
    render(<Beranda />);
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
    const staticRoutes = ["/", "/jelajah", "/masuk", "/daftar"];
    screen.getAllByRole("link").forEach((a) => {
      const href = a.getAttribute("href") ?? "";
      if (!href.startsWith("/")) return;
      const path = href.split("#")[0] ?? href;
      const isProposalDetailRoute = /^\/proposal\/[^/]+$/.test(path);
      expect(staticRoutes.includes(path) || isProposalDetailRoute).toBe(true);
    });
  });

  // Versi sebelumnya menghitung SETIAP elemen `.bg-accent` di halaman,
  // termasuk permukaan section CTA berlatar aksen penuh yang bukan sebuah
  // aksi sama sekali. Itu persis kesalahan yang DESIGN.md sebut sebagai
  // sumber kedataran: pagar yang menggeledah kata "bg-accent" alih-alih
  // membedakan AKSI dari LATAR. Diperbaiki memakai pemeriksa yang sama
  // dengan "spends exactly one accent action..." di bawah, bukan dihapus:
  // anggaran satu aksi berlatar aksen tetap berlaku, cuma dihitung benar.
  it("uses the accent colour on at most one primary action on this screen", async () => {
    stubEmptyFetch();
    const { container } = render(<Beranda />);
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
    const aksi = [...container.querySelectorAll("a[href], button")].filter((el) =>
      el.className.split(" ").includes("bg-accent"),
    );
    expect(aksi.length).toBeLessThanOrEqual(1);
  });
});

describe("public proposal list on the explore page", () => {
  it("makes the whole row a link to the proposal, named by the business it belongs to", async () => {
    // Satu tautan per baris, bukan tautan "Baca proposal" terpisah di dalam
    // kartu. Di daftar dua puluh baris, dua puluh tautan yang namanya sama
    // persis adalah daftar yang tidak bisa dinavigasi pembaca layar: nama
    // tautannya harus menyebut proposal mana yang dituju.
    stubFetchWithProposals();
    render(<ExplorePage />);
    expect(await screen.findByText("Kopi Senja")).toBeInTheDocument();
    const links = screen
      .getAllByRole("link")
      .filter((a) => a.getAttribute("href")?.startsWith("/proposal/"));
    expect(links).toHaveLength(2);
    expect(links[0]?.textContent).toContain("Kopi Senja");
    expect(links[1]?.textContent).toContain("Batik Lereng");
  });

  it("gives every row the same nominal scale, so the amounts line up as a column", async () => {
    // Kebalikan dari pagar sebelumnya, dan itu disengaja. Dulu baris pertama
    // wajib bernominal lebih besar dari sisanya. Aturan itu masuk akal di
    // halaman yang memang punya satu kartu unggulan, dan menyesatkan di
    // halaman indeks yang urutannya dipilih pengunjung: begitu daftar
    // diurutkan dari nominal terkecil, baris pertama tidak lagi istimewa
    // dalam arti apa pun, ia cuma kebetulan di atas. Yang membuat daftar
    // panjang bisa dipindai adalah nominal yang sejajar, bukan satu baris
    // yang dibesarkan.
    stubFetchWithProposals();
    render(<ExplorePage />);
    await screen.findByText("Kopi Senja");
    const kelas = (teks: string) => screen.getByText(teks).className.split(" ");
    expect(kelas("Rp25.000.000")).toContain("text-amount-sm");
    expect(kelas("Rp15.000.000")).toContain("text-amount-sm");
    // Angka tabular: tanpa ini, digit berlebar berbeda membuat kolom nominal
    // bergoyang dan dua baris tidak bisa dibandingkan sekilas.
    expect(kelas("Rp25.000.000")).toContain("tabular");
  });

  it("shows how much of each requested amount has actually been collected", async () => {
    // collected_amount sudah ada di ProposalOut sejak lama tapi daftar ini
    // tidak pernah membacanya, jadi setiap baris menyebut dana yang diminta
    // tanpa satu pun petunjuk seberapa jauh ia sudah terkumpul.
    stubFetchWithProposals();
    render(<ExplorePage />);
    await screen.findByText("Kopi Senja");
    expect(screen.getByText("Rp5.000.000 terkumpul")).toBeInTheDocument();
    expect(screen.getByText("Rp9.000.000 terkumpul")).toBeInTheDocument();
  });

  it("renders the list as a real ordered list, not a div that only looks numbered", async () => {
    stubFetchWithProposals();
    const { container } = render(<ExplorePage />);
    await screen.findByText("Kopi Senja");
    const ol = container.querySelector("ol");
    expect(ol).not.toBeNull();
    expect(ol!.querySelectorAll("li").length).toBe(2);
  });
});

// Ditemukan sambil membangun halaman ini, bukan dirancang lebih dulu:
// --accent-2 dipakai sebagai warna TEKS polos di satu draf awal halaman
// landing (label kategori di atas judul section, penekanan di dalam
// kalimat), persis pola yang DESIGN.md sebut sah. Tabel kontras DESIGN.md
// cuma mengukur --accent-2 sebagai teks di atas --paper GELAP (9,59:1,
// lolos) dan tidak pernah mengukurnya di tema terang, karena --accent-2
// sengaja tidak ikut berbalik warna sementara --paper dan --panel berbalik
// dari hampir hitam ke hampir putih. Dihitung di sini dengan rumus yang
// sama seperti tests/accent-contrast.test.ts: hasilnya gagal jauh di kedua
// latar tema terang. Perbaikannya di app/page.tsx: --accent-2 sekarang
// dipakai sebagai LATAR highlight kecil berpasangan dengan --on-accent
// (kombinasi yang sudah diukur DESIGN.md lolos dan tidak pernah berbalik),
// bukan sebagai warna teks lepas. Pagar di bawah mengunci temuan ini supaya
// tidak terulang di halaman yang sama.
describe("accent-2 as a bare text colour fails AA in light mode (a gap DESIGN.md's own table never measured)", () => {
  function luminance(hex: string): number {
    const ch = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
    const [r, g, b] = ch.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)) as [
      number,
      number,
      number,
    ];
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  function ratio(a: string, b: string): number {
    const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
    return (hi + 0.05) / (lo + 0.05);
  }

  it("proves accent-2 text on the light-theme paper and panel backgrounds both fail 4.5:1", () => {
    const ACCENT_2 = "#AAB2FF";
    const PAPER_LIGHT = "#FBF9F4";
    const PANEL_LIGHT = "#F3EFE6";
    expect(ratio(ACCENT_2, PAPER_LIGHT)).toBeLessThan(4.5);
    expect(ratio(ACCENT_2, PANEL_LIGHT)).toBeLessThan(4.5);
  });

  it("keeps the landing and explore pages from using text-accent-2 as a bare text colour", () => {
    for (const berkas of ["app/page.tsx", "app/jelajah/page.tsx"]) {
      const source = readFileSync(berkas, "utf8");
      // className=\"...text-accent-2...\" di luar pasangan bg-accent-2 (yang
      // aman, lihat komentar di atas) berarti accent-2 dipakai sebagai warna
      // teks lepas, persis bug yang pernah ada di sini.
      // Negative lookahead atas "-text": `text-accent-2-text` adalah token
      // yang BENAR untuk aksen sebagai teks (6.14:1 di tema terang) dan baru
      // ada setelah pagar ini ditulis; tanpa pengecualian ini pagarnya menolak
      // satu-satunya cara yang aman.
      expect(source, `${berkas} memakai text-accent-2 sebagai warna teks lepas`).not.toMatch(
        /\btext-accent-2(?!-text)\b/,
      );
    }
  });
});
