"use client";

import { useId, useRef } from "react";
import { Field } from "@/components/ui/Field";
import { formatRupiah } from "@/lib/money";

export type MilestoneDraft = {
  title: string;
  description: string;
  /** Disimpan sebagai string digit, bukan number: input terkontrol butuh
   *  representasi teks persis apa yang tampil, termasuk saat kosong. */
  amount: string;
};

// BR-14: proposal wajib punya minimal 2 milestone. Dua baris pertama tidak
// pernah bisa dihapus, supaya jumlah baris tidak pernah turun di bawah ini.
export const MIN_MILESTONES = 2;

export function nominalMilestone(milestone: MilestoneDraft): number {
  return Number(milestone.amount) || 0;
}

export function totalMilestone(milestones: MilestoneDraft[]): number {
  return milestones.reduce((total, m) => total + nominalMilestone(m), 0);
}

type MilestonePlanProps = {
  requestedAmount: number;
  milestones: MilestoneDraft[];
  onChange: (milestones: MilestoneDraft[]) => void;
};

// Validasi jumlah milestone jalan di klien (lihat DESIGN.md dan brief fase
// 11 task 7): UMKM langsung tahu selisihnya tanpa menunggu respons server,
// dan BR-14 (jumlah milestone harus pas dengan dana yang diminta) sudah
// diperiksa sebelum form ini sempat dikirim.
export function MilestonePlan({ requestedAmount, milestones, onChange }: MilestonePlanProps) {
  const total = totalMilestone(milestones);
  const selisih = requestedAmount - total;

  function updateRow(index: number, patch: Partial<MilestoneDraft>) {
    onChange(milestones.map((m, i) => (i === index ? { ...m, ...patch } : m)));
  }

  function addRow() {
    onChange([...milestones, { title: "", description: "", amount: "" }]);
  }

  function removeRow(index: number) {
    onChange(milestones.filter((_, i) => i !== index));
  }

  return (
    <div className="flex flex-col gap-space-4" data-pola="daftar-bernomor">
      {milestones.map((milestone, index) => (
        <MilestoneRow
          key={index}
          index={index}
          milestone={milestone}
          onChange={(patch) => updateRow(index, patch)}
          // Baris ke-0 dan ke-1 adalah dua tahap minimum (BR-14) dan tidak
          // pernah bisa dihapus; baris tambahan di atas itu boleh dihapus.
          onRemove={
            milestones.length > MIN_MILESTONES && index >= MIN_MILESTONES
              ? () => removeRow(index)
              : undefined
          }
        />
      ))}
      <button
        type="button"
        onClick={addRow}
        className="min-h-[44px] self-start rounded-sm border border-ink px-space-3 py-space-2 text-body font-semibold text-ink"
      >
        Tambah tahap
      </button>
      <p role="status" aria-live="polite" className="tabular text-body font-medium text-ink">
        {selisih === 0
          ? "Jumlah sudah pas dengan dana yang diminta."
          : selisih > 0
            ? `Kurang ${formatRupiah(selisih)} dari dana yang diminta.`
            : `Lebih ${formatRupiah(Math.abs(selisih))} dari dana yang diminta.`}
      </p>
    </div>
  );
}

type MoneyFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
};

// Field (fase 10) tidak boleh diubah di sini dan type="number" bawaannya
// tidak cocok untuk rupiah (mengizinkan "e"/"+"/"-"/"." lalu membulatkan
// diam-diam), sementara filter digit di handleAmountChange butuh <input>
// bertipe teks sungguhan. inputMode="numeric" tetap memunculkan keypad angka
// di ponsel tanpa kehilangan filter itu (laporan review: nominal milestone
// dan nominal proposal dulu sama-sama tidak punya inputMode, padahal
// CampaignForm sudah type="number" untuk nominal sejenis).
function MoneyField({ label, value, onChange, required }: MoneyFieldProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-space-1">
      <label htmlFor={id} className="text-label font-medium text-muted">
        {label}
        {required && <span aria-hidden="true"> *</span>}
      </label>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        className="control"
      />
    </div>
  );
}

type MilestoneRowProps = {
  index: number;
  milestone: MilestoneDraft;
  onChange: (patch: Partial<MilestoneDraft>) => void;
  onRemove?: () => void;
};

function MilestoneRow({ index, milestone, onChange, onRemove }: MilestoneRowProps) {
  // Mengunci kolom nominal begitu karakter non-digit terdeteksi: input
  // terkontrol React menimpa paksa nilai DOM kembali ke state setiap kali
  // event input terjadi (perilaku bawaan React untuk <input> terkontrol),
  // jadi tanpa kunci ini, karakter valid yang diketik TEPAT setelah karakter
  // tidak valid akan diterima begitu saja karena titik desimalnya sudah
  // ditimpa duluan. Kunci lepas sendiri begitu nilai mengecil (backspace),
  // supaya pengguna tetap bisa membetulkan ketikannya.
  const lockedRef = useRef(false);

  function handleAmountChange(raw: string) {
    const isShrinking = raw.length < milestone.amount.length;
    if (isShrinking) {
      lockedRef.current = false;
      onChange({ amount: raw.replace(/[^0-9]/g, "") });
      return;
    }
    if (lockedRef.current) {
      // Kunci juga lepas saat kolomnya memang SUDAH kosong dan yang masuk
      // seluruhnya digit. Tanpa cabang ini kolomnya punya keadaan mati:
      // karakter non-digit yang diketik paling pertama mengunci kolom pada
      // nilai kosong, lalu `isShrinking` di atas tidak pernah bisa benar
      // karena tidak ada apa pun yang bisa mengecil dari string kosong --
      // backspace tidak menolong, dan kolom itu tidak bisa diisi lagi
      // sampai halaman dimuat ulang. Ditemukan saat perekaman demo, bukan
      // oleh test: seluruh test mengetik digit lebih dulu.
      if (milestone.amount === "" && !/[^0-9]/.test(raw)) {
        lockedRef.current = false;
      } else {
        return;
      }
    }
    if (/[^0-9]/.test(raw)) {
      lockedRef.current = true;
      return;
    }
    onChange({ amount: raw });
  }

  return (
    <div
      className="flex flex-col gap-space-3 rounded-card border border-line bg-panel p-space-4"
      data-pola="tabel-padat"
    >
      <p className="text-label font-medium text-muted">Tahap {index + 1}</p>
      <Field
        label={`Judul tahap ${index + 1}`}
        value={milestone.title}
        onChange={(value) => onChange({ title: value })}
        required
      />
      <Field
        label={`Rincian tahap ${index + 1}`}
        value={milestone.description}
        onChange={(value) => onChange({ description: value })}
        required
      />
      <MoneyField
        label={`Nominal tahap ${index + 1}`}
        value={milestone.amount}
        onChange={handleAmountChange}
        required
      />
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          // border-line-strong, bukan border-line: border-line mengukur
          // 1.27:1 di atas bg-panel, gagal ambang 3:1 untuk batas kontrol
          // interaktif (laporan review, satu-satunya tombol yang terlewat
          // saat batas interaktif lain di aplikasi ini sudah dipindahkan).
          className="min-h-[44px] self-start rounded-sm border border-line-strong px-space-3 py-space-2 text-body font-medium text-muted"
        >
          Hapus tahap {index + 1}
        </button>
      )}
    </div>
  );
}
