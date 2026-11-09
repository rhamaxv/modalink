import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProposalDetailView } from "@/components/ProposalDetailView";

const PROPOSAL_ID = "p1";

function fakeResponse(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

function baseProposal(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: PROPOSAL_ID,
    campaign_id: "c1",
    umkm_id: "u-umkm-1",
    business_name: "Kopi Rakyat Nusantara",
    business_profile: "Usaha kopi rakyat yang sudah berjalan tiga tahun di Yogyakarta.",
    fund_usage_plan: "60% mesin roasting, 40% kemasan dan distribusi ke tiga kota baru.",
    business_projection: "Omzet diproyeksikan naik dua kali lipat dalam satu tahun.",
    requested_amount: 10_000_000,
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
    stubEndpoints({ proposal: baseProposal({ status: "funded" }) });
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

    expect(await screen.findByRole("alert")).toHaveTextContent("sisa Rp1.000.000");
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
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("composition rhythm (RHYTHM 3)", () => {
  it("never repeats the same section pattern on two consecutive sections", async () => {
    stubEndpoints({
      proposal: baseProposal({ status: "partially_funded" }),
      pledges: {
        items: [{ id: "pl1", proposal_id: PROPOSAL_ID, investor_id: "u-investor-9", amount: 4_000_000, status: "active", created_at: "2026-11-01T00:00:00Z" }],
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
});
