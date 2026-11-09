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
    <form onSubmit={submit} noValidate className="flex flex-col gap-space-4">
      {formError && (
        <p role="alert" className="rounded-sm border border-danger bg-surface px-space-3 py-space-2 text-base leading-[1.6] text-danger">
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
        // disabled:opacity-60 di atas bg-accent terukur 1.26:1 di tema gelap
        // dan 3.62:1 di tema terang, gagal 4.5:1. Diganti pasangan token yang
        // sudah terukur lolos: --muted di atas --surface (6.25:1 terang,
        // 6.50:1 gelap).
        className="min-h-[44px] rounded-sm bg-accent px-space-4 py-space-2 text-base leading-[1.6] font-semibold text-ink disabled:border disabled:border-line disabled:bg-surface disabled:text-muted"
      >
        Masuk
      </button>
    </form>
  );
}
