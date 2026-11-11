"use client";

import { useCallback, useEffect, useState } from "react";
import { Button, ErrorState, Field, LoadingState } from "@/components/ui";
import { Icon } from "@/components/icons/Icon";
import { ApiError, api } from "@/lib/api";

type KycStatus = "verified" | "rejected";

type BankCode =
  "bca" | "bni" | "bri" | "mandiri" | "bsi" | "cimb" | "permata" | "danamon";

// Bentuk ini mengikuti KycOut persis (backend/app/schemas/kyc.py). Tidak ada
// field nik atau account_number di sini karena backend memang tidak
// mengirimkannya: keduanya tidak pernah disimpan utuh, jadi yang bisa
// ditampilkan kembali hanya empat digit terakhirnya.
type KycOut = {
  status: KycStatus;
  full_name: string;
  nik_last4: string;
  bank_code: BankCode;
  account_holder_name: string;
  account_last4: string;
  rejection_reason: string | null;
  submitted_at: string;
  verifikasi_simulasi: boolean;
};

type KycIn = {
  full_name: string;
  nik: string;
  bank_code: BankCode;
  account_holder_name: string;
  account_number: string;
};

// Daftar tertutup, sama persis dengan BankCode di backend/app/models/kyc.py.
// Satu sumber untuk dua kegunaan: opsi di <select> dan terjemahan kode bank
// jadi nama bank di ringkasan. Dua daftar terpisah akan menyimpang begitu
// satu bank ditambahkan.
const NAMA_BANK: Record<BankCode, string> = {
  bca: "BCA",
  bni: "BNI",
  bri: "BRI",
  mandiri: "Mandiri",
  bsi: "BSI",
  cimb: "CIMB Niaga",
  permata: "Permata",
  danamon: "Danamon",
};

// Opsi kosong di depan, bukan BCA yang terpilih diam-diam: bank pertama yang
// kebetulan ada di daftar bukan jawaban pengguna, dan formulir yang sudah
// terisi sendiri membuat pilihan yang salah ikut terkirim tanpa pernah
// dilihat.
const OPSI_BANK = [
  { value: "", label: "Pilih bank" },
  ...(Object.keys(NAMA_BANK) as BankCode[]).map((kode) => ({
    value: kode,
    label: NAMA_BANK[kode],
  })),
];

const PANJANG_NIK = 16;
const REKENING_MIN = 8;
const REKENING_MAX = 20;
const NAMA_MIN = 3;

// Sama dengan normalkan_digit() di backend/app/domain/identity.py: nomor
// rekening dan NIK sering disalin dengan spasi atau tanda hubung, dan
// menolaknya karena itu memindahkan beban ke pengguna untuk kesalahan yang
// bukan kesalahan.
function digitSaja(nilai: string): string {
  return nilai.replace(/[\s.-]/g, "");
}

function hanyaAngka(nilai: string): boolean {
  return /^\d+$/.test(nilai);
}

