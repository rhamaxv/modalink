import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProposalList } from "@/components/ProposalCard";
import { Pagination, ResultCount } from "@/components/ui";

// Halaman jelajah dirombak dari halaman yang terlihat seperti landing page
// menjadi halaman indeks. Yang diuji di sini adalah bagian yang membuat
// rombakan itu berarti pada data bervolume: penyaring dan paginasi yang
// benar-benar sampai ke server, bukan yang cuma merapikan dua puluh baris
// yang sudah terlanjur diunduh.

function proposal(nama: string, nominal: number) {
  return {
    id: `id-${nama}`,
    campaign_id: "c1",
    umkm_id: "u1",
    business_name: nama,
    business_profile_excerpt: "Usaha rumahan yang sudah berjalan tiga tahun.",
    requested_amount: nominal,
    collected_amount: Math.round(nominal / 4),
    status: "listed",
    scoring_status: "done",
    lead_investor_id: null,
    funded_at: null,
    created_at: "2026-01-01T00:00:00Z",
  };
}

// Mengumpulkan setiap URL yang diminta, karena itulah bukti bahwa
// penyaringnya server-side: kalau filter dikerjakan di browser, URL-nya
// tidak akan pernah berubah.
function stubFetch(total: number, items = [proposal("Kopi Senja", 20_000_000)]) {
  const urls: string[] = [];
  vi.stubGlobal("fetch", (url: string) => {
    urls.push(url);
    return Promise.resolve(
      new Response(JSON.stringify({ items, total, page: 1, page_size: 20 }), { status: 200 }),
    );
  });
  return urls;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ProposalList sends its filters to the server, not to the browser", () => {
  it("asks for the default page with an explicit page size, never an unbounded list", async () => {
    const urls = stubFetch(54);
    render(<ProposalList />);
    await screen.findByText("Kopi Senja");
    expect(urls[0]).toContain("page=1");
    expect(urls[0]).toContain("page_size=20");
    expect(urls[0]).toContain("sort=newest");
  });

  it("refetches with sector in the query when the sector filter changes", async () => {
    const urls = stubFetch(54);
    render(<ProposalList />);
    await screen.findByText("Kopi Senja");

    await userEvent.selectOptions(screen.getByLabelText("Sektor"), "kerajinan");
    await waitFor(() => expect(urls.some((u) => u.includes("sector=kerajinan"))).toBe(true));
  });

  it("refetches with the chosen sort, so ordering survives beyond the current page", async () => {
    const urls = stubFetch(54);
    render(<ProposalList />);
    await screen.findByText("Kopi Senja");

    await userEvent.selectOptions(screen.getByLabelText("Urutkan"), "amount_desc");
    await waitFor(() => expect(urls.some((u) => u.includes("sort=amount_desc"))).toBe(true));
  });

  it("returns to page one when a filter changes", async () => {
    // Menyaring dari halaman 3 tanpa reset memberi daftar kosong yang
    // terlihat persis seperti "tidak ada hasil", padahal hasilnya ada di
    // halaman 1.
    const urls = stubFetch(54);
    render(<ProposalList />);
    await screen.findByText("Kopi Senja");

    await userEvent.click(screen.getByRole("button", { name: "Berikutnya" }));
    await waitFor(() => expect(urls.some((u) => u.includes("page=2"))).toBe(true));

    await userEvent.selectOptions(screen.getByLabelText("Sektor"), "kuliner");
    await waitFor(() => {
      const terakhir = urls[urls.length - 1] ?? "";
      expect(terakhir).toContain("sector=kuliner");
      expect(terakhir).toContain("page=1");
    });
  });

  it("tells the visitor how much of the whole list they are looking at", async () => {
    stubFetch(54);
    render(<ProposalList />);
    await screen.findByText("Kopi Senja");
    // Teks ini sengaja terpotong dua elemen: totalnya dibungkus <span>
    // beraksen sendiri, jadi pencocokannya lewat textContent gabungan.
    const baris = screen.getByText(/Menampilkan/).textContent ?? "";
    // Rentangnya dihitung dari page/page_size/total, bukan dari panjang
    // array yang kebetulan dikirim stub: itu memang yang benar, karena
    // server yang menentukan berapa baris satu halaman berisi.
    expect(baris).toContain("Menampilkan 1-20 dari");
    expect(baris).toContain("54");
  });

  it("explains an empty filtered result differently from an empty list", async () => {
    // "Belum ada proposal sama sekali" dan "tidak ada di sektor yang Anda
    // pilih" adalah dua keadaan berbeda, dan menyamakannya membuat
    // pengunjung menyimpulkan produk ini kosong.
    stubFetch(0, []);
    render(<ProposalList />);
    await screen.findByText("Belum ada proposal yang terbuka untuk didanai saat ini.");

    await userEvent.selectOptions(screen.getByLabelText("Sektor"), "teknologi");
    expect(
      await screen.findByText(/Tidak ada proposal terbuka di sektor itu/),
    ).toBeInTheDocument();
  });
});

describe("Pagination only appears when there is somewhere to go", () => {
  it("renders nothing when everything fits on one page", () => {
    const { container } = render(
      <Pagination page={1} pageSize={20} total={12} onPageChange={() => {}} label="x" />,
    );
    // Dua tombol mati di kedua sisi lebih membingungkan daripada tidak ada
    // tombol sama sekali.
    expect(container.innerHTML).toBe("");
  });

  it("disables the edges instead of letting the visitor walk off the list", async () => {
    const onPageChange = vi.fn();
    const { rerender } = render(
      <Pagination page={1} pageSize={20} total={54} onPageChange={onPageChange} label="x" />,
    );
    expect(screen.getByRole("button", { name: "Sebelumnya" })).toBeDisabled();
    expect(screen.getByText("Halaman 1 dari 3")).toBeInTheDocument();

    rerender(
      <Pagination page={3} pageSize={20} total={54} onPageChange={onPageChange} label="x" />,
    );
    expect(screen.getByRole("button", { name: "Berikutnya" })).toBeDisabled();
  });

  it("announces the page change, because nothing else tells a screen reader the list moved", () => {
    render(<Pagination page={2} pageSize={20} total={54} onPageChange={() => {}} label="x" />);
    expect(screen.getByText("Halaman 2 dari 3")).toHaveAttribute("aria-live", "polite");
  });
});

describe("ResultCount never claims the page is the whole list", () => {
  it("names the visible range and the real total", () => {
    render(<ResultCount page={2} pageSize={20} total={54} noun="proposal" />);
    expect(screen.getByText(/Menampilkan/).textContent).toContain("Menampilkan 21-40 dari");
  });

  it("clamps the last page to the total instead of promising rows that do not exist", () => {
    render(<ResultCount page={3} pageSize={20} total={54} noun="proposal" />);
    expect(screen.getByText(/Menampilkan/).textContent).toContain("Menampilkan 41-54 dari");
  });
});
