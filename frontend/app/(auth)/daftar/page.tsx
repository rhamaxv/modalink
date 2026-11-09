import type { Metadata } from "next";
import Link from "next/link";
import { SignUpForm } from "@/components/SignUpForm";

export const metadata: Metadata = {
  title: "Daftar di Modalink",
};

export default function Daftar() {
  return (
    <div className="mx-auto flex max-w-baca flex-col gap-ruang-5 px-ruang-3 py-ruang-6">
      <div>
        <h1 className="text-[clamp(2rem,4vw,2.5rem)] font-semibold text-ink">Daftar</h1>
        <p className="mt-ruang-2 text-sm text-muted">
          Pilih peran Anda: investor yang mendanai, UMKM yang mengajukan proposal, atau
          komunitas yang memberi vote dan komentar.
        </p>
      </div>
      <SignUpForm />
      <p className="text-sm text-muted">
        Sudah punya akun?{" "}
        <Link href="/masuk" className="font-medium text-ink underline">
          Masuk di sini
        </Link>
      </p>
    </div>
  );
}
