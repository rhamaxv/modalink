import type { Metadata } from "next";
import { CampaignForm } from "@/components/CampaignForm";

export const metadata: Metadata = {
  title: "Buat campaign baru - Modalink",
};

// Keputusan di layar ini: kriteria apa yang saya pasang untuk proposal yang
// masuk nanti, terutama ambang skor. Halaman ini sengaja tanpa "use client":
// hanya CampaignForm yang menyimpan state form dan memanggil api, sama
// seperti pola SignInForm/SignUpForm di app/(auth)/.
export default function NewCampaignPage() {
  return (
    <div className="mx-auto flex max-w-measure flex-col gap-space-5 px-space-3 py-space-6">
      <div>
        <h1 className="text-[clamp(2.5rem,5vw,4rem)] font-semibold leading-tight text-ink">
          Buat campaign baru
        </h1>
        <p className="mt-space-2 text-base leading-[1.6] text-muted">
          Ambang skor menentukan proposal mana yang otomatis terbuka untuk didanai. Setelah ada
          proposal masuk, ambang ini terkunci dan tidak bisa diubah lagi.
        </p>
      </div>
      <CampaignForm mode="create" />
    </div>
  );
}
