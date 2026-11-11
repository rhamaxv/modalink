import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { KycForm } from "@/components/KycForm";

function fakeResponse(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

const TERVERIFIKASI = {
  status: "verified",
  full_name: "Nama Pemilik Akun",
  nik_last4: "1234",
  bank_code: "bca",
  account_holder_name: "Nama Pemilik Rekening",
  account_last4: "5678",
  rejection_reason: null,
  submitted_at: "2026-11-11T03:00:00Z",
  verifikasi_simulasi: true,
};

const DITOLAK = {
  ...TERVERIFIKASI,
  status: "rejected",
  rejection_reason: "Kode wilayah pada NIK tidak sah.",
};

type Panggilan = { url: string; init?: RequestInit };

// GET /kyc/me dan POST /kyc adalah dua endpoint berbeda dengan dua jawaban
// berbeda, jadi stub ini memisahkannya seperti backend sungguhan, bukan
// membalas satu bentuk untuk keduanya. Daftar panggilan dikembalikan supaya
// test bisa memeriksa bodi yang sungguh terkirim, bukan hanya akibatnya di
// layar.
function stubKyc(opsi: {
  me: () => Promise<Response>;
  submit?: () => Promise<Response>;
}): Panggilan[] {
  const panggilan: Panggilan[] = [];
  vi.stubGlobal("fetch", (url: string, init?: RequestInit) => {
    panggilan.push({ url, init });
    if (url.endsWith("/kyc/me")) return opsi.me();
    if (url.endsWith("/kyc")) {
      if (!opsi.submit) throw new Error("POST /kyc tidak diharapkan di test ini");
      return opsi.submit();
    }
    throw new Error(`permintaan fetch tak terduga ke ${url}`);
  });
  return panggilan;
}

async function isiFormulir() {
  await userEvent.type(screen.getByLabelText(/^Nama sesuai identitas/), "Nama Pemilik Akun");
  await userEvent.type(screen.getByLabelText(/^NIK/), "3201234567890123");
  await userEvent.selectOptions(screen.getByLabelText(/^Bank/), "bca");
  await userEvent.type(
    screen.getByLabelText(/^Nama pemilik rekening/),
    "Nama Pemilik Rekening",
  );
  await userEvent.type(screen.getByLabelText(/^Nomor rekening/), "1234567890");
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("kyc form load states", () => {
  it("announces what it is loading while the request is in flight", () => {
    stubKyc({
      me: () =>
        new Promise(() => {
          // Sengaja tidak pernah selesai, untuk mengamati keadaan memuat.
        }),
    });
    render(<KycForm />);
    expect(screen.getByTestId("loading-state")).toHaveTextContent(/memuat status verifikasi/i);
  });

  it("shows the backend message and one retry button when loading fails", async () => {
    stubKyc({
      me: () =>
        fakeResponse(503, {
          error: { code: "jaringan_bermasalah", message: "Koneksi ke server bermasalah." },
        }),
    });
    render(<KycForm />);
    const galat = await screen.findByRole("alert");
    expect(galat).toHaveTextContent("Koneksi ke server bermasalah.");
    expect(screen.getByRole("button", { name: /coba lagi/i })).toBeInTheDocument();
  });

  it("retries the request when the retry button is pressed", async () => {
    const panggilan = stubKyc({
      me: () => fakeResponse(500, { error: { code: "galat_server", message: "Server bermasalah." } }),
    });
    render(<KycForm />);
    await userEvent.click(await screen.findByRole("button", { name: /coba lagi/i }));
    await vi.waitFor(() => {
      expect(panggilan.filter((p) => p.url.endsWith("/kyc/me")).length).toBeGreaterThan(1);
    });
  });

  it("treats a 404 as never submitted, not as an error, and shows the form", async () => {
    // GET /kyc/me menjawab 404 ketika akun belum pernah mengajukan. Itu
    // jawaban, bukan kegagalan: menampilkan keadaan galat di sini akan
    // menghalangi pengguna dari satu-satunya formulir yang bisa
    // memperbaikinya.
    stubKyc({
      me: () => fakeResponse(404, { error: { code: "kyc_belum_ada", message: "Belum ada." } }),
    });
    render(<KycForm />);
    expect(await screen.findByLabelText(/^Nama sesuai identitas/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^NIK/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Bank/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Nama pemilik rekening/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Nomor rekening/)).toBeInTheDocument();
    expect(screen.queryByText(/identitas terverifikasi/i)).not.toBeInTheDocument();
  });
});

describe("kyc form honesty statement", () => {
  it("says on screen that the verification is a simulation, in every load state", async () => {
    // Pernyataan ini wajib dan tidak boleh hilang justru di keadaan galat,
    // ketika satu-satunya yang tersisa di layar adalah tombol coba lagi.
    stubKyc({
      me: () => fakeResponse(500, { error: { code: "galat_server", message: "Server bermasalah." } }),
    });
    render(<KycForm />);
    expect(screen.getByText(/verifikasi ini simulasi/i)).toBeInTheDocument();
    expect(screen.getByText(/tidak ada pengecekan ke dukcapil/i)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /coba lagi/i })).toBeInTheDocument();
    expect(screen.getByText(/verifikasi ini simulasi/i)).toBeInTheDocument();
  });

  it("says that the nik and the account number are not stored in full", () => {
    stubKyc({
      me: () =>
        new Promise(() => {
          // Keadaan memuat cukup: kalimat ini tidak bergantung pada data.
        }),
    });
    render(<KycForm />);
    expect(screen.getByText(/tidak disimpan utuh/i)).toBeInTheDocument();
  });
});

