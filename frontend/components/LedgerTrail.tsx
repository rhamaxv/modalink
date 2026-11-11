"use client";

import { useCallback, useEffect, useState } from "react";
import { ErrorState, LoadingState } from "@/components/ui";
import { Icon, type IconName } from "@/components/icons/Icon";
import { ApiError, api } from "@/lib/api";
import { formatRupiah } from "@/lib/money";

type EntryType = "pledge_in" | "refund_out" | "disbursement_out";

type LedgerEntry = {
  id: string;
  entry_type: EntryType;
  amount: number;
  ref_type: string;
  created_at: string;
  milik_saya: boolean;
};

type LedgerOut = {
  entries: LedgerEntry[];
  balance: number;
  total_masuk: number;
  total_cair: number;
};

// Tiga jenis baris, dan kalimatnya menjelaskan APA yang terjadi, bukan
// menyalin nama enumnya. "pledge_in" tidak berarti apa pun bagi pemilik
// usaha yang membaca riwayat dananya sendiri.
const JENIS: Record<EntryType, { label: string; ikon: IconName; arah: "masuk" | "keluar" }> = {
  pledge_in: { label: "Dana masuk dari investor", ikon: "money", arah: "masuk" },
  refund_out: { label: "Pendanaan dibatalkan, dana dikembalikan", ikon: "arrow-left", arah: "keluar" },
  disbursement_out: { label: "Dana cair ke UMKM", ikon: "check", arah: "keluar" },
};

