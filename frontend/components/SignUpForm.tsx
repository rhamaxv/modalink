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

type LoginResponse = {
  access_token: string;
};

// Form daftar: body mengikuti POST /auth/register (email, password, name,
// role), lalu auto-login dengan token yang dikembalikan backend, konsisten
// dengan SignInForm.
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
      const result = await api.post<LoginResponse>("/auth/register", {
        name,
        email,
        password,
        role,
      });
      try {
        localStorage.setItem("modalink_token", result.access_token);
      } catch {
        // Tanpa localStorage, akun tetap terbuat tapi sesi tidak tersimpan.
      }
      router.push("/");
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-ruang-4">
      {formError && (
        <p role="alert" className="rounded-kecil border border-danger bg-surface px-ruang-3 py-ruang-2 text-sm text-danger">
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
        className="min-h-[44px] rounded-kecil bg-accent px-ruang-4 py-ruang-2 text-sm font-semibold text-ink disabled:opacity-60"
      >
        Daftar
      </button>
    </form>
  );
}