describe("kyc form submission", () => {
  it("sends every field the endpoint expects, with the bank code and not its label", async () => {
    const panggilan = stubKyc({
      me: () => fakeResponse(404, { error: { code: "kyc_belum_ada", message: "Belum ada." } }),
      submit: () => fakeResponse(200, TERVERIFIKASI),
    });
    render(<KycForm />);
    await screen.findByLabelText(/^Nama sesuai identitas/);
    await isiFormulir();
    await userEvent.click(screen.getByRole("button", { name: /kirim pengajuan/i }));

    await vi.waitFor(() => {
      expect(panggilan.some((p) => p.url.endsWith("/kyc") && p.init?.method === "POST")).toBe(true);
    });
    const kirim = panggilan.find((p) => p.url.endsWith("/kyc") && p.init?.method === "POST");
    expect(JSON.parse(String(kirim?.init?.body))).toEqual({
      full_name: "Nama Pemilik Akun",
      nik: "3201234567890123",
      bank_code: "bca",
      account_holder_name: "Nama Pemilik Rekening",
      account_number: "1234567890",
    });
  });

  it("never submits a bank the user did not pick", async () => {
    // Opsi pertama di <select> adalah penanda kosong, bukan BCA: bank yang
    // kebetulan paling atas di daftar bukan jawaban pengguna.
    stubKyc({
      me: () => fakeResponse(404, { error: { code: "kyc_belum_ada", message: "Belum ada." } }),
    });
    render(<KycForm />);
    await screen.findByLabelText(/^Nama sesuai identitas/);
    await userEvent.type(screen.getByLabelText(/^Nama sesuai identitas/), "Nama Pemilik Akun");
    await userEvent.type(screen.getByLabelText(/^NIK/), "3201234567890123");
    await userEvent.type(
      screen.getByLabelText(/^Nama pemilik rekening/),
      "Nama Pemilik Rekening",
    );
    await userEvent.type(screen.getByLabelText(/^Nomor rekening/), "1234567890");
    await userEvent.click(screen.getByRole("button", { name: /kirim pengajuan/i }));

    const pesan = await screen.findByRole("alert");
    expect(pesan).toHaveTextContent(/pilih bank/i);
    const bank = screen.getByLabelText(/^Bank/);
    expect(bank).toHaveAttribute("aria-invalid", "true");
    expect(document.getElementById(bank.getAttribute("aria-describedby") ?? "")).toHaveTextContent(
      /pilih bank/i,
    );
  });

  it("shows the server message as is when the submission is rejected with 422", async () => {
    stubKyc({
      me: () => fakeResponse(404, { error: { code: "kyc_belum_ada", message: "Belum ada." } }),
      submit: () =>
        fakeResponse(422, {
          error: { code: "nik_tidak_sah", message: "Pemilik NIK harus berusia minimal 17 tahun." },
        }),
    });
    render(<KycForm />);
    await screen.findByLabelText(/^Nama sesuai identitas/);
    await isiFormulir();
    await userEvent.click(screen.getByRole("button", { name: /kirim pengajuan/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Pemilik NIK harus berusia minimal 17 tahun.",
    );
  });

  it("replaces the form with the summary of what was just recorded", async () => {
    stubKyc({
      me: () => fakeResponse(404, { error: { code: "kyc_belum_ada", message: "Belum ada." } }),
      submit: () => fakeResponse(200, TERVERIFIKASI),
    });
    render(<KycForm />);
    await screen.findByLabelText(/^Nama sesuai identitas/);
    await isiFormulir();
    await userEvent.click(screen.getByRole("button", { name: /kirim pengajuan/i }));
    expect(await screen.findByText(/identitas terverifikasi/i)).toBeInTheDocument();
  });
});

describe("kyc form existing submission", () => {
  it("summarises a verified submission with only the last four digits", async () => {
    stubKyc({ me: () => fakeResponse(200, TERVERIFIKASI) });
    render(<KycForm />);
    const judul = await screen.findByText(/identitas terverifikasi/i);
    // Dibatasi ke panel ringkasannya: "BCA" juga hidup sebagai <option> di
    // dalam formulir di bawahnya, dan pencarian seluruh dokumen menemukan
    // keduanya tanpa membuktikan yang ini tampil.
    const ringkasan = within(judul.closest("section") as HTMLElement);
    expect(ringkasan.getByText("Nama Pemilik Akun")).toBeInTheDocument();
    expect(ringkasan.getByText("Nama Pemilik Rekening")).toBeInTheDocument();
    expect(ringkasan.getByText("BCA")).toBeInTheDocument();
    expect(ringkasan.getByText("••••1234")).toBeInTheDocument();
    expect(ringkasan.getByText("••••5678")).toBeInTheDocument();
    // Nomor utuhnya tidak pernah dikirim backend, jadi ia juga tidak boleh
    // muncul di layar dalam bentuk apa pun.
    expect(screen.queryByText(/3201234567890123/)).not.toBeInTheDocument();
  });

  it("explains that submitting again replaces the recorded data", async () => {
    stubKyc({ me: () => fakeResponse(200, TERVERIFIKASI) });
    render(<KycForm />);
    expect(await screen.findByRole("heading", { name: /ajukan ulang/i })).toBeInTheDocument();
    expect(screen.getByText(/menggantikan data di atas/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ganti data verifikasi/i })).toBeInTheDocument();
  });

  it("shows the rejection reason, with the status also written as text", async () => {
    stubKyc({ me: () => fakeResponse(200, DITOLAK) });
    render(<KycForm />);
    expect(await screen.findByText(/pengajuan ditolak/i)).toBeInTheDocument();
    expect(screen.getByText("Kode wilayah pada NIK tidak sah.")).toBeInTheDocument();
  });
});
