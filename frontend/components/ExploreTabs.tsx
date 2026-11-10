"use client";

import { useCallback, useEffect, useState } from "react";
import { ProposalList } from "@/components/ProposalCard";
import { CampaignBrowseList } from "@/components/CampaignBrowseCard";
import { fetchCurrentUser } from "@/lib/auth";

type Tab = "proposal" | "campaign";

// Satu layar, dua niat yang datang dengan harapan berbeda: investor mencari
// proposal untuk didanai, UMKM mencari campaign untuk diajukan proposal. Tab
// dipilih dibanding dua rute terpisah supaya pengunjung anonim, termasuk
// juri lomba, melihat KEDUANYA ada tanpa harus masuk dulu: GET /auth/me di
// bawah cuma memilih tab default yang lebih relevan, bukan menyembunyikan
// tab yang lain di belakang akun.
//
// `tab` bernilai null berarti "belum dipilih manual oleh pengunjung". Begitu
// peran UMKM diketahui, default pindah ke tab campaign, TAPI hanya kalau
// pengunjung belum pernah mengklik tab apa pun sendiri: klik manual selalu
// menang atas tebakan peran, supaya tab tidak melompat balik begitu pengunjung
// sudah memilih.
export function ExploreTabs() {
  const [roleDefault, setRoleDefault] = useState<Tab>("proposal");
  const [tab, setTab] = useState<Tab | null>(null);
  // Jumlah di label tab datang dari `total` milik kedua endpoint, bukan dari
  // panjang array yang sedang tampil: dengan paginasi, panjang array adalah
  // jumlah baris di halaman ini saja, dan menuliskannya sebagai "Proposal
  // (20)" pada daftar berisi lima puluh adalah angka yang salah.
  const [totalProposal, setTotalProposal] = useState<number | null>(null);
  const [totalCampaign, setTotalCampaign] = useState<number | null>(null);

  useEffect(() => {
    fetchCurrentUser().then((user) => {
      if (user?.role === "umkm") setRoleDefault("campaign");
    });
  }, []);

  // useCallback: kedua daftar memakai callback ini di dalam dependency
  // useEffect-nya. Fungsi baru di tiap render akan membuat effect itu jalan
  // lagi setiap kali state apa pun di sini berubah, dan karena effect itu
  // sendiri memanggil setTotal..., hasilnya fetch yang memanggil dirinya
  // sendiri tanpa henti.
  const catatTotalProposal = useCallback((total: number) => setTotalProposal(total), []);
  const catatTotalCampaign = useCallback((total: number) => setTotalCampaign(total), []);

  const aktif = tab ?? roleDefault;

  // Tab aktif ditandai garis --accent, bukan border-ink seperti sebelumnya.
  // Ia penanda, bukan aksi: DESIGN.md menjatah aksi BERLATAR aksen (tepat
  // satu per layar, dipegang tautan daftar di bawah), sementara aksen
  // sebagai penanda dijatah sampai tiga kemunculan, dan menandai "daftar
  // mana yang sedang Anda lihat" adalah penggunaan penanda yang paling
  // langsung di halaman ini.
  function kelasTab(terpilih: boolean): string {
    return `inline-flex min-h-[44px] items-center gap-space-2 border-b-2 px-space-3 text-body font-semibold transition-colors ${
      terpilih ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink"
    }`;
  }

  function jumlah(total: number | null) {
    // null berarti daftarnya belum selesai dimuat. Menulis "(0)" di sana
    // akan menyatakan "tidak ada apa-apa di sini" selama satu detik pertama,
    // yang justru kebalikan dari keadaan sebenarnya pada daftar yang penuh.
    if (total === null) return null;
    // aria-hidden: tanpa ini nama tab yang dibacakan menjadi "Campaign 2",
    // yang menggantung tanpa satuan. Angkanya tetap sampai ke pembaca layar
    // lewat ResultCount di dalam panelnya ("Menampilkan 1-20 dari 57
    // campaign"), kalimat lengkap yang memang menyebut satuannya.
    return (
      <span aria-hidden="true" className="tabular text-label font-medium text-muted">
        {total}
      </span>
    );
  }

  return (
    <div className="flex flex-col gap-space-4">
      <div
        role="tablist"
        aria-label="Pilih yang ingin dijelajahi"
        className="flex gap-space-2 border-b border-line"
      >
        <button
          type="button"
          role="tab"
          id="tab-proposal"
          aria-selected={aktif === "proposal"}
          aria-controls="panel-proposal"
          className={kelasTab(aktif === "proposal")}
          onClick={() => setTab("proposal")}
        >
          Proposal
          {jumlah(totalProposal)}
        </button>
        <button
          type="button"
          role="tab"
          id="tab-campaign"
          aria-selected={aktif === "campaign"}
          aria-controls="panel-campaign"
          className={kelasTab(aktif === "campaign")}
          onClick={() => setTab("campaign")}
        >
          Campaign
          {jumlah(totalCampaign)}
        </button>
      </div>
      {/* hidden, bukan unmount bersyarat: kedua panel tetap dimuat sekali di
          balik layar begitu halaman terbuka, supaya berpindah tab tidak
          memicu fetch ulang setiap kali, dan supaya pengunjung yang belum
          pernah mengklik tab lain tetap bisa dibuktikan kontennya ada lewat
          pemeriksaan DOM (role query mengecualikan elemen hidden, sesuai
          pohon aksesibilitas yang sungguh dilihat pembaca layar). */}
      <div role="tabpanel" id="panel-proposal" aria-labelledby="tab-proposal" hidden={aktif !== "proposal"}>
        <ProposalList onTotalChange={catatTotalProposal} />
      </div>
      <div role="tabpanel" id="panel-campaign" aria-labelledby="tab-campaign" hidden={aktif !== "campaign"}>
        <CampaignBrowseList onTotalChange={catatTotalCampaign} />
      </div>
    </div>
  );
}
