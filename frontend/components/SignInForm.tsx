"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Field } from "@/components/ui/Field";
import { ApiError, api } from "@/lib/api";
import { tujuanAmanSetelahMasuk } from "@/lib/auth";

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
//
// Dibungkus Suspense di sini (bukan di app/(auth)/masuk/page.tsx) supaya
// pemanggil tidak perlu tahu SignInForm sekarang membaca useSearchParams:
// Next.js mewajibkan batas Suspense di sekitar useSearchParams saat halaman
// dirender statis, dan menaruhnya di komponen terkecil yang membutuhkannya
// mengikuti konvensi fase 10 ("use client" di komponen terkecil, bukan di
// halaman).
export function SignInForm() {
  return (
    <Suspense fallback={null}>
      <SignInFormInner />
    </Suspense>
  );
}

function SignInFormInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
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
      // Membawa pengguna kembali ke halaman yang semula dituju (query
      // "next", ditulis RequireRole saat mengarahkan ke sini), bukan selalu
      // ke "/". Membuang tujuan asal memaksa pengguna menavigasi ulang dari
      // nol setelah berhasil masuk.
      router.push(tujuanAmanSetelahMasuk(searchParams.get("next")));
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "Terjadi kesalahan. Coba lagi sebentar lagi.");
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
        // sudah terukur lolos: --muted di atas --panel (6.25:1 terang,
        // 6.50:1 gelap).
        className="min-h-[44px] rounded-sm bg-accent px-space-4 py-space-2 text-body font-semibold text-on-accent disabled:border disabled:border-line disabled:bg-panel disabled:text-muted"
      >
        Masuk
      </button>
    </form>
  );
}
