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
function checkPolaBerurutanBerbeda(sourcePath: string) {
  const source = readFileSync(sourcePath, "utf8");
  const patterns = [...source.matchAll(/data-pola="([a-z-]+)"/g)].map((m) => m[1]);
  expect(patterns.length).toBeGreaterThanOrEqual(4);
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
    vi.fn(() => Promise.resolve(new Response(JSON.stringify({ items: [] }), { status: 200 }))),
  );
}

function stubFetchWithProposals() {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            items: [
              {
                id: "p1",
                campaign_id: "c1",
                umkm_id: "u1",
                business_name: "Kopi Senja",
                business_profile_excerpt:
                  "Usaha kopi rumahan yang sudah berjalan tiga tahun dan ingin memperluas kapasitas produksi.",
                requested_amount: 25_000_000,
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
                business_profile_excerpt: "Usaha batik tulis.",
                requested_amount: 15_000_000,
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
    checkPolaBerurutanBerbeda("app/page.tsx");
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
  it("naratif-kiri on the explore page is really a single column with no grid", async () => {
    stubEmptyFetch();
    const { container } = render(<ExplorePage />);
    expectSingleColumnNarrative(findSectionByPola(container, "naratif-kiri"));
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
  });

  it("daftar-bernomor on the explore page is a real <ol>, matching the numbered badge each card already shows", async () => {
    stubFetchWithProposals();
    render(<ExplorePage />);
    await screen.findByText("Kopi Senja");
    expectRealNumberedList(findSectionByPola(document.body, "daftar-bernomor"));
  });

  it("dua-kolom-asimetris on the explore page truly renders two unequal columns", async () => {
    stubEmptyFetch();
    const { container } = render(<ExplorePage />);
    expectAsymmetricTwoColumn(findSectionByPola(container, "dua-kolom-asimetris"));
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
  });

  it("lebar-penuh-cta on the explore page bleeds full width with exactly one action", async () => {
    stubEmptyFetch();
    const { container } = render(<ExplorePage />);
    expectFullBleedWithOneAction(findSectionByPola(container, "lebar-penuh-cta"));
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
  });

  it("kiri-sorotan-nominal on the landing page truly renders two columns (narrative, then the featured amount)", async () => {
    stubEmptyFetch();
    const { container } = render(<Beranda />);
    expectAsymmetricTwoColumn(findSectionByPola(container, "kiri-sorotan-nominal"));
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");
  });

  it("the featured amount on the landing page actually renders at the hero scale, once settled", async () => {
    stubFetchWithProposals();
    render(<Beranda />);
    const nominal = await screen.findByText("Rp25.000.000");
    expect(nominal.className.split(" ")).toContain("text-amount");
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
  it("renders every proposal as a link to its detail page", async () => {
    stubFetchWithProposals();
    render(<ExplorePage />);
    expect(await screen.findByText("Kopi Senja")).toBeInTheDocument();
    expect(screen.getByText("Batik Lereng")).toBeInTheDocument();
    const links = screen.getAllByRole("link", { name: /baca proposal$/i });
    expect(links).toHaveLength(2);
    links.forEach((a) => expect(a.getAttribute("href")).toMatch(/^\/proposal\//));
  });

  it("gives the first proposal a larger nominal than the following ones", async () => {
    // Versi sebelumnya mengassert kartu biasa TIDAK memakai 1.75rem, yang
    // mengunci pelanggaran DESIGN.md: dokumen itu menetapkan 1.75rem sebagai
    // batas BAWAH nominal di setiap kartu, bukan sebagai hak istimewa kartu
    // pertama. Yang dijamin di sini adalah hierarkinya, bukan satu nilai rem
    // tertentu, sehingga skala boleh berubah tanpa test ini ikut berbohong.
    stubFetchWithProposals();
    render(<ExplorePage />);
    await screen.findByText("Kopi Senja");
    const urutan = ["text-amount", "text-amount-sm", "text-card-title"];
    const tingkat = (el: HTMLElement) =>
      urutan.findIndex((k) => el.className.split(" ").includes(k));

    const utama = tingkat(screen.getByText("Rp25.000.000"));
    const biasa = tingkat(screen.getByText("Rp15.000.000"));
    expect(utama, "nominal kartu pertama tidak memakai token skala").toBeGreaterThanOrEqual(0);
    expect(biasa, "nominal kartu kedua tidak memakai token skala").toBeGreaterThanOrEqual(0);
    expect(utama, "kartu pertama harus lebih besar, bukan sama").toBeLessThan(biasa);
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
      expect(source, `${berkas} memakai text-accent-2 sebagai warna teks lepas`).not.toMatch(
        /\btext-accent-2\b/,
      );
    }
  });
});