function formatWaktu(iso: string): string {
  return new Date(iso).toLocaleString("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

type GalatKolom = {
  full_name?: string;
  nik?: string;
  bank_code?: string;
  account_holder_name?: string;
  account_number?: string;
};

type Muatan =
  | { status: "loading" }
  | { status: "error"; pesan: string }
  // pengajuan null berarti akun ini belum pernah mengajukan: GET /kyc/me
  // menjawab 404, dan 404 di sini adalah jawaban, bukan kegagalan.
  | { status: "siap"; pengajuan: KycOut | null };

export function KycForm() {
  const [muatan, setMuatan] = useState<Muatan>({ status: "loading" });
  const [fullName, setFullName] = useState("");
  const [nik, setNik] = useState("");
  const [bankCode, setBankCode] = useState<BankCode | "">("");
  const [accountHolderName, setAccountHolderName] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [galatKolom, setGalatKolom] = useState<GalatKolom>({});
  const [galatKirim, setGalatKirim] = useState<string | null>(null);
  const [mengirim, setMengirim] = useState(false);

  const muat = useCallback(async () => {
    setMuatan({ status: "loading" });
    try {
      const data = await api.get<KycOut>("/kyc/me");
      setMuatan({ status: "siap", pengajuan: data });
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setMuatan({ status: "siap", pengajuan: null });
        return;
      }
      setMuatan({
        status: "error",
        pesan:
          error instanceof ApiError
            ? error.message
            : "Status verifikasi gagal dimuat. Coba lagi sebentar lagi.",
      });
    }
  }, []);

  useEffect(() => {
    muat();
  }, [muat]);

  // Pemeriksaan di klien ini hanya mendahului yang sudah pasti salah supaya
  // pengguna tidak menunggu roundtrip untuknya. Sumber kebenarannya tetap
  // backend/app/domain/identity.py, yang memeriksa kode wilayah, tanggal
  // lahir, dan usia minimum; pesan 422-nya sudah berbahasa Indonesia dan
  // ditampilkan apa adanya di bawah.
  function periksa(): KycIn | null {
    const next: GalatKolom = {};
    const nama = fullName.trim();
    const namaRekening = accountHolderName.trim();
    const nikDigit = digitSaja(nik);
    const rekeningDigit = digitSaja(accountNumber);

    if (nama.length < NAMA_MIN) {
      next.full_name = `Nama sesuai identitas wajib diisi, minimal ${NAMA_MIN} karakter.`;
    }
    if (!hanyaAngka(nikDigit) || nikDigit.length !== PANJANG_NIK) {
      next.nik = `NIK harus ${PANJANG_NIK} digit angka.`;
    }
    if (bankCode === "") {
      next.bank_code = "Pilih bank tujuan pencairan.";
    }
    if (namaRekening.length < NAMA_MIN) {
      next.account_holder_name = `Nama pemilik rekening wajib diisi, minimal ${NAMA_MIN} karakter.`;
    }
    if (
      !hanyaAngka(rekeningDigit) ||
      rekeningDigit.length < REKENING_MIN ||
      rekeningDigit.length > REKENING_MAX
    ) {
      next.account_number = `Nomor rekening harus ${REKENING_MIN} sampai ${REKENING_MAX} digit angka.`;
    }

    setGalatKolom(next);
    if (Object.keys(next).length > 0) return null;
    // Tidak mungkin tercapai setelah pemeriksaan di atas. Ditulis supaya
    // TypeScript tahu banknya sudah terpilih, bukan dipaksa lewat cast yang
    // akan tetap lolos kalau pemeriksaannya hilang suatu hari.
    if (bankCode === "") return null;

    return {
      full_name: nama,
      nik: nik.trim(),
      bank_code: bankCode,
      account_holder_name: namaRekening,
      account_number: accountNumber.trim(),
    };
  }

  async function kirim(event: React.FormEvent) {
    event.preventDefault();
    setGalatKirim(null);
    const payload = periksa();
    if (!payload) return;

    setMengirim(true);
    try {
      const hasil = await api.post<KycOut>("/kyc", payload);
      setMuatan({ status: "siap", pengajuan: hasil });
      // Kolom dikosongkan karena ringkasan di atasnya sekarang adalah
      // catatan resminya, dan karena NIK serta nomor rekening tidak
      // disimpan utuh: membiarkannya tertinggal di layar menahan data yang
      // sistem ini sendiri sudah memutuskan untuk tidak menyimpan.
      setFullName("");
      setNik("");
      setBankCode("");
      setAccountHolderName("");
      setAccountNumber("");
      setGalatKolom({});
    } catch (error) {
      setGalatKirim(
        error instanceof ApiError
          ? error.message
          : "Pengajuan gagal dikirim. Coba lagi sebentar lagi.",
      );
    } finally {
      setMengirim(false);
    }
  }

  const pengajuan = muatan.status === "siap" ? muatan.pengajuan : null;

  return (
    <div className="flex flex-col gap-space-5">
      <PernyataanSimulasi />

      {muatan.status === "loading" && (
        <LoadingState label="Memuat status verifikasi" minHeight={180} />
      )}

      {muatan.status === "error" && (
        <ErrorState message={muatan.pesan} onRetry={muat} />
      )}

      {muatan.status === "siap" && (
        <>
          {/* Wadahnya tetap dirender walau masih kosong: aria-live hanya
              mengumumkan perubahan pada wilayah yang sudah ada sejak awal,
              jadi hasil pengajuan yang baru masuk tidak akan terdengar kalau
              wilayahnya baru lahir bersama isinya. */}
          <div aria-live="polite">
            {pengajuan && <RingkasanPengajuan data={pengajuan} />}
          </div>

          <form
            onSubmit={kirim}
            noValidate
            className="flex flex-col gap-space-4"
          >
            {/* Judul hanya muncul saat sudah ada pengajuan sebelumnya, karena
                di sanalah formulir ini butuh dipisahkan dari ringkasan di
                atasnya. Saat belum ada apa pun, H1 halaman sudah menamai
                formulir ini dan judul kedua hanya mengulanginya. */}
            {pengajuan && (
              <div>
                <h2 className="font-display text-section text-ink">
                  Ajukan ulang
                </h2>
                <p className="mt-space-2 text-body text-muted">
                  Satu akun menyimpan satu pengajuan. Pengajuan baru
                  menggantikan data di atas, bukan menambah di sebelahnya.
                </p>
              </div>
            )}

            {galatKirim && (
              <p
                role="alert"
                className="rounded-sm border border-danger bg-panel px-space-3 py-space-2 text-body text-danger"
              >
                {galatKirim}
              </p>
            )}

            <Field
              label="Nama sesuai identitas"
              value={fullName}
              onChange={setFullName}
              error={galatKolom.full_name}
              autoComplete="name"
              required
            />
            <Field
              label="NIK"
              value={nik}
              onChange={setNik}
              error={galatKolom.nik}
              required
              inputMode="numeric"
            />
            <Field
              label="Bank"
              value={bankCode}
              onChange={(nilai) => setBankCode(nilai as BankCode | "")}
              error={galatKolom.bank_code}
              options={OPSI_BANK}
              required
            />
            <Field
              label="Nama pemilik rekening"
              value={accountHolderName}
              onChange={setAccountHolderName}
              error={galatKolom.account_holder_name}
              required
            />
            <Field
              label="Nomor rekening"
              value={accountNumber}
              onChange={setAccountNumber}
              error={galatKolom.account_number}
              required
              inputMode="numeric"
            />

            {/* Satu-satunya aksi berlatar aksen di layar ini (DESIGN.md).
                Nama aksesibelnya tidak berganti saat permintaan berjalan;
                yang menyampaikan itu adalah aria-busy dan disabled. */}
            <Button
              type="submit"
              disabled={mengirim}
              aria-busy={mengirim}
              className="self-start"
            >
              {pengajuan ? "Ganti data verifikasi" : "Kirim pengajuan"}
            </Button>
          </form>
        </>
      )}
    </div>
  );
}

// Pernyataan ini wajib, bukan pelengkap, dan ia tetap di layar di ketiga
// keadaan muat. Backend mengirim `verifikasi_simulasi` sebagai field justru
// supaya antarmuka menyebutnya (backend/app/schemas/kyc.py), jadi kalimat ini
// adalah pasangan field itu di sisi yang dibaca orang.
function PernyataanSimulasi() {
  return (
    <aside className="flex gap-space-3 rounded-card border border-line bg-panel-raised px-space-4 py-space-4">
      {/* Ikon peringatan, bukan hiasan: ia menandai satu-satunya blok di
          halaman ini yang isinya kabar buruk tentang produk itu sendiri.
          Warnanya accent-2-text, token aksen untuk TEKS yang berbalik ikut
          tema (7.86:1 gelap, 5.10:1 terang di atas --panel-raised). */}
      <Icon name="alert" size={20} className="mt-space-1 text-accent-2-text" />
      <div className="flex flex-col gap-space-2">
        <p className="text-label font-semibold text-accent-2-text">
          Verifikasi ini simulasi
        </p>
        <p className="text-body text-ink">
          Tidak ada pengecekan ke Dukcapil dan tidak ada konfirmasi ke bank mana
          pun. Yang diperiksa hanya bentuk datanya: panjang dan pola NIK, nama
          bank yang dikenal, dan panjang nomor rekening. Lolos di sini tidak
          berarti identitas Anda sudah terbukti.
        </p>
        <p className="text-body text-muted">
          NIK dan nomor rekening tidak disimpan utuh. Yang tersimpan hanya empat
          digit terakhirnya, untuk ditampilkan kembali kepada Anda.
        </p>
      </div>
    </aside>
  );
}

function RingkasanPengajuan({ data }: { data: KycOut }) {
  const terverifikasi = data.status === "verified";
  return (
    <section className="rounded-card border border-line bg-panel px-space-4 py-space-4">
      <div className="flex items-center gap-space-2">
        {/* Statusnya tidak pernah disampaikan lewat warna saja: judul di
            sebelah ikon menyebutkannya sebagai teks. */}
        <Icon
          name={terverifikasi ? "check" : "alert"}
          size={20}
          className={terverifikasi ? "text-ok" : "text-danger"}
        />
        <h2 className="text-card-title font-semibold text-ink">
          {terverifikasi ? "Identitas terverifikasi" : "Pengajuan ditolak"}
        </h2>
      </div>
      <p className="mt-space-2 text-label text-muted">
        Diajukan {formatWaktu(data.submitted_at)}
      </p>

      {!terverifikasi && data.rejection_reason && (
        <p className="mt-space-3 rounded-sm border border-danger px-space-3 py-space-2 text-body text-ink">
          {data.rejection_reason}
        </p>
      )}

      <dl className="mt-space-4 grid gap-space-3 sm:grid-cols-2">
        <Baris label="Nama sesuai identitas" nilai={data.full_name} />
        <BarisSamar label="NIK" empatTerakhir={data.nik_last4} />
        <Baris
          label="Bank"
          nilai={NAMA_BANK[data.bank_code] ?? data.bank_code}
        />
        <Baris label="Nama pemilik rekening" nilai={data.account_holder_name} />
        <BarisSamar label="Nomor rekening" empatTerakhir={data.account_last4} />
      </dl>
    </section>
  );
}

function Baris({ label, nilai }: { label: string; nilai: string }) {
  return (
    <div>
      <dt className="text-label text-muted">{label}</dt>
      <dd className="break-words text-body text-ink">{nilai}</dd>
    </div>
  );
}

function BarisSamar({
  label,
  empatTerakhir,
}: {
  label: string;
  empatTerakhir: string;
}) {
  return (
    <div>
      <dt className="text-label text-muted">{label}</dt>
      <dd className="text-body text-ink">
        {/* Titik penyamar dibaca pembaca layar satu per satu sebagai "bullet",
            jadi bentuk visualnya disembunyikan dan digantikan kalimat yang
            menyebutkan maksudnya. */}
        <span aria-hidden="true" className="tabular">
          {`••••${empatTerakhir}`}
        </span>
        <span className="sr-only">{`empat digit terakhir ${empatTerakhir}`}</span>
      </dd>
    </div>
  );
}
