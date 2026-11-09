"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Field } from "@/components/ui/Field";
import { ApiError, api } from "@/lib/api";

type FieldErrors = {
  email?: string;
  password?: string;
};

type LoginResponse = {
  access_token: string;
};

// Form masuk sungguhan: validasi kolom di sisi klien, lalu bentuk error
// backend ditampilkan apa adanya (lihat .claude/prd/10-api-contract.md),
// bukan diganti pesan generik. Token disimpan dengan kunci "modalink_token"
// yang sama dengan yang dibaca lib/api.ts.
export function SignInForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function validate(): boolean {
    const next: FieldErrors = {};
    if (!email.trim()) next.email = "Email wajib diisi.";
    if (!password) next.password = "Password wajib diisi.";
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    if (!validate()) return;

    setSubmitting(true);
    try {
      const result = await api.post<LoginResponse>("/auth/login", { email, password });
      try {
        localStorage.setItem("modalink_token", result.access_token);
      } catch {
        // Tanpa localStorage, token tidak tersimpan tapi login tetap sukses secara server.
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
        <p role="alert" className="rounded-kecil border border-danger bg-surface px-ruang-3 py-ruang-2 text-base leading-[1.6] text-danger">
          {formError}
        </p>
      )}
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
        autoComplete="current-password"
        required
      />
      <button
        type="submit"
        disabled={submitting}
        aria-busy={submitting}
        // Nama aksesibel tombol tetap "Masuk" saat memuat, supaya pembaca
        // layar dan pengujian yang mencari tombol lewat namanya tidak
        // kehilangan jejak; status sedang berjalan disampaikan lewat
        // aria-busy dan atribut disabled, bukan dengan mengganti labelnya.
        className="min-h-[44px] rounded-kecil bg-accent px-ruang-4 py-ruang-2 text-base leading-[1.6] font-semibold text-ink disabled:opacity-60"
      >
        Masuk
      </button>
    </form>
  );
}
