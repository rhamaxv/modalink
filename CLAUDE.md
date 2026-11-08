# Logicodix

Platform crowdfunding UMKM: investor membuat campaign, UMKM mengajukan proposal, AI menilai,
beberapa investor patungan mendanai, dan dana cair bertahap per milestone.

Dokumen sumber kebenaran ada di `.claude/`. Baca sebelum menulis kode.

## Peta dokumen

| Butuh tahu | Baca |
| --- | --- |
| Apa yang dibangun dan kenapa | `.claude/prd/README.md` |
| Urutan pengerjaan dan definisi selesai | `.claude/plan/README.md` |
| Keputusan arsitektur yang sudah dikunci | `.claude/docs/decisions.md` |
| Arah visual | `DESIGN.md` |

## Aturan yang tidak bisa ditawar

1. **Logika bisnis tidak boleh tinggal di router.** Aturan uang dan status hidup di
   `backend/app/domain/` sebagai fungsi murni: tanpa sesi database, tanpa objek Request.
   Lihat `.claude/skills/fastapi-domain-service/SKILL.md`.
2. **Status funding punya satu penulis.** Hanya `recompute_funding_status()` yang boleh
   mengubah `Listed` / `Partially funded` / `Funded`. Lihat `.claude/skills/state-machine-guard/SKILL.md`.
3. **Uang tidak pernah di-update, hanya dicatat.** Setiap pergerakan dana adalah baris baru di
   `ledger_entries`. Saldo dihitung dari penjumlahan. Lihat `.claude/skills/ledger-invariants/SKILL.md`.
4. **Regression suite harus hijau sebelum klaim selesai apa pun.** `make test-regression`.
   Lihat `.claude/skills/testing-and-regression/SKILL.md`.
5. **Tidak ada test yang memanggil Gemini sungguhan** kecuali yang ditandai `@pytest.mark.live`,
   dan itu di-skip secara default. Lihat `.claude/skills/gemini-structured-output/SKILL.md`.

## Batasan lomba yang mengikat

Project ini adalah karya untuk Logicodix 2026. Aturan panitia ada di
`.claude/docs/aturan-lomba.md` dan **wajib dibaca sebelum commit pertama**. Yang paling sering
menjebak:

| Aturan | Akibat melanggar |
| --- | --- |
| Code freeze **14 November 2026, 23.59 WIB** | Perubahan setelahnya tidak dinilai |
| Dilarang bulk upload satu commit di akhir | Diskualifikasi |
| Dilarang force push, rebase, squash, hapus commit, ubah tanggal setelah push | Diskualifikasi |
| Dilarang hardcode API key; `.env` wajib di `.gitignore`; wajib ada `.env.example` | Tanggung jawab tim |
| README.md wajib memuat diagram arsitektur, akun demonstrasi, dan dokumentasi penggunaan AI | Submission tidak memenuhi syarat |
| Web wajib **sudah di-deploy** dan bisa diakses juri lewat browser | Submission tidak memenuhi syarat |

### Format pesan commit

Dipatok panitia, dan tidak boleh menyimpang:

```
feat: add user authentication
fix: resolve login validation bug
docs: update project installation guide
```

- Awalan: `feat`, `fix`, `docs`, `style`, `refactor`, `chore`. **Tidak ada `test`.**
- Satu kalimat, bahasa Inggris, tanpa scope dalam kurung.
- Test dan implementasinya masuk **satu commit `feat:`** yang sama.
- **Tidak ada baris `Co-Authored-By`.**
- Pesan `update`, `test`, atau `final` ditolak panitia karena tidak menjelaskan perubahan.

## Perintah

```
make up              # Postgres + backend via Docker Compose
make migrate         # alembic upgrade head
make test            # unit + integration + regression
make test-regression # hanya invarian; wajib hijau sebelum bilang selesai
make check           # ruff + mypy + eslint + tsc + semua test
```

<!-- antislop:start -->
## antislop

Modul anti-AI-slop terpasang sebagai plugin Claude Code. Untuk pekerjaan UI, copy, aksesibilitas,
layout mobile, atau komentar kode, muat skill `antislop:antislop` (core) lalu yang sesuai tugasnya:

- UI / visual: `antislop:antislop-ui`
- Copy & teks: `antislop:antislop-copywriting`
- Manusia & aksesibilitas: `antislop:antislop-human`
- Mobile / responsif: `antislop:antislop-layoutmobile`
- Komentar kode: `antislop:antislop-code`

Mode yang dipilih pemilik project: **DURING** (aturan diterapkan sambil mengerjakan, bukan audit
setelah jadi). Arah design ada di `DESIGN.md` dan wajib dibaca sebelum UI apa pun ditulis.
Setiap penyerahan UI ditutup dengan Delivery Gate berupa laporan PASS/FAIL per aturan.
<!-- antislop:end -->