function formatWaktu(iso: string): string {
  return new Date(iso).toLocaleString("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

type Keadaan =
  | { status: "loading" }
  | { status: "ditolak" }
  | { status: "error"; pesan: string }
  | { status: "siap"; data: LedgerOut };

// Riwayat pergerakan dana satu proposal.
//
// Catatan ini sudah append-only sejak awal (BR-51: tidak ada endpoint,
// service, atau migrasi yang boleh meng-UPDATE atau menghapus barisnya), tapi
// satu-satunya jalan membacanya adalah endpoint internal yang HANYA hidup
// saat ENV=dev. Artinya di produksi, investor yang menaruh uang dan UMKM yang
// menerimanya sama-sama tidak bisa melihat apa pun. Bukti yang tidak bisa
// dilihat pemiliknya belum benar-benar jadi bukti.
export function LedgerTrail({ proposalId }: { proposalId: string }) {
  const [keadaan, setKeadaan] = useState<Keadaan>({ status: "loading" });

  const muat = useCallback(async () => {
    setKeadaan({ status: "loading" });
    try {
      const data = await api.get<LedgerOut>(`/proposals/${proposalId}/ledger`);
      // Pagar bentuk respons, bukan pemanis tipe: api.get hanya MEMAKSA
      // tipe, ia tidak memeriksa apa pun saat berjalan. Tanpa baris ini,
      // satu respons yang tidak berbentuk amplop ini membuat entries.map
      // melempar di tengah render, React membuang seluruh pohon, dan
      // pengunjung melihat layar kosong alih-alih halaman proposalnya.
      // Kelas kegagalan yang sama sudah pernah mengosongkan halaman ini
      // lewat satu nominal yang hilang.
      if (!Array.isArray(data?.entries) || !Number.isInteger(data?.balance)) {
        throw new ApiError(
          "bentuk_respons_tidak_terduga",
          "Riwayat dana tidak bisa dibaca. Coba muat ulang halaman.",
          0,
        );
      }
      setKeadaan({ status: "siap", data });
    } catch (error) {
      // 401 dan 403 bukan kegagalan teknis di sini: riwayat dana memang
      // hanya untuk pihak yang uangnya ada di dalamnya. Ditampilkan sebagai
      // penjelasan, bukan sebagai galat merah.
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        setKeadaan({ status: "ditolak" });
        return;
      }
      setKeadaan({
        status: "error",
        pesan:
          error instanceof ApiError
            ? error.message
            : "Terjadi kesalahan. Coba lagi sebentar lagi.",
      });
    }
  }, [proposalId]);

  useEffect(() => {
    muat();
  }, [muat]);

  if (keadaan.status === "loading") {
    return <LoadingState label="Memuat riwayat dana" minHeight={160} />;
  }
  if (keadaan.status === "ditolak") {
    return (
      <p className="max-w-measure text-body text-muted">
        Riwayat dana hanya bisa dilihat oleh investor dan pemilik proposal ini.
      </p>
    );
  }
  if (keadaan.status === "error") {
    return <ErrorState message={keadaan.pesan} onRetry={muat} />;
  }

  const { entries, balance, total_masuk, total_cair } = keadaan.data;

  return (
    <div className="flex flex-col gap-space-4">
      {/* Tiga angka yang menjawab tiga pertanyaan berbeda, dan ketiganya
          dihitung ulang dari baris di bawah, bukan dari kolom tersimpan
          (BR-52: kolom saldo tidak ada dan tidak boleh ada). */}
      <dl className="grid grid-cols-1 gap-space-3 sm:grid-cols-3">
        {[
          ["Total masuk", total_masuk, "Dari investor, setelah dikurangi pembatalan"],
          ["Sudah cair", total_cair, "Diterima UMKM lewat milestone yang disetujui"],
          ["Masih tertahan", balance, "Belum cair, menunggu milestone berikutnya"],
        ].map(([label, nilai, penjelasan]) => (
          <div
            key={label as string}
            className="flex flex-col gap-space-1 rounded-card border border-line bg-panel px-space-4 py-space-3"
          >
            <dt className="text-label text-muted">{label as string}</dt>
            <dd className="tabular text-amount-sm text-ink">
              {formatRupiah(nilai as number)}
            </dd>
            <dd className="text-label text-muted">{penjelasan as string}</dd>
          </div>
        ))}
      </dl>

      {entries.length === 0 ? (
        <p className="max-w-measure text-body text-muted">
          Belum ada pergerakan dana pada proposal ini.
        </p>
      ) : (
        <>
          {/* <ol>, bukan <ul>: urutannya kronologis dan itu bagian dari
              artinya. Baris tidak pernah dihapus maupun diubah, jadi daftar
              ini adalah riwayat, bukan keadaan sekarang. */}
          <ol className="flex flex-col">
            {entries.map((entri) => {
              const jenis = JENIS[entri.entry_type];
              return (
                <li
                  key={entri.id}
                  className="flex flex-wrap items-center justify-between gap-space-3 border-b border-line py-space-3"
                >
                  <span className="flex min-w-0 items-center gap-space-3">
                    <span
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-line ${
                        jenis.arah === "masuk" ? "text-accent-text" : "text-muted"
                      }`}
                    >
                      <Icon name={jenis.ikon} size={18} />
                    </span>
                    <span className="flex min-w-0 flex-col">
                      <span className="text-body font-medium text-ink">
                        {jenis.label}
                        {entri.milik_saya && (
                          <span className="ml-space-2 rounded-sm bg-accent-2 px-space-2 py-space-1 text-label font-semibold text-on-accent">
                            dari Anda
                          </span>
                        )}
                      </span>
                      <span className="tabular text-label text-muted">
                        {formatWaktu(entri.created_at)}
                      </span>
                    </span>
                  </span>
                  <span
                    className={`tabular text-amount-sm ${
                      jenis.arah === "masuk" ? "text-ink" : "text-muted"
                    }`}
                  >
                    {jenis.arah === "masuk" ? "+" : "-"}
                    {formatRupiah(entri.amount)}
                  </span>
                </li>
              );
            })}
          </ol>
          <p className="max-w-measure text-label text-muted">
            Catatan ini hanya bisa ditambah, tidak pernah diubah atau dihapus. Pembatalan
            pendanaan muncul sebagai baris baru, bukan sebagai baris yang hilang.
          </p>
        </>
      )}
    </div>
  );
}
