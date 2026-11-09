import { ProposalDetailView } from "@/components/ProposalDetailView";

type ProposalDetailPageProps = {
  params: Promise<{ id: string }>;
};

// Server component tipis: satu-satunya tugasnya membongkar `params` yang
// asinkron (Next.js 15) lalu menyerahkan id proposal ke client component
// yang sungguh mengambil data dan berinteraksi (localStorage, fetch, form).
// Memisahkannya begini juga membuat ProposalDetailView bisa diuji langsung
// dengan proposalId berupa string biasa, tanpa mensimulasikan Promise params
// Next.js di setiap test.
export default async function ProposalDetailPage({ params }: ProposalDetailPageProps) {
  const { id } = await params;
  return <ProposalDetailView proposalId={id} />;
}
