import type { Metadata } from "next";
import { CampaignDetailPanel } from "@/components/CampaignDetailPanel";

export const metadata: Metadata = {
  title: "Detail campaign - Modalink",
};

// Halaman detail campaign publik: tujuan sisi UMKM dari /jelajah, setara
// dengan /proposal/[id] di sisi investor. Tanpa "use client" di sini:
// CampaignDetailPanel sendiri yang menyimpan state fetch dan retry.
export default async function CampaignBrowseDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="mx-auto flex max-w-[72rem] flex-col px-space-3 py-space-6">
      <CampaignDetailPanel campaignId={id} />
    </div>
  );
}
