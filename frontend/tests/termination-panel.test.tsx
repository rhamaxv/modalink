import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TerminationPanel } from "@/components/TerminationPanel";

// Panel ini adalah satu-satunya jalan keluar dari jalan buntu yang sebelumnya
// ada: proposal yang dananya penuh tapi UMKM-nya berhenti melapor menahan
// sisa dana selamanya.

afterEach(() => vi.unstubAllGlobals());

function stubFetch(status = 200) {
  const panggilan: string[] = [];
  vi.stubGlobal("fetch", (url: string, init?: RequestInit) => {
    panggilan.push(`${init?.method ?? "GET"} ${url}`);
    return Promise.resolve(
      new Response(
        JSON.stringify(
          status === 200
            ? {}
            : { error: { code: "tahap_belum_macet", message: "Tahap berikutnya belum melewati tenggat laporannya." } },
        ),
        { status },
      ),
    );
  });
  return panggilan;
}

describe("before a termination is requested", () => {
  it("offers the control to the lead investor only", () => {
    const { container } = render(
      <TerminationPanel
        proposalId="p1"
        terminationRequestedAt={null}
        bolehMengajukan={false}
        akuUmkm
        onBerubah={() => {}}
      />,
    );
    // UMKM tidak melihat apa pun selama belum ada pengajuan: memberitahunya
    // bahwa tombol itu ada hanya menakutinya tanpa ada yang bisa dilakukan.
    expect(container.innerHTML).toBe("");
  });

  it("explains the consequence before asking for the click", async () => {
    render(
      <TerminationPanel
        proposalId="p1"
        terminationRequestedAt={null}
        bolehMengajukan
        akuUmkm={false}
        onBerubah={() => {}}
      />,
    );
    expect(screen.getByText(/tujuh hari untuk tetap melapor/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ajukan penghentian/i })).toBeInTheDocument();
  });

  it("sends the request and tells the page to reload itself", async () => {
    const panggilan = stubFetch();
    const onBerubah = vi.fn();
    render(
      <TerminationPanel
        proposalId="p1"
        terminationRequestedAt={null}
        bolehMengajukan
        akuUmkm={false}
        onBerubah={onBerubah}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /ajukan penghentian/i }));
    await waitFor(() => expect(onBerubah).toHaveBeenCalled());
    expect(panggilan.some((p) => p.includes("POST") && p.includes("/p1/terminate"))).toBe(true);
  });

  it("shows the server reason when the stage is not overdue yet", async () => {
    stubFetch(409);
    render(
      <TerminationPanel
        proposalId="p1"
        terminationRequestedAt={null}
        bolehMengajukan
        akuUmkm={false}
        onBerubah={() => {}}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /ajukan penghentian/i }));
    // 409 di sini penolakan yang SAH dan menjelaskan sesuatu, jadi pesannya
    // diteruskan apa adanya, bukan diganti kalimat generik.
    expect(await screen.findByRole("alert")).toHaveTextContent(/belum melewati tenggat/i);
  });
});

describe("while a termination is pending, both sides see the same clock", () => {
  const DIAJUKAN = "2026-11-11T00:00:00Z";

  it("tells the umkm what to do and by when", () => {
    render(
      <TerminationPanel
        proposalId="p1"
        terminationRequestedAt={DIAJUKAN}
        bolehMengajukan={false}
        akuUmkm
        onBerubah={() => {}}
      />,
    );
    expect(screen.getByText(/kirim laporan tahap berikutnya sebelum/i)).toBeInTheDocument();
    // 11 November + 7 hari.
    expect(screen.getByText(/18 November 2026/)).toBeInTheDocument();
  });

  it("tells the investor it is waiting, with the same date", () => {
    render(
      <TerminationPanel
        proposalId="p1"
        terminationRequestedAt={DIAJUKAN}
        bolehMengajukan
        akuUmkm={false}
        onBerubah={() => {}}
      />,
    );
    expect(screen.getByText(/menunggu jawaban umkm sampai/i)).toBeInTheDocument();
    expect(screen.getByText(/18 November 2026/)).toBeInTheDocument();
    // Tombolnya hilang: pengajuan kedua tidak berarti apa pun.
    expect(screen.queryByRole("button", { name: /ajukan penghentian/i })).toBeNull();
  });

  it("says plainly that disbursed money is not clawed back", () => {
    render(
      <TerminationPanel
        proposalId="p1"
        terminationRequestedAt={DIAJUKAN}
        bolehMengajukan
        akuUmkm={false}
        onBerubah={() => {}}
      />,
    );
    expect(screen.getByText(/dana yang sudah cair tidak ditarik kembali/i)).toBeInTheDocument();
  });
});
