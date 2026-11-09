import { CampaignManagePanel } from "@/components/CampaignManagePanel";

// Keputusan di layar ini: proposal mana yang layak saya baca lebih dalam.
// Tanpa "use client" di sini: CampaignManagePanel sendiri yang menyimpan
// state fetch, konfirmasi tutup, dan mode ubah.
export default async function CampaignDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="mx-auto flex max-w-[72rem] flex-col px-space-3 py-space-6">
      <CampaignManagePanel campaignId={id} />
    </div>
  );
}
