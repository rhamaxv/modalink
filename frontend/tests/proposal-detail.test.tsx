import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProposalDetailView } from "@/components/ProposalDetailView";

const PROPOSAL_ID = "p1";

function fakeResponse(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

// Mengambil elemen yang memakai --accent lewat kelas Tailwind apa pun
// (bg-accent, text-accent, border-l-accent, dst), bukan hanya "bg-accent":
// versi awal pagar ini hanya menggeledah "bg-accent" dan melewatkan
// border-l-accent sama sekali (terbukti saat border itu sempat dikembalikan
// untuk membuktikan pagar lain bisa merah). "accent-2" dan "on-accent"
// sengaja TIDAK cocok: keduanya token berbeda, bukan kemunculan --accent.
const KELAS_ACCENT = /^(?:bg|text|border|border-[trblxy])-accent$/;
function elemenBerakenAccent(container: HTMLElement): Element[] {
  return Array.from(container.querySelectorAll("*")).filter((el) =>
    el.className
      .toString()
      .split(/\s+/)
      .some((kelas) => KELAS_ACCENT.test(kelas)),
  );
}

function baseProposal(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: PROPOSAL_ID,
    campaign_id: "c1",
    umkm_id: "u-umkm-1",
    business_name: "Kopi Rakyat Nusantara",
    business_summary: "Usaha kopi rakyat yang sudah berjalan tiga tahun di Yogyakarta.",
    requested_amount: 10_000_000,
    // GET /proposals/{id} sungguhan mengirim ini publik dan sudah terhitung
    // di server (dikonfirmasi lewat verifikasi browser terhadap backend
    // sungguhan); ProposalDetailView membaca field ini langsung, bukan
    // menjumlahkan pledges.data sendiri lagi.
    collected_amount: 0,
    status: "listed",
    scoring_status: "done",
    lead_investor_id: null,
    funded_at: null,
    created_at: "2026-10-01T08:00:00Z",
    ...overrides,
  };
}

function baseScore() {
  return {
    id: "s1",
    proposal_id: PROPOSAL_ID,
    engine_name: "gemini",
    model_name: "gemini-2.5-flash",
    fit_score: 34,
    data_quality_score: 21,
    impact_score: 18,
    total_score: 73,
    threshold_used: 60,
    red_flags: [],
    brief: {
      strengths: ["Usaha berjalan 3 tahun."],
      risks: ["Proyeksi agresif."],
      recommendation: "Minta rincian asumsi proyeksi.",
    },
    verdict: "listed",
    latency_ms: 1200,
    created_at: "2026-11-07T10:00:00Z",
  };
}

type FetchMap = {
  proposal?: unknown;
  proposalStatus?: number;
  scoring?: unknown;
  scoringStatus?: number;
  pledges?: unknown;
  pledgesStatus?: number;
  milestones?: unknown;
  comments?: unknown;
  me?: unknown;
  meStatus?: number;
  pledgeCreateStatus?: number;
  pledgeCreateBody?: unknown;
};

