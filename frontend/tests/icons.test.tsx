import { readFileSync } from "node:fs";
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Icon, NAMA_IKON, type IconName } from "@/components/icons/Icon";
import { SECTOR_ICON, SECTOR_LABEL } from "@/components/CampaignBrowseCard";

describe("the sector icon set stays in step with the sectors the backend defines", () => {
  // Sektor adalah enum di backend/app/models/campaign.py. Kalau satu sektor
  // ditambahkan di sana dan ikonnya tidak, kolom sektor di daftar campaign
  // akan menampilkan nama tanpa lambang sementara lima tetangganya punya --
  // kelihatan seperti data yang rusak, bukan seperti fitur yang belum jadi.
  it("has an icon for every sector that has a label", () => {
    expect(Object.keys(SECTOR_ICON).sort()).toEqual(Object.keys(SECTOR_LABEL).sort());
  });

  it("points every sector at an icon that actually exists", () => {
    Object.values(SECTOR_ICON).forEach((nama) => {
      expect(NAMA_IKON).toContain(nama);
    });
  });

  it("covers the six sectors the backend enum declares", () => {
    // Dibaca dari sumber backend, bukan disalin ulang di sini: menyalinnya
    // berarti pagar ini ikut salah pada hari enum-nya berubah.
    const model = readFileSync("../backend/app/models/campaign.py", "utf8");
    const blok = /class Sector\(StrEnum\):([\s\S]*?)\n\n/.exec(model)?.[1] ?? "";
    const sektor = [...blok.matchAll(/=\s*"([a-z_]+)"/g)].map((m) => m[1]).sort();
    expect(sektor.length).toBeGreaterThan(0);
    expect(Object.keys(SECTOR_ICON).sort()).toEqual(sektor);
  });
});

describe("every icon draws something and nothing more", () => {
  it.each(NAMA_IKON)("%s renders a path with real geometry", (nama: IconName) => {
    const { container } = render(<Icon name={nama} />);
    const path = container.querySelector("path");
    expect(path, `ikon ${nama} tidak menggambar apa pun`).not.toBeNull();
    const d = path!.getAttribute("d") ?? "";
    // Ambang 20 karakter: cukup untuk menolak jalur placeholder seperti
    // "M0 0" yang akan lolos pemeriksaan "ada path".
    expect(d.length, `jalur ikon ${nama} terlalu pendek untuk menggambar apa pun`).toBeGreaterThan(20);
  });

  it.each(NAMA_IKON)("%s stays inside the 24x24 grid", (nama: IconName) => {
    // Koordinat di luar kanvas akan terpotong diam-diam, dan ikonnya tampak
    // rusak hanya pada ukuran tertentu.
    //
    // Angka di dalam atribut d TIDAK bisa diperiksa apa adanya: perintah
    // huruf kecil (a, h, v, l) memakai SELISIH, bukan koordinat, dan
    // perintah busur menyelipkan jari-jari serta tiga tanda di antara
    // angkanya. Versi pertama pagar ini membandingkan setiap angka mentah
    // terhadap 0..24 dan menyatakan enam ikon yang benar sebagai rusak.
    // Jadi titiknya ditelusuri, bukan dibaca.
    const { container } = render(<Icon name={nama} />);
    const d = container.querySelector("path")!.getAttribute("d") ?? "";
    titikJalur(d).forEach(([x, y]) => {
      expect(x, `ikon ${nama} menggambar x=${x} di luar kanvas`).toBeGreaterThanOrEqual(-0.5);
      expect(x, `ikon ${nama} menggambar x=${x} di luar kanvas`).toBeLessThanOrEqual(24.5);
      expect(y, `ikon ${nama} menggambar y=${y} di luar kanvas`).toBeGreaterThanOrEqual(-0.5);
      expect(y, `ikon ${nama} menggambar y=${y} di luar kanvas`).toBeLessThanOrEqual(24.5);
    });
  });

  it("proves the canvas guard can fail, on a path drawn deliberately off-grid", () => {
    expect(titikJalur("M12 12L40 12")).toContainEqual([40, 12]);
    expect(titikJalur("M12 12l30 0")).toContainEqual([42, 12]);
  });
});

// Jumlah parameter per perintah jalur SVG. Hanya perintah yang benar-benar
// dipakai set ikon ini yang perlu benar, tapi daftarnya ditulis lengkap
// supaya ikon baru dengan kurva tetap tertangkap, bukan diam-diam dilewati.
const PARAM: Record<string, number> = {
  m: 2, l: 2, t: 2, h: 1, v: 1, c: 6, s: 4, q: 4, a: 7, z: 0,
};

function titikJalur(d: string): [number, number][] {
  const token = d.match(/[a-zA-Z]|-?\d*\.?\d+/g) ?? [];
  const titik: [number, number][] = [];
  let x = 0;
  let y = 0;
  let i = 0;
  let perintah = "";
  while (i < token.length) {
    if (/[a-zA-Z]/.test(token[i]!)) {
      perintah = token[i]!;
      i += 1;
    }
    const huruf = perintah.toLowerCase();
    const relatif = perintah === huruf;
    const n = PARAM[huruf];
    if (n === undefined) break;
    if (n === 0) continue;
    const arg = token.slice(i, i + n).map(Number);
    i += n;
    if (huruf === "h") {
      x = relatif ? x + arg[0]! : arg[0]!;
    } else if (huruf === "v") {
      y = relatif ? y + arg[0]! : arg[0]!;
    } else {
      // Titik akhir selalu dua angka terakhir, untuk garis, kurva, maupun busur.
      const [dx, dy] = [arg[n - 2]!, arg[n - 1]!];
      x = relatif ? x + dx : dx;
      y = relatif ? y + dy : dy;
    }
    titik.push([x, y]);
  }
  return titik;
}

describe("icons take colour and meaning from the text they sit next to", () => {
  it("inherits the surrounding text colour instead of carrying its own", () => {
    // currentColor, bukan warna tetap: ikon berwarna tetap akan memunculkan
    // pasangan warna yang belum pernah diukur begitu tema berganti.
    const { container } = render(<Icon name="kuliner" />);
    expect(container.querySelector("svg")).toHaveAttribute("stroke", "currentColor");
  });

  it("hides itself from screen readers when the text beside it already says the same thing", () => {
    const { container } = render(<Icon name="check" />);
    const svg = container.querySelector("svg")!;
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg.querySelector("title")).toBeNull();
  });

  it("becomes announceable only when it is given a title, for the case where it stands alone", () => {
    const { container } = render(<Icon name="check" title="Disetujui" />);
    const svg = container.querySelector("svg")!;
    expect(svg).toHaveAttribute("role", "img");
    expect(svg).not.toHaveAttribute("aria-hidden");
    expect(svg.querySelector("title")).toHaveTextContent("Disetujui");
  });
});
