import type { Metadata } from "next";
import Link from "next/link";
import { SignInForm } from "@/components/SignInForm";

export const metadata: Metadata = {
  title: "Masuk ke Modalink",
};

// Halaman ini sengaja tanpa "use client": hanya SignInForm, yang menyimpan
// state form dan memanggil api, yang perlu jadi client component.
export default function Masuk() {
  return (
    <div className="mx-auto flex max-w-baca flex-col gap-ruang-5 px-ruang-3 py-ruang-6">
      <div>
        <h1 className="text-[clamp(2rem,4vw,2.5rem)] font-semibold text-ink">Masuk</h1>
        <p className="mt-ruang-2 text-sm text-muted">
          Masuk untuk melihat proposal, pledge, dan dashboard Anda.
        </p>
      </div>
      <SignInForm />
      <p className="text-sm text-muted">
        Belum punya akun?{" "}
        <Link href="/daftar" className="font-medium text-ink underline">
          Daftar di sini
        </Link>
      </p>
    </div>
  );
}