function stubEndpoints(map: FetchMap) {
  vi.stubGlobal("fetch", (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (method === "POST" && url.endsWith("/pledges")) {
      return fakeResponse(map.pledgeCreateStatus ?? 201, map.pledgeCreateBody ?? {});
    }
    if (url.endsWith("/auth/me")) {
      return fakeResponse(map.meStatus ?? 200, map.me ?? { id: "u-investor-1", name: "Investor", role: "investor" });
    }
    if (url.endsWith("/scoring")) {
      return fakeResponse(map.scoringStatus ?? 200, map.scoring ?? baseScore());
    }
    if (url.endsWith("/pledges")) {
      return fakeResponse(
        map.pledgesStatus ?? 200,
        map.pledges ?? { items: [] },
      );
    }
    if (url.endsWith("/milestones")) {
      return fakeResponse(200, map.milestones ?? { items: [] });
    }
    if (url.endsWith("/comments")) {
      return fakeResponse(200, map.comments ?? { items: [] });
    }
    if (url.includes(`/proposals/${PROPOSAL_ID}`)) {
      return fakeResponse(map.proposalStatus ?? 200, map.proposal ?? baseProposal());
    }
    throw new Error(`permintaan fetch tak terduga ke ${url} (${method})`);
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  try {
    localStorage.clear();
  } catch {
    // tidak relevan di lingkungan tanpa localStorage.
  }
});

describe("proposal detail page", () => {
  it("links to the proposal document, because that is where the actual proposal lives", async () => {
    // Satu-satunya jalan investor membaca isi proposal sejak uraiannya
    // pindah ke PDF. Tanpa tautan ini, yang tersisa di halaman hanyalah
    // ringkasan satu kalimat dan skor AI -- meminta orang mendanai
    // berdasarkan angka tanpa pernah bisa memeriksa dasarnya.
    stubEndpoints({ proposal: baseProposal({ status: "listed" }) });
    render(<ProposalDetailView proposalId={PROPOSAL_ID} />);
    const tautan = await screen.findByRole("link", { name: /buka dokumen proposal/i });
    expect(tautan).toHaveAttribute("href", expect.stringContaining(`/proposals/${PROPOSAL_ID}/document`));
    // Tab baru: halaman proposal punya formulir pendanaan yang mungkin
    // sudah separuh diisi, dan menimpanya dengan pembaca PDF berarti
    // kehilangan isian itu tanpa peringatan.
    expect(tautan).toHaveAttribute("target", "_blank");
    expect(tautan.getAttribute("rel")).toContain("noopener");
  });

  it("shows the score panel waiting, not an empty panel and not a zero, while scoring is unfinished", async () => {
    stubEndpoints({
      proposal: baseProposal({ status: "submitted", scoring_status: "processing" }),
    });
    localStorage.setItem("modalink_token", "token-palsu");
    render(<ProposalDetailView proposalId={PROPOSAL_ID} />);

    expect(await screen.findByText(/sedang dinilai/i)).toBeInTheDocument();
    expect(screen.queryByText("0")).toBeNull();
  });

  it("hides the pledge form entirely for a proposal that is already funded, and names the reason", async () => {
    stubEndpoints({ proposal: baseProposal({ status: "funded", collected_amount: 10_000_000 }) });
    localStorage.setItem("modalink_token", "token-palsu");
    render(<ProposalDetailView proposalId={PROPOSAL_ID} />);

    await screen.findByText("73");
    expect(screen.queryByRole("button", { name: /danai/i })).toBeNull();
    expect(screen.getByText(/sudah tercapai/i)).toBeInTheDocument();
  });

  it("shows the server message as is, including the remaining amount, when a pledge exceeds what is left", async () => {
    stubEndpoints({
      pledgeCreateStatus: 409,
      pledgeCreateBody: {
        error: {
          code: "pledge_melebihi_sisa",
          message: "Pledge melebihi sisa dana yang dibutuhkan, sisa Rp1.000.000.",
          detail: { remaining_amount: 1_000_000 },
        },
      },
    });
    localStorage.setItem("modalink_token", "token-palsu");
    render(<ProposalDetailView proposalId={PROPOSAL_ID} />);

    const nominal = await screen.findByLabelText(/nominal/i);
    await userEvent.type(nominal, "5000000");
    await userEvent.click(screen.getByRole("button", { name: /danai/i }));

    // Dipersempit ke pesan form pledge: halaman ini sekarang juga memuat
    // riwayat dana, dan stub di test ini tidak melayani /ledger sehingga
    // bagian itu menampilkan keadaan galatnya sendiri -- dua role="alert"
    // di satu halaman, keduanya benar.
    const galat = await screen.findAllByRole("alert");
    expect(galat.map((el) => el.textContent).join(" ")).toContain("sisa Rp1.000.000");
  });

  it("hides the pledge form for an UMKM account on its own proposal while still showing the score panel, and shows both for an investor", async () => {
    stubEndpoints({ me: { id: "u-umkm-1", name: "Pemilik Usaha", role: "umkm" } });
    localStorage.setItem("modalink_token", "token-umkm");
    const { unmount } = render(<ProposalDetailView proposalId={PROPOSAL_ID} />);

    await screen.findByText("73");
    expect(screen.queryByRole("button", { name: /danai/i })).toBeNull();
    unmount();

    stubEndpoints({ me: { id: "u-investor-1", name: "Investor", role: "investor" } });
    render(<ProposalDetailView proposalId={PROPOSAL_ID} />);

    await screen.findByText("73");
    expect(screen.getByRole("button", { name: /danai/i })).toBeInTheDocument();
  });

  // GET .../pledges dan GET .../scoring (10-api-contract.md:59,67) menolak
  // pemanggil tanpa token dengan 401 "Token tidak ada." -- bukan kasus
  // langka: ini persis apa yang terjadi saat seorang juri tanpa akun
  // membuka /jelajah lalu mengklik satu proposal, jalur paling umum ke
  // halaman ini. Sebelumnya pesan 401 mentah itu tampil persis di tempat
  // bilah funding dan panel skor seharusnya berada (laporan Fase 11 Task
  // 12, ditemukan lewat e2e jalur anonim karena tidak ada test unit yang
  // pernah merender komponen ini tanpa token di localStorage sebelumnya).
  it("never shows a raw 401 where the funding bar or score panel belong, for a visitor with no account", async () => {
    stubEndpoints({
      pledgesStatus: 401,
      pledges: { error: { code: "tidak_terautentikasi", message: "Token tidak ada." } },
      scoringStatus: 401,
      scoring: { error: { code: "tidak_terautentikasi", message: "Token tidak ada." } },
    });
    // Sengaja tidak menyetel modalink_token: ini pengunjung anonim.
    render(<ProposalDetailView proposalId={PROPOSAL_ID} />);

    await screen.findByRole("heading", { name: /kopi rakyat nusantara/i });
    // findByText, bukan getByText: pledges dan scoring diambil lewat efek
    // terpisah yang baru terpicu dan baru gagal (lalu memutuskan "forbidden")
    // beberapa microtask setelah heading proposal sendiri sudah tampil, jadi
    // memeriksa dengan getByText yang sinkron sempat flaky di sini.
    await screen.findByText(/masuk sebagai investor, atau sebagai umkm pemilik proposal ini/i);
    await screen.findByText(/panel skor hanya terlihat oleh investor/i);
    expect(screen.queryByText(/token tidak ada/i)).toBeNull();
    expect(
      screen.queryAllByRole("alert").filter((el) => /pledge|sisa/i.test(el.textContent ?? "")),
    ).toHaveLength(0);
  });

  it("shows real funding progress to a visitor with no account, even though the per-funder list stays gated", async () => {
    // GET /proposals/{id} sungguhan (dibuktikan lewat permintaan langsung ke
    // backend saat verifikasi browser) mengirim collected_amount publik,
    // tanpa token, untuk proposal listed ke atas. Sebelumnya seluruh bilah
    // funding dihitung dari pledges.data (yang butuh login), jadi pengunjung
    // tanpa akun tidak pernah melihat progres dananya sama sekali, padahal
    // kartu proposal di /jelajah sudah menampilkannya ke publik.
    stubEndpoints({
      proposal: baseProposal({ status: "listed", collected_amount: 4_000_000 }),
      pledgesStatus: 401,
      pledges: { error: { code: "tidak_terautentikasi", message: "Token tidak ada." } },
      scoringStatus: 401,
      scoring: { error: { code: "tidak_terautentikasi", message: "Token tidak ada." } },
    });
    render(<ProposalDetailView proposalId={PROPOSAL_ID} />);

    await screen.findByText("Rp4.000.000");
    expect(screen.getByText(/dari Rp10.000.000/)).toBeInTheDocument();
    // Jumlah pendana tetap tidak tampil: itu satu-satunya bagian yang
    // sungguh butuh GET .../pledges yang digerbang login.
    expect(screen.queryByText(/investor$/i)).toBeNull();
    await screen.findByText(/masuk sebagai investor, atau sebagai umkm pemilik proposal ini/i);
  });

  it("renders the funder list without crashing when the backend anonymises investor_id to null", async () => {
    // GET .../pledges sungguhan (dibuktikan lewat permintaan langsung ke
    // backend saat verifikasi browser, bukan ditaksir dari dokumen) mengirim
    // investor_id: null untuk menganonimkan pemberi dana lain, dan
    // is_lead_investor sebagai gantinya. Kode lama memanggil
    // pledge.investor_id.slice(-4) langsung dan meledak dengan "Cannot read
    // properties of null (reading 'slice')" persis saat investor sungguhan
    // membuka proposal berpendana.
    stubEndpoints({
      proposal: baseProposal({ status: "partially_funded", collected_amount: 4_000_000 }),
      pledges: {
        items: [
          { id: "pl1", proposal_id: PROPOSAL_ID, investor_id: null, amount: 4_000_000, status: "active", created_at: "2026-11-01T00:00:00Z", is_lead_investor: true },
        ],
      },
    });
    localStorage.setItem("modalink_token", "token-palsu");
    render(<ProposalDetailView proposalId={PROPOSAL_ID} />);

    expect(await screen.findByText(/pendana ke-1/i)).toBeInTheDocument();
    expect(screen.getByText(/investor utama/i)).toBeInTheDocument();
  });

  it("never shows the score loading spinner at the same time as the waiting-for-score panel: one live region, not two", async () => {
    // Sebelumnya "score === null" berarti dua hal sekaligus: "belum diminta
    // ke server" dan "sengaja tidak ada yang diminta karena scoring_status
    // belum done". Kedua guard memeriksa literal yang sama, jadi LoadingState
    // dan ScorePanel keadaan menunggu/gagal dua-duanya ikut lolos dan
    // merender berdampingan, masing-masing aria-live mengumumkan sesuatu
    // yang berbeda (tinjauan minggu ini). Discriminated union ScoreState
    // memisahkan "loading" dari "idle" supaya hanya satu cabang yang benar.
    stubEndpoints({
      proposal: baseProposal({ status: "submitted", scoring_status: "processing" }),
    });
    localStorage.setItem("modalink_token", "token-palsu");
    render(<ProposalDetailView proposalId={PROPOSAL_ID} />);

    await screen.findByText(/sedang dinilai/i);
    expect(screen.queryByText(/memuat hasil penilaian/i)).toBeNull();
  });

  it("updates the pledge form's remaining amount after a successful pledge, without needing a failed attempt first", async () => {
    // PledgeForm menyimpan sisa lewat useState(sisa) sekali di mount dan
    // sebelumnya tidak pernah disinkron ulang, dan ProposalDetailView tidak
    // memasang key apa pun padanya. Satu-satunya jalan form tahu sisa yang
    // benar adalah lewat gagal dulu (409 membawa remaining_amount). key={sisa}
    // memaksa form remount dengan sisa terbaru begitu pledges berhasil
    // dimuat ulang setelah pledge SUKSES, bukan hanya setelah gagal.
    let pledgesSoFar: unknown[] = [];
    vi.stubGlobal("fetch", (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.endsWith("/auth/me")) {
        return fakeResponse(200, { id: "u-investor-1", name: "Investor", role: "investor" });
      }
      if (url.endsWith("/scoring")) return fakeResponse(200, baseScore());
      if (method === "POST" && url.endsWith("/pledges")) {
        // investor_id null + is_lead_investor: bentuk persis respons POST
        // .../pledges sungguhan (dikonfirmasi lewat verifikasi browser),
        // bukan string investor_id yang dulu diasumsikan tipe lama.
        const pledge = {
          id: "pl9",
          proposal_id: PROPOSAL_ID,
          investor_id: null,
          amount: 4_000_000,
          status: "active",
          created_at: "2026-11-07T12:00:00Z",
          is_lead_investor: true,
        };
        pledgesSoFar = [...pledgesSoFar, pledge];
        return fakeResponse(201, pledge);
      }
      if (url.endsWith("/pledges")) return fakeResponse(200, { items: pledgesSoFar });
      if (url.endsWith("/milestones")) return fakeResponse(200, { items: [] });
      if (url.endsWith("/comments")) return fakeResponse(200, { items: [] });
      if (url.includes(`/proposals/${PROPOSAL_ID}`)) {
        // collected_amount dihitung dari pledgesSoFar supaya proposal yang
        // dimuat ulang (muatProposal() di dalam onSukses) benar-benar
        // mencerminkan pledge yang baru dikirim, persis seperti backend
        // sungguhan yang menghitungnya di server.
        const terkumpulSoFar = (pledgesSoFar as { amount: number }[]).reduce(
          (total, p) => total + p.amount,
          0,
        );
        return fakeResponse(200, baseProposal({ status: "listed", collected_amount: terkumpulSoFar }));
      }
      throw new Error(`permintaan fetch tak terduga ke ${url} (${method})`);
    });

    localStorage.setItem("modalink_token", "token-palsu");
    render(<ProposalDetailView proposalId={PROPOSAL_ID} />);

    const nominal = await screen.findByLabelText(/nominal/i);
    expect(screen.getByText(/maksimal Rp10.000.000/i)).toBeInTheDocument();
    await userEvent.type(nominal, "4000000");
    await userEvent.click(screen.getByRole("button", { name: /danai/i }));

    await waitFor(() => expect(screen.getByText(/maksimal Rp6.000.000/i)).toBeInTheDocument());
    expect(screen.getByLabelText(/nominal/i)).toHaveValue("");
  });

  it("marks the active milestone with the accent badge only, never also an accent-coloured border", async () => {
    // Versi sebelumnya memasang border-l-4 border-l-accent DAN badge aksen
    // pada tahap yang sama, menghabiskan dua dari tiga jatah --accent untuk
    // satu ide, dan DESIGN.md mengecualikan aksen dari border kartu secara
    // eksplisit.
    stubEndpoints({
      proposal: baseProposal({ status: "partially_funded" }),
      milestones: {
        items: [
          { id: "m1", seq: 1, title: "Pembelian mesin", description: "x", amount: 5_000_000, status: "pending" },
        ],
      },
    });
    localStorage.setItem("modalink_token", "token-palsu");
    render(<ProposalDetailView proposalId={PROPOSAL_ID} />);

    const badge = await screen.findByText(/tahap aktif/i);
    expect(badge.className).toMatch(/bg-accent/);
    const baris = badge.closest("li");
    expect(baris?.className ?? "").not.toMatch(/border-l-accent/);
  });

  it("spends the accent colour on at most three elements, counted with the pledge button in its real enabled state after typing", async () => {
    // DESIGN.md membatasi tiga kemunculan --accent per layar: bilah funding,
    // tombol aksi utama, penanda milestone aktif. Audit browser sebelumnya
    // menghitung empat setelah nominal diketik, karena tombol disabled
    // tampil sebagai bg-panel (lewat variant disabled: CSS, bukan lewat DOM)
    // sehingga hitungan saat idle menyesatkan. Test ini menghitung di kedua
    // keadaan: idle (tombol benar-benar disabled, tidak dihitung) dan
    // setelah nominal valid diketik (tombol benar-benar enabled, dihitung).
    stubEndpoints({
      proposal: baseProposal({ status: "partially_funded", collected_amount: 4_000_000 }),
      pledges: {
        items: [
          { id: "pl1", proposal_id: PROPOSAL_ID, investor_id: null, amount: 4_000_000, status: "active", created_at: "2026-11-01T00:00:00Z", is_lead_investor: true },
        ],
      },
      milestones: {
        items: [
          { id: "m1", seq: 1, title: "Pembelian mesin", description: "x", amount: 5_000_000, status: "pending" },
        ],
      },
    });
    localStorage.setItem("modalink_token", "token-palsu");
    const { container } = render(<ProposalDetailView proposalId={PROPOSAL_ID} />);

    await screen.findByText(/tahap aktif/i);
    const nominal = await screen.findByLabelText(/nominal/i);
    const tombolDanai = screen.getByRole("button", { name: /danai/i });

    expect(tombolDanai).toBeDisabled();
    const kandidatIdle = elemenBerakenAccent(container).filter((el) => el !== tombolDanai);
    expect(kandidatIdle).toHaveLength(2); // bilah funding + badge tahap aktif

    await userEvent.type(nominal, "1000000");
    await waitFor(() => expect(tombolDanai).toBeEnabled());
    expect(elemenBerakenAccent(container)).toHaveLength(3); // + tombol yang sekarang sungguh lime
  });
});

