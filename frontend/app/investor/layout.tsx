import { RequireRole } from "@/components/RouteGuard";

// Satu penjaga untuk seluruh route /investor/*, bukan diulang di tiap
// page.tsx: akun yang belum masuk diarahkan ke /masuk (membawa tujuan
// asalnya), dan akun yang bukan investor mendapat 404 (lihat
// components/RouteGuard.tsx untuk alasan 404, bukan 403).
export default function InvestorLayout({ children }: { children: React.ReactNode }) {
  return <RequireRole role="investor">{children}</RequireRole>;
}
