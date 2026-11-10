import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    // next-env.d.ts dihasilkan ulang oleh `next build` dan berkasnya sendiri
    // menulis "This file should not be edited". Sejak Next menambahkan baris
    // referensi ke .next/types/routes.d.ts di sana, aturan
    // @typescript-eslint/triple-slash-reference menolaknya, sehingga
    // `make check` gagal setiap kali build dijalankan lebih dulu, atas
    // berkas yang tidak boleh diperbaiki siapa pun.
    ignores: ["node_modules/**", ".next/**", "coverage/**", "next-env.d.ts"],
  },
];

export default eslintConfig;
