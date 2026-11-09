"use client";

import { useId } from "react";

type FieldOption = {
  value: string;
  label: string;
};

type FieldProps = {
  label: string;
  type?: "text" | "email" | "password";
  value: string;
  onChange: (value: string) => void;
  error?: string;
  required?: boolean;
  autoComplete?: string;
  /** Saat diisi, Field merender <select> berisi opsi ini, bukan <input>. */
  options?: FieldOption[];
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
}: FieldProps) {
  const id = useId();
  const errorId = `${id}-error`;

  return (
    <div className="flex flex-col gap-ruang-1">
      <label htmlFor={id} className="text-[0.8125rem] font-medium text-muted">
        {label}
        {required && <span aria-hidden="true"> *</span>}
      </label>
      {options ? (
        <select
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          className="min-h-[44px] rounded-kecil border border-ink bg-paper px-ruang-3 py-ruang-2 text-base leading-[1.6] text-ink"
        >
          {options.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={id}
          type={type}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          autoComplete={autoComplete}
          className="min-h-[44px] rounded-kecil border border-ink bg-paper px-ruang-3 py-ruang-2 text-base leading-[1.6] text-ink"
        />
      )}
      {error && (
        <p id={errorId} role="alert" className="text-[0.8125rem] text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