describe("composition rhythm (RHYTHM 3)", () => {
  it("never repeats the same section pattern on two consecutive sections", async () => {
    stubEndpoints({
      proposal: baseProposal({ status: "partially_funded", collected_amount: 4_000_000 }),
      pledges: {
        items: [{ id: "pl1", proposal_id: PROPOSAL_ID, investor_id: null, amount: 4_000_000, status: "active", created_at: "2026-11-01T00:00:00Z", is_lead_investor: true }],
      },
      milestones: {
        items: [
          { id: "m1", seq: 1, title: "Pembelian mesin", description: "Membeli mesin roasting baru.", amount: 5_000_000, status: "pending" },
          { id: "m2", seq: 2, title: "Distribusi", description: "Distribusi ke tiga kota.", amount: 5_000_000, status: "pending" },
        ],
      },
      comments: {
        items: [{ id: "c1", proposal_id: PROPOSAL_ID, user_id: "u-lain", body: "Mantap.", created_at: "2026-11-02T00:00:00Z" }],
      },
    });
    localStorage.setItem("modalink_token", "token-palsu");
    render(<ProposalDetailView proposalId={PROPOSAL_ID} />);

    await screen.findByText("73");
    await screen.findByText("Pembelian mesin");
    await screen.findByText("Mantap.");

    const pola = Array.from(document.querySelectorAll("[data-pola]")).map((el) =>
      el.getAttribute("data-pola"),
    );
    expect(pola.length).toBeGreaterThanOrEqual(7);
    for (let i = 1; i < pola.length; i += 1) {
      expect(pola[i]).not.toBe(pola[i - 1]);
    }
  });

  it("never gives two differently-labelled sections the exact same computed class, and keeps 'dua-kolom-asimetris' a real two-column grid", async () => {
    // Audit browser sebelumnya menemukan section berlabel "dua-kolom-asimetris"
    // yang class komputasinya "flex flex-col gap-space-3", satu kolom biasa,
    // dan section lain (daftar-bernomor) berlabel berbeda dengan class yang
    // persis sama. Label hanya jujur kalau class-nya memang berbeda DAN kalau
    // "dua kolom asimetris" sungguh grid dua kolom, bukan sekadar nama.
    stubEndpoints({ proposal: baseProposal({ status: "partially_funded" }) });
    localStorage.setItem("modalink_token", "token-palsu");
    render(<ProposalDetailView proposalId={PROPOSAL_ID} />);

    await screen.findByText("73");
    const sections = Array.from(document.querySelectorAll<HTMLElement>("[data-pola]"));
    const classPerLabel = sections.map((el) => [el.getAttribute("data-pola"), el.className] as const);
    const classSet = new Set(classPerLabel.map(([, className]) => className));
    expect(classSet.size).toBe(classPerLabel.length);

    const duaKolom = sections.find((el) => el.getAttribute("data-pola") === "dua-kolom-asimetris");
    expect(duaKolom?.className).toMatch(/\bgrid\b/);
    expect(duaKolom?.className).toMatch(/grid-cols-\[2fr_1fr\]/);
  });
});
