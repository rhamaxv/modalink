import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SignUpForm } from "@/components/SignUpForm";
import { SignInForm } from "@/components/SignInForm";

// Komponen form memanggil useRouter untuk pindah halaman setelah berhasil;
// di luar Next.js App Router sungguhan, hook itu melempar invariant kecuali
// di-mock.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}));

function fakeResponse(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

async function fillAndSubmitSignIn() {
  await userEvent.type(screen.getByLabelText(/email/i), "investor@contoh.id");
  await userEvent.type(screen.getByLabelText(/password/i), "rahasia123");
  await userEvent.click(screen.getByRole("button", { name: /masuk/i }));
}

afterEach(() => {
  vi.unstubAllGlobals();
  try {
    localStorage.clear();
  } catch {
    // tidak relevan di lingkungan tanpa localStorage.
  }
});

describe("form masuk", () => {
  it("setiap kolom punya label yang terhubung", () => {
    render(<SignInForm />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("pesan error terhubung ke kolomnya lewat aria-describedby", async () => {
    render(<SignInForm />);
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));
    const field = screen.getByLabelText(/email/i);
    const messageId = field.getAttribute("aria-describedby");
    expect(messageId).toBeTruthy();
    expect(document.getElementById(messageId!)).toHaveTextContent(/email/i);
  });

  it("menampilkan pesan dari backend apa adanya, bukan pesan generik", async () => {
    vi.stubGlobal("fetch", () => fakeResponse(401, {
      error: { code: "kredensial_salah", message: "Email atau password salah." },
    }));
    render(<SignInForm />);
    await fillAndSubmitSignIn();
    expect(await screen.findByRole("alert"))
      .toHaveTextContent("Email atau password salah.");
  });

  it("tombol kirim nonaktif selama permintaan berjalan", async () => {
    vi.stubGlobal("fetch", () => new Promise(() => {
      // Sengaja tidak pernah selesai, untuk mengamati status nonaktif saat permintaan berjalan.
    }));
    render(<SignInForm />);
    await fillAndSubmitSignIn();
    expect(screen.getByRole("button", { name: /masuk/i })).toBeDisabled();
  });

  it("menyimpan token ke localStorage saat berhasil masuk", async () => {
    vi.stubGlobal("fetch", () => fakeResponse(200, { access_token: "token-palsu" }));
    render(<SignInForm />);
    await fillAndSubmitSignIn();
    await vi.waitFor(() => {
      expect(localStorage.getItem("modalink_token")).toBe("token-palsu");
    });
  });
});

describe("form daftar", () => {
  it("setiap kolom punya label yang terhubung", () => {
    render(<SignUpForm />);
    expect(screen.getByLabelText(/^nama/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/peran/i)).toBeInTheDocument();
  });

  it("menampilkan pesan dari backend apa adanya saat gagal daftar", async () => {
    vi.stubGlobal("fetch", () => fakeResponse(409, {
      error: { code: "email_terdaftar", message: "Email sudah terdaftar." },
    }));
    render(<SignUpForm />);
    await userEvent.type(screen.getByLabelText(/^nama/i), "Budi Santoso");
    await userEvent.type(screen.getByLabelText(/email/i), "budi@contoh.id");
    await userEvent.type(screen.getByLabelText(/password/i), "rahasia123");
    await userEvent.click(screen.getByRole("button", { name: /daftar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Email sudah terdaftar.");
  });
});
