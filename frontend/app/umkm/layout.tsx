import { RequireRole } from "@/components/RouteGuard";

// Satu penjaga untuk seluruh route /umkm/*, sepadan dengan
// app/investor/layout.tsx.
//
// Berkas ini SEBELUMNYA TIDAK ADA, dan itu lubang sungguhan: seluruh segmen
// /umkm/* berjalan tanpa pagar peran sama sekali, sehingga akun investor
// maupun komunitas yang membuka /umkm/proposal/baru melihat form pengajuan
// proposal lengkap dengan tombol kirimnya. Backend tetap menolak
// pengirimannya (require_role(Role.UMKM) di api/v1/proposals.py), jadi tidak
// ada data yang bocor, tapi produk menawarkan jalan yang pasti buntu dan
// /umkm/beranda menampilkan keadaan galat alih-alih 404 yang jujur.
//
// Ditemukan oleh e2e alur pasar, bukan oleh pembacaan kode: pagarnya tidak
// hilang, ia memang tidak pernah ada, dan satu-satunya yang menyadarinya
// adalah test yang sungguh membuka halaman itu sebagai investor.
export default function UmkmLayout({ children }: { children: React.ReactNode }) {
  return <RequireRole role="umkm">{children}</RequireRole>;
}
