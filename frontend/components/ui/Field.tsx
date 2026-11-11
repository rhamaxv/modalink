"use client";

import { useId } from "react";

type FieldOption = {
  value: string;
  label: string;
};

type FieldProps = {
  label: string;
  type?: "text" | "email" | "password" | "date" | "number";
  value: string;
  onChange: (value: string) => void;
  error?: string;
  required?: boolean;
  autoComplete?: string;
  /** Saat diisi, Field merender <select> berisi opsi ini, bukan <input>. */
  options?: FieldOption[];
  /** Saat true, Field merender <textarea>, untuk teks panjang seperti deskripsi. */
  multiline?: boolean;
  /** Batas bawah untuk type="number" atau type="date" (format sesuai tipe input native). */
  min?: string;
  /** Papan tombol yang dimunculkan ponsel. Dipakai field yang isinya angka
   * tapi BUKAN type="number": nomor rekening dan NIK berawalan nol akan
   * rusak oleh input numerik bawaan, sementara papan tombol angka tetap
   * dibutuhkan supaya tidak ada yang mengetik enam belas digit di papan
   * huruf. */
  inputMode?: "numeric" | "tel";
};

// Satu komponen dipakai di setiap field di seluruh aplikasi, supaya
// <label htmlFor>, aria-describedby, dan aria-invalid terhubung dengan benar
// di satu tempat, bukan diingat ulang setiap kali form baru ditulis. Dipakai
// juga untuk field pilihan (peran saat daftar), bukan hanya teks bebas.
export function Field({
  label,
  type = "text",
  value,
  onChange,
  error,
  required,
  autoComplete,
  options,
  multiline,
  min,
  inputMode,
}: FieldProps) {
  const id = useId();
  const errorId = `${id}-error`;
  // Kelas .control didefinisikan sekali di app/globals.css dan dipakai setiap
  // kontrol formulir di aplikasi ini. Versi sebelumnya memakai border-ink,
  // yaitu putih penuh di tema gelap: batas kontrol seterang itu membuat
  // formulir terbaca sebagai deretan kotak, bukan sebagai field. Ia juga
  // tidak pernah mencabut gaya bawaan sistem, sehingga panah <select>,
  // pemilih tanggal, dan tombol naik-turun angka tetap digambar browser.
  const controlClassName = "control";

  return (
    <div className="flex flex-col gap-space-1">
      <label htmlFor={id} className="text-label font-medium text-muted">
        {label}
        {/* Tanda bintang hanya dekorasi visual; status wajib yang sungguh
            terbaca pembaca layar datang dari atribut required di bawah. */}
        {required && <span aria-hidden="true"> *</span>}
      </label>
      {options ? (
        <select
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          className={controlClassName}
        >
          {options.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      ) : multiline ? (
        <textarea
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          className={controlClassName}
        />
      ) : (
        <input
          id={id}
          type={type}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          required={required}
          min={min}
          inputMode={inputMode}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          autoComplete={autoComplete}
          className={controlClassName}
        />
      )}
      {error && (
        <p id={errorId} role="alert" className="text-label text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
