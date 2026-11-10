"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Field } from "@/components/ui/Field";
import { ApiError, api } from "@/lib/api";

// Tiga peran dari .claude/prd/09-data-model.md: investor, umkm, community.
const ROLE_OPTIONS = [
  { value: "investor", label: "Investor" },
  { value: "umkm", label: "UMKM" },
  { value: "community", label: "Komunitas" },
];

type FieldErrors = {
  name?: string;
  email?: string;
  password?: string;
};

// POST /auth/register mengembalikan UserOut (lihat backend/app/schemas/auth.py),
// bukan token: akun baru tidak otomatis membawa sesi. Mengambil access_token
// dari respons register akan selalu undefined, dan localStorage.setItem
// mengubahnya jadi string literal "undefined" yang lolos pemeriksaan truthy
// di lib/api.ts, membuat pengguna mengira sudah masuk padahal setiap
// permintaan berikutnya mengirim header Authorization yang tidak valid.
type RegisterResponse = {
  id: string;
  email: string;
  name: string;
  role: string;
  created_at: string;
};

type LoginResponse = {
  access_token: string;
};

// Form daftar: body mengikuti POST /auth/register (email, password, name,
// role) sesuai .claude/prd/10-api-contract.md. Register tidak mengembalikan
// token, jadi auto-masuk dilakukan dengan memanggil POST /auth/login memakai
// kredensial yang sama persis seperti SignInForm, dan token disimpan dari
// respons login itu, bukan dari respons register.
export function SignUpForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("investor");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function validate(): boolean {
    const next: FieldErrors = {};
    if (!name.trim()) next.name = "Nama wajib diisi.";
    if (!email.trim()) next.email = "Email wajib diisi.";
    if (password.length < 8) next.password = "Password minimal 8 karakter.";
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    if (!validate()) return;

    setSubmitting(true);
    try {
      await api.post<RegisterResponse>("/auth/register", { name, email, password, role });
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.");
      setSubmitting(false);
      return;
    }

    // Akun sudah benar-benar terbuat di titik ini. Kegagalan di bawah ini
    // hanya berarti auto-masuk gagal, bukan bahwa pendaftaran gagal, jadi
    // pesannya tidak menimpa fakta bahwa akunnya sudah ada.
    try {
      const login = await api.post<LoginResponse>("/auth/login", { email, password });
      try {
        localStorage.setItem("modalink_token", login.access_token);
      } catch {
        // Tanpa localStorage, token tidak tersimpan tapi login tetap sukses secara server.
      }
      router.push("/");
    } catch (error) {
      const sebab = error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.";
      setFormError(`Akun berhasil dibuat, tetapi masuk otomatis gagal: ${sebab}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-space-4">
      {formError && (
        <p role="alert" className="rounded-sm border border-danger bg-panel px-space-3 py-space-2 text-body text-danger">
          {formError}
        </p>
      )}
      <Field label="Nama" value={name} onChange={setName} error={fieldErrors.name} autoComplete="name" required />
      <Field
        label="Email"
        type="email"
        value={email}
        onChange={setEmail}
        error={fieldErrors.email}
        autoComplete="email"
        required
      />
      <Field
        label="Password"
        type="password"
        value={password}
        onChange={setPassword}
        error={fieldErrors.password}
        autoComplete="new-password"
        required
      />
      <Field label="Peran" value={role} onChange={setRole} options={ROLE_OPTIONS} required />
      <button
        type="submit"
        disabled={submitting}
        aria-busy={submitting}
        // disabled:opacity-60 di atas bg-accent terukur 1.26:1 di tema gelap
        // dan 3.62:1 di tema terang, gagal 4.5:1. Diganti pasangan token yang
        // sudah terukur lolos: --muted di atas --panel (6.25:1 terang,
        // 6.50:1 gelap).
        className="min-h-[44px] rounded-sm bg-accent px-space-4 py-space-2 text-body font-semibold text-on-accent disabled:border disabled:border-line disabled:bg-panel disabled:text-muted"
      >
        Daftar
      </button>
    </form>
  );
}
