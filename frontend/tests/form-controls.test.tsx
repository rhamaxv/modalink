import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Field } from "@/components/ui";

// Setiap kontrol formulir di aplikasi ini memakai satu definisi yang sama
// (.control di app/globals.css). Sebelum pagar ini ada, lima berkas menyalin
// string kelasnya masing-masing dan ketiganya sudah menyimpang: Field memakai
// border --ink (putih penuh di tema gelap), Select memakai --line-strong, dan
// tidak satu pun mencabut gaya bawaan sistem, sehingga panah <select>,
// pemilih tanggal, dan tombol naik-turun angka tetap digambar browser dengan
// warna terang di atas halaman hampir hitam.

function sumberTsx(dir: string): string[] {
  return readdirSync(dir).flatMap((nama) => {
    const penuh = path.join(dir, nama);
    if (statSync(penuh).isDirectory()) return sumberTsx(penuh);
    return penuh.endsWith(".tsx") ? [penuh] : [];
  });
}

const BERKAS = [...sumberTsx("app"), ...sumberTsx("components")];

// Hanya elemen formulir sungguhan. Tombol tidak ikut: ia punya komponennya
// sendiri (ui/Button.tsx) dengan varian yang memang berbeda-beda.
const ELEMEN = /<(input|select|textarea)\b/g;

// Komentar dibuang lebih dulu. Beberapa komentar di repo ini membahas
// kontrol formulir dengan menyebut "<input>" atau "<textarea>" sebagai kata,
// dan tanpa langkah ini kalimat penjelasan ikut dihitung sebagai pelanggaran.
function tanpaKomentar(sumber: string): string {
  return sumber.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/[^\n]*/g, "");
}

// Tag JSX tidak bisa dipotong dengan /<input[^>]*>/: atribut JSX memuat
// ekspresi seperti onChange={(event) => ...}, dan ">" milik panah fungsi itu
// mengakhiri pencocokan jauh sebelum tag-nya benar-benar selesai. Jadi
// dipindai maju sambil menghitung kurung kurawal, dan tag dianggap selesai
// pada ">" pertama yang berada di kedalaman nol.
function tagPembuka(sumber: string, mulai: number): string {
  let dalam = 0;
  for (let i = mulai; i < sumber.length; i += 1) {
    const c = sumber[i];
    if (c === "{") dalam += 1;
    else if (c === "}") dalam -= 1;
    else if (c === ">" && dalam === 0) return sumber.slice(mulai, i + 1);
  }
  return sumber.slice(mulai);
}

describe("every form control in the app uses the one shared definition", () => {
  it("gives each input, select, and textarea the control class", () => {
    const pelanggar: string[] = [];
    BERKAS.forEach((berkas) => {
      const sumber = tanpaKomentar(readFileSync(berkas, "utf8"));
      for (const cocok of sumber.matchAll(ELEMEN)) {
        const tag = tagPembuka(sumber, cocok.index ?? 0);
        // Kelas yang dioper lewat variabel dilewati di sini dan diperiksa
        // oleh test render di bawah, yang melihat DOM sungguhan.
        if (/className=\{[A-Za-z]/.test(tag)) continue;
        if (!/className="[^"]*\bcontrol\b/.test(tag)) {
          pelanggar.push(`${berkas}: ${tag.slice(0, 90).replace(/\s+/g, " ")}`);
        }
      }
    });
    expect(pelanggar, `kontrol formulir tanpa kelas .control:\n${pelanggar.join("\n")}`).toEqual([]);
  });

  it("leaves no copy of the old hand-written control styling behind", () => {
    // String persis yang dulu disalin ke lima berkas. Kalau ia muncul lagi,
    // berarti satu kontrol baru ditulis dengan menyalin tetangganya, bukan
    // dengan memakai definisi bersama.
    const pelanggar = BERKAS.filter((berkas) =>
      /border-ink bg-paper px-space-3 py-space-2/.test(
        tanpaKomentar(readFileSync(berkas, "utf8")),
      ),
    );
    expect(pelanggar).toEqual([]);
  });
});

describe("the shared control definition covers what the browser would otherwise draw itself", () => {
  const css = readFileSync("app/globals.css", "utf8");

  it("declares color-scheme in both themes, so system-drawn widgets follow the theme", () => {
    // Daftar pilihan yang terbuka dari <select>, pemilih tanggal, tombol
    // naik-turun angka, dan scrollbar digambar sistem operasi, bukan CSS
    // kita. Tanpa color-scheme, semuanya terang di atas halaman gelap.
    expect(css).toMatch(/:root\s*\{[^}]*color-scheme:\s*dark/);
    expect(css).toMatch(/\[data-theme="light"\]\s*\{[^}]*color-scheme:\s*light/);
  });

  it("strips the native appearance and draws its own select arrow", () => {
    expect(css).toMatch(/\.control\s*\{[^}]*appearance:\s*none/);
    expect(css).toMatch(/select\.control\s*\{[^}]*background-image:\s*var\(--chevron\)/);
  });

  it("defines the arrow colour per theme, because a data URI cannot read a CSS variable", () => {
    const chevron = [...css.matchAll(/--chevron:\s*url\([^)]*\)/g)];
    expect(chevron.length, "panah harus didefinisikan di tema gelap dan terang").toBe(2);
    expect(chevron[0]?.[0]).not.toBe(chevron[1]?.[0]);
  });

  it("uses line-strong for the control border, the token meant for interactive edges", () => {
    // Bukan --line (1.46:1, gagal ambang 3:1 untuk batas kontrol) dan bukan
    // lagi --ink yang putih penuh.
    expect(css).toMatch(/\.control\s*\{[^}]*border:\s*1px solid var\(--line-strong\)/);
  });

  it("makes aria-invalid visible, not just announced", () => {
    expect(css).toMatch(/\.control\[aria-invalid="true"\]\s*\{[^}]*border-color:\s*var\(--danger\)/);
  });

  it("keeps every control at the 44px touch target", () => {
    expect(css).toMatch(/\.control\s*\{[^}]*min-height:\s*44px/);
  });
});

describe("Field still wires label, error, and validity to the control it renders", () => {
  it("marks an invalid field so the shared styling can react to it", () => {
    render(
      <Field label="Email" value="bukan email" onChange={() => {}} error="Format email salah." />,
    );
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input.className).toContain("control");
    expect(screen.getByRole("alert")).toHaveTextContent("Format email salah.");
  });

  it("renders a select, not an input, when options are given", () => {
    render(
      <Field
        label="Peran"
        value="umkm"
        onChange={() => {}}
        options={[
          { value: "umkm", label: "UMKM" },
          { value: "investor", label: "Investor" },
        ]}
      />,
    );
    const select = screen.getByLabelText("Peran");
    expect(select.tagName).toBe("SELECT");
    expect(select.className).toContain("control");
  });
});
