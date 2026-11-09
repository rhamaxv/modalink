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

// POST /auth/register mengembalikan UserOut (tanpa access_token); hanya
// POST /auth/login mengembalikan TokenOut. Mock ini meniru kedua endpoint
// berbeda itu secara terpisah, persis seperti backend sungguhan
// (.claude/prd/10-api-contract.md).
function stubRegisterThenLogin(loginBody: unknown, loginStatus = 200) {
  vi.stubGlobal("fetch", (url: string) => {
    if (url.includes("/auth/register")) {
      return fakeResponse(201, {
        id: "u1",
        email: "budi@contoh.id",
        name: "Budi Santoso",
        role: "umkm",
        created_at: "2026-01-01T00:00:00Z",
      });
    }
    if (url.includes("/auth/login")) {
      return fakeResponse(loginStatus, loginBody);
    }
    throw new Error(`permintaan fetch tak terduga ke ${url}`);
  });
}

async function fillAndSubmitSignUp() {
  await userEvent.type(screen.getByLabelText(/^nama/i), "Budi Santoso");
  await userEvent.type(screen.getByLabelText(/email/i), "budi@contoh.id");
  await userEvent.type(screen.getByLabelText(/password/i), "rahasia123");
  await userEvent.click(screen.getByRole("button", { name: /daftar/i }));
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

describe("sign in form", () => {
  it("every field has a connected label", () => {
    render(<SignInForm />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("connects the error message to its field via aria-describedby", async () => {
    render(<SignInForm />);
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));
    const field = screen.getByLabelText(/email/i);
    const messageId = field.getAttribute("aria-describedby");
    expect(messageId).toBeTruthy();
    expect(document.getElementById(messageId!)).toHaveTextContent(/email/i);
  });

  it("shows the backend message as is, not a generic message", async () => {
    vi.stubGlobal("fetch", () => fakeResponse(401, {
      error: { code: "kredensial_salah", message: "Email atau password salah." },
    }));
    render(<SignInForm />);
    await fillAndSubmitSignIn();
    expect(await screen.findByRole("alert"))
      .toHaveTextContent("Email atau password salah.");
  });

  it("disables the submit button while the request is in flight", async () => {
    vi.stubGlobal("fetch", () => new Promise(() => {
      // Sengaja tidak pernah selesai, untuk mengamati status nonaktif saat permintaan berjalan.
    }));
    render(<SignInForm />);
    await fillAndSubmitSignIn();
    expect(screen.getByRole("button", { name: /masuk/i })).toBeDisabled();
  });

  it("stores the token in localStorage on a successful sign in", async () => {
    vi.stubGlobal("fetch", () => fakeResponse(200, { access_token: "token-palsu" }));
    render(<SignInForm />);
    await fillAndSubmitSignIn();
    await vi.waitFor(() => {
      expect(localStorage.getItem("modalink_token")).toBe("token-palsu");
    });
  });
});

describe("sign up form", () => {
  it("every field has a connected label", () => {
    render(<SignUpForm />);
    expect(screen.getByLabelText(/^nama/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/peran/i)).toBeInTheDocument();
  });

  it("shows the backend message as is when sign up fails", async () => {
    vi.stubGlobal("fetch", () => fakeResponse(409, {
      error: { code: "email_terdaftar", message: "Email sudah terdaftar." },
    }));
    render(<SignUpForm />);
    await fillAndSubmitSignUp();
    expect(await screen.findByRole("alert")).toHaveTextContent("Email sudah terdaftar.");
  });

  it("stores the real login token after a successful sign up, never the literal string undefined", async () => {
    // POST /auth/register tidak mengembalikan access_token sama sekali
    // (lihat backend/app/schemas/auth.py: UserOut). Mengambil
    // result.access_token langsung dari respons register menghasilkan
    // undefined, dan localStorage.setItem mengubahnya jadi string literal
    // "undefined" yang lolos pemeriksaan truthy di lib/api.ts: pengguna
    // tampak masuk padahal setiap permintaan berikutnya mengirim
    // "Authorization: Bearer undefined". Token yang benar hanya datang dari
    // POST /auth/login yang dipanggil ulang dengan kredensial yang sama
    // setelah register sukses.
    stubRegisterThenLogin({ access_token: "token-asli", token_type: "bearer" });
    render(<SignUpForm />);
    await fillAndSubmitSignUp();
    await vi.waitFor(() => {
      expect(localStorage.getItem("modalink_token")).toBe("token-asli");
    });
    expect(localStorage.getItem("modalink_token")).not.toBe("undefined");
  });

  it("keeps the created account and shows the login error when auto sign in fails after sign up", async () => {
    stubRegisterThenLogin(
      { error: { code: "jaringan_bermasalah", message: "Koneksi ke server bermasalah." } },
      503,
    );
    render(<SignUpForm />);
    await fillAndSubmitSignUp();
    expect(await screen.findByRole("alert")).toHaveTextContent(/Koneksi ke server bermasalah/);
    // Akun tetap tercatat dibuat oleh backend; hanya auto-masuknya yang gagal,
    // jadi tidak ada token palsu yang tersimpan.
    expect(localStorage.getItem("modalink_token")).toBeNull();
  });
});
