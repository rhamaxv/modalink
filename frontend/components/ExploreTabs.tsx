"use client";

import { useEffect, useState } from "react";
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

  useEffect(() => {
    fetchCurrentUser().then((user) => {
      if (user?.role === "umkm") setRoleDefault("campaign");
    });
  }, []);

  const aktif = tab ?? roleDefault;

  // Bukan bg-accent: tab adalah sakelar tampilan, bukan aksi utama halaman,
  // dan anggaran satu aksi berlatar aksen di layar ini sudah dipegang CTA
  // "Daftar sekarang" di section penutup. Tab aktif ditandai border-ink,
  // bukan warna, sama seperti pola tab yang sudah ada di tempat lain.
  function kelasTab(terpilih: boolean): string {
    return `inline-flex min-h-[44px] items-center border-b-2 px-space-3 text-body font-semibold transition-colors ${
      terpilih ? "border-ink text-ink" : "border-transparent text-muted hover:text-ink"
    }`;
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
        </button>
      </div>
      {/* hidden, bukan unmount bersyarat: kedua panel tetap dimuat sekali di
          balik layar begitu halaman terbuka, supaya berpindah tab tidak
          memicu fetch ulang setiap kali, dan supaya pengunjung yang belum
          pernah mengklik tab lain tetap bisa dibuktikan kontennya ada lewat
          pemeriksaan DOM (role query mengecualikan elemen hidden, sesuai
          pohon aksesibilitas yang sungguh dilihat pembaca layar). */}
      <div role="tabpanel" id="panel-proposal" aria-labelledby="tab-proposal" hidden={aktif !== "proposal"}>
        <ProposalList />
      </div>
      <div role="tabpanel" id="panel-campaign" aria-labelledby="tab-campaign" hidden={aktif !== "campaign"}>
        <CampaignBrowseList />
      </div>
    </div>
  );
}
