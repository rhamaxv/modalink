import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CommentForm } from "@/components/CommentForm";
import { CommentList } from "@/components/CommentList";

function fakeResponse(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

function stubFetchByUrl(handlers: Record<string, () => Promise<Response>>) {
  vi.stubGlobal("fetch", (url: string, init?: RequestInit) => {
    const key = Object.keys(handlers).find((pattern) => url.includes(pattern));
    if (!key) throw new Error(`permintaan fetch tak terduga ke ${url} (${init?.method ?? "GET"})`);
    return handlers[key]!();
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("comment form", () => {
  it("rejects an empty comment with a message read by screen readers, and never sends it", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    render(<CommentForm proposalId="p1" />);
    await userEvent.click(screen.getByRole("button", { name: /kirim/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/komentar tidak boleh kosong/i);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("links the textarea to its error message via aria-describedby, so a screen reader hears why it is invalid", async () => {
    // Sebelumnya elemen galat tidak punya id dan textarea tidak punya
    // aria-describedby, jadi pembaca layar diberi tahu field ini salah
    // tanpa pernah diberi tahu alasannya (laporan tinjauan minggu ini).
    render(<CommentForm proposalId="p1" />);
    await userEvent.click(screen.getByRole("button", { name: /kirim/i }));
    const galat = await screen.findByRole("alert");
    const textarea = screen.getByLabelText(/komentar/i);
    expect(galat).toHaveAttribute("id");
    expect(textarea).toHaveAttribute("aria-describedby", galat.id);
  });

  it("sends a filled comment and notifies the parent through onKirim", async () => {
    const onKirim = vi.fn();
    stubFetchByUrl({
      "/comments": () =>
        fakeResponse(201, {
          id: "c9",
          proposal_id: "p1",
          user_id: "u-saya",
          body: "Usahanya meyakinkan.",
          created_at: "2026-11-07T10:00:00Z",
        }),
    });
    render(<CommentForm proposalId="p1" onKirim={onKirim} />);
    await userEvent.type(screen.getByLabelText(/komentar/i), "Usahanya meyakinkan.");
    await userEvent.click(screen.getByRole("button", { name: /kirim/i }));
    await waitFor(() => expect(onKirim).toHaveBeenCalledOnce());
    expect(screen.getByLabelText(/komentar/i)).toHaveValue("");
  });
});

describe("comment list", () => {
  it("shows a loading state before the comments arrive", () => {
    vi.stubGlobal("fetch", () => new Promise(() => {
      // Sengaja tidak pernah selesai, untuk mengamati keadaan memuat.
    }));
    render(<CommentList proposalId="p1" />);
    expect(screen.getByRole("status")).toHaveTextContent(/memuat/i);
  });

  it("shows a cause and a retry action when loading fails", async () => {
    vi.stubGlobal("fetch", () =>
      fakeResponse(500, { error: { code: "galat_server", message: "Gagal memuat komentar." } }),
    );
    render(<CommentList proposalId="p1" />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/gagal memuat komentar/i);
    expect(screen.getByRole("button", { name: /coba lagi/i })).toBeInTheDocument();
  });

  it("shows an empty state naming the cause and one action when there are no comments yet", async () => {
    stubFetchByUrl({
      "/comments": () => fakeResponse(200, { items: [] }),
    });
    render(<CommentList proposalId="p1" />);
    expect(await screen.findByText(/belum ada yang berkomentar/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /tulis komentar/i })).toBeInTheDocument();
  });

  // Jumlah dukungan sekarang ikut di amplop GET .../comments
  // (backend/app/schemas/community.py). Sebelumnya tidak, dan satu-satunya
  // sumbernya adalah respons POST /vote: artinya pengunjung yang belum pernah
  // menekan tombolnya selalu membaca "Jumlah dukungan belum tersedia",
  // termasuk pengunjung anonim yang memang tidak boleh menekannya sama
  // sekali, sehingga angka itu tidak pernah muncul untuk mereka.
  it("does not offer an anonymous visitor an action that is certain to be refused", async () => {
    // Bug yang dilaporkan pemilik project dengan tangkapan layar: halaman
    // proposal menampilkan tombol "Dukung proposal ini" kepada pengunjung
    // tanpa akun, dan menekannya membalas pesan mentah server "Token tidak
    // ada." tepat di bawahnya.
    stubFetchByUrl({
      "/comments": () => fakeResponse(200, { items: [], vote_count: 9, voted_by_me: null }),
    });
    render(<CommentList proposalId="p1" />);
    expect(await screen.findByText("9 dukungan")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /dukung proposal/i })).toBeNull();
    expect(
      screen.getByRole("link", { name: /masuk sebagai komunitas/i }),
    ).toHaveAttribute("href", "/masuk");
  });

  it("does not offer the action to a signed-in account whose role cannot vote", async () => {
    // Investor dan UMKM punya akun, tapi POST /vote hanya untuk peran
    // community (10-api-contract.md:82).
    stubFetchByUrl({
      "/comments": () => fakeResponse(200, { items: [], vote_count: 3, voted_by_me: false }),
    });
    render(<CommentList proposalId="p1" currentRole="investor" />);
    expect(await screen.findByText("3 dukungan")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /dukung proposal/i })).toBeNull();
  });

  it("shows a community account the real count and its own vote state on load", async () => {
    // Tanpa voted_by_me dari server, tombolnya selalu mulai "belum didukung",
    // dan akun yang sudah pernah mendukung baru menemukannya setelah menekan
    // tombol itu sekali lagi dan justru mencabut dukungannya sendiri.
    stubFetchByUrl({
      "/comments": () => fakeResponse(200, { items: [], vote_count: 12, voted_by_me: true }),
    });
    render(<CommentList proposalId="p1" currentRole="community" />);
    const voteButton = await screen.findByRole("button", { name: /dukungan anda tercatat/i });
    expect(voteButton).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("12 dukungan")).toBeInTheDocument();
  });

  it("toggles the vote and updates the count when clicked", async () => {
    stubFetchByUrl({
      "/vote": () => fakeResponse(200, { voted: true, vote_count: 6 }),
      "/comments": () => fakeResponse(200, { items: [], vote_count: 5, voted_by_me: false }),
    });
    render(<CommentList proposalId="p1" currentRole="community" />);
    const voteButton = await screen.findByRole("button", { name: /dukung proposal/i });
    expect(voteButton).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(voteButton);
    await waitFor(() => expect(voteButton).toHaveAttribute("aria-pressed", "true"));
    expect(screen.getByText("6 dukungan")).toBeInTheDocument();
  });

  it("never shows the raw server message when the session expired mid-visit", async () => {
    // Token bisa kedaluwarsa setelah halaman terbuka, jadi cabang 401 tetap
    // tercapai walau tombolnya hanya dirender untuk akun community. Yang
    // tidak boleh adalah kalimat internalnya sampai ke layar.
    stubFetchByUrl({
      "/vote": () =>
        fakeResponse(401, {
          error: { code: "tidak_terautentikasi", message: "Token tidak ada." },
        }),
      "/comments": () => fakeResponse(200, { items: [], vote_count: 1, voted_by_me: false }),
    });
    render(<CommentList proposalId="p1" currentRole="community" />);
    await userEvent.click(await screen.findByRole("button", { name: /dukung proposal/i }));
    const galat = await screen.findByRole("alert");
    expect(galat).toHaveTextContent(/sesi anda sudah berakhir/i);
    expect(screen.queryByText("Token tidak ada.")).toBeNull();
  });

  it("shows the delete button only on the comment that belongs to the signed-in account, matched by user_id", async () => {
    stubFetchByUrl({
      "/comments": () =>
        fakeResponse(200, {
          items: [
            { id: "c1", proposal_id: "p1", user_id: "u-saya", body: "Komentar milik saya.", created_at: "2026-11-07T10:00:00Z" },
            { id: "c2", proposal_id: "p1", user_id: "u-lain", body: "Komentar orang lain.", created_at: "2026-11-07T11:00:00Z" },
          ],
        }),
    });
    render(<CommentList proposalId="p1" currentUserId="u-saya" />);
    await screen.findByText("Komentar milik saya.");
    expect(screen.getAllByRole("button", { name: /hapus komentar/i })).toHaveLength(1);
  });

  it("shows no delete button at all for an anonymous visitor (no currentUserId)", async () => {
    stubFetchByUrl({
      "/comments": () =>
        fakeResponse(200, {
          items: [
            { id: "c1", proposal_id: "p1", user_id: "u-saya", body: "Komentar siapa pun.", created_at: "2026-11-07T10:00:00Z" },
          ],
        }),
    });
    render(<CommentList proposalId="p1" />);
    await screen.findByText("Komentar siapa pun.");
    expect(screen.queryByRole("button", { name: /hapus komentar/i })).toBeNull();
  });
});
