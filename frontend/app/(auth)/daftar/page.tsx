import type { Metadata } from "next";
import Link from "next/link";
import { SignUpForm } from "@/components/SignUpForm";

export const metadata: Metadata = {
  title: "Daftar di Modalink",
};

export default function Daftar() {
  return (
    <div className="mx-auto flex max-w-measure flex-col gap-space-5 px-space-3 py-space-6">
      <div>
        <h1 className="text-[clamp(2.5rem,5vw,4rem)] font-semibold text-ink">Daftar</h1>
        <p className="mt-space-2 text-base leading-[1.6] text-muted">
          Pilih peran Anda: investor yang mendanai, UMKM yang mengajukan proposal, atau
          komunitas yang memberi vote dan komentar.
        </p>
      </div>
      <SignUpForm />
      <p className="text-base leading-[1.6] text-muted">
        Sudah punya akun?{" "}
        <Link href="/masuk" className="font-medium text-ink underline">
          Masuk di sini
        </Link>
      </p>
    </div>
  );
}
