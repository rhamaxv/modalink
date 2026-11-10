"use client";

import { useId } from "react";

type Pilihan = { value: string; label: string };

type SelectProps = {
  label: string;
  value: string;
  options: Pilihan[];
  onChange: (value: string) => void;
};

// <select> asli, bukan menu yang dibangun dari <div>: kontrol penyaring di
// halaman daftar wajib bisa dioperasikan keyboard dan dibaca pembaca layar
// tanpa kode tambahan, dan di layar sentuh ia memanggil pemilih bawaan
// sistem yang jauh lebih enak dipakai daripada daftar melayang buatan
// sendiri.
//
// Label terlihat, bukan placeholder atau hanya aria-label: begitu sebuah
// pilihan dipilih, placeholder hilang dan pengguna kehilangan satu-satunya
// keterangan tentang apa yang sedang disaring.
export function Select({ label, value, options, onChange }: SelectProps) {
  const id = useId();
  return (
    <div className="flex items-center gap-space-2">
      <label htmlFor={id} className="text-label font-medium text-muted">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        // border-line-strong (3.94:1), bukan border-line: ini batas kontrol
        // interaktif, dan DESIGN.md memisahkan dua token itu justru untuk
        // kasus ini.
        className="min-h-[44px] rounded-sm border border-line-strong bg-panel px-space-2 text-body font-medium text-ink"
      >
        {options.map((pilihan) => (
          <option key={pilihan.value} value={pilihan.value}>
            {pilihan.label}
          </option>
        ))}
      </select>
    </div>
  );
}
