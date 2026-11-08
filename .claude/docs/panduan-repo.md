# Panduan repositori Modalink

Disusun dari ketentuan di [aturan-lomba.md](aturan-lomba.md). Tujuannya satu: membuat pelanggaran
aturan **sulit dilakukan secara tidak sengaja**, bukan sekadar diingat-ingat.

---

## Identitas repo

| Hal | Nilai | Alasan |
| --- | --- | --- |
| Nama | `modalink` | Nama produk, bukan nama lomba. `logicodix` adalah nama kompetisi dan akan membingungkan juri yang membuka puluhan repo serupa |
| Visibility | **Public** | Diwajibkan sejak submission sampai penilaian selesai |
| Default branch | `main` | |
| Description | `Platform crowdfunding UMKM dengan AI scoring, co-funding, dan pencairan dana bertahap per milestone.` | Satu kalimat ini yang terbaca juri sebelum mereka klik apa pun |
| Topics | `hackathon` `umkm` `crowdfunding` `fastapi` `nextjs` `postgresql` `gemini-api` | Membantu juri mengenali stack tanpa membuka kode |
| About, bagian Website | URL aplikasi yang sudah di-deploy | Juri menilai lewat browser, jadi tautannya harus satu klik dari halaman repo |

## Setelan yang mencegah pelanggaran

Panitia melarang force push, rebase, squash, dan penghapusan commit setelah di-push. Hukumannya
diskualifikasi. Jangan mengandalkan ingatan, matikan kemampuannya.

**Settings → General → Pull Requests:**

- [ ] Matikan **Allow squash merging**
- [ ] Matikan **Allow rebase merging**
- [ ] Biarkan hanya **Allow merge commits**

Dengan begitu, bahkan kalau nanti ada yang memakai pull request, tombol yang melanggar aturan
tidak ada di layar.

**Settings → Code security:**

- [ ] Nyalakan **Secret scanning**
- [ ] Nyalakan **Push protection**

Push protection menolak push yang memuat API key sebelum sampai ke GitHub. Ini jaring pengaman
sungguhan untuk larangan hardcode kredensial, dan gratis untuk repo publik.

**Yang sebaiknya tidak dinyalakan:** branch protection yang mewajibkan pull request atau review.
Tim kecil dengan tenggat lima hari akan terhambat, dan aturan lomba tidak memintanya.

## Identitas commit

Panitia mewajibkan **seluruh commit berasal dari akun GitHub anggota terdaftar**. Commit dari akun
lain dibaca sebagai keterlibatan pihak luar tim, dan itu bentuk pelanggaran.

Git lokal saat ini memakai:

```
user.name  = rhamaxv
user.email = rhamaxv@gmail.com
```

- [ ] Pastikan email itu **terdaftar di akun GitHub anggota tim**, di Settings → Emails. Kalau
      tidak, commit akan muncul tanpa tertaut ke akun mana pun, dan sulit dibuktikan asalnya.
- [ ] Tambahkan seluruh anggota sebagai **Collaborator**, dan pastikan masing-masing commit dari
      akun sendiri. Commit yang semuanya dari satu akun akan ditanya juri.

Periksa kapan saja dengan:

```bash
git log --format='%an <%ae>' | sort -u
```

## Struktur

Panitia membolehkan backend dan frontend dalam satu repo, **asal nama foldernya dipisahkan jelas
dan dijelaskan di README**.

```
modalink/
├─ README.md              wajib, di direktori utama
├─ .env.example           wajib, nama variabel tanpa nilai
├─ .gitignore             .env sudah ditutup
├─ docker-compose.yml     pengembangan lokal
├─ docker-compose.prod.yml
├─ Caddyfile
├─ backend/               FastAPI, Python 3.12
├─ frontend/              Next.js, TypeScript
├─ deploy/                panduan deploy VPS
└─ .claude/               spec, plan, konvensi (tidak dinilai, tapi menunjukkan proses)
```

`.claude/` sengaja ikut di-commit. Rubrik memberi 25% untuk Software Engineering yang menilai
arsitektur dan dokumentasi, dan isi folder itu adalah bukti bahwa produk dirancang sebelum
ditulis, bukan ditambal sambil jalan.

## Ritme commit

Panitia menilai **keberkalaan** commit, dan melarang bulk upload di akhir.

- Satu commit per task selesai, bukan satu commit per fase.
- Push setiap kali selesai beberapa commit, jangan menumpuk sampai hari terakhir. Tanggal commit
  memang tersebar, tapi riwayat push yang menumpuk tetap berpeluang dibaca sebagai bulk upload.
- Format: `feat: add user authentication`. Awalan `feat`, `fix`, `docs`, `style`, `refactor`,
  `chore`. Tanpa `test`. Tanpa `Co-Authored-By`.

## Sebelum submission

- [ ] README memuat seluruh poin wajib, termasuk **diagram arsitektur**, **akun demonstrasi**, dan
      **dokumentasi penggunaan AI**. Tiga ini yang paling sering terlewat
- [ ] `.env` tidak pernah ada di riwayat: `git log --all --full-history -- .env` harus kosong
- [ ] Tidak ada kredensial di riwayat: `git log -p | grep -iE "AIza|sk-|SECRET|PASSWORD" | head`
- [ ] Repo sudah Public
- [ ] Aplikasi terbuka dari jaringan lain, bukan hanya dari mesin sendiri
- [ ] Commit hash final dicatat, dan **tidak ada commit setelahnya**
- [ ] Video demo berasal dari commit final itu

## Yang tidak boleh dilakukan, apa pun alasannya

| Tindakan | Akibat |
| --- | --- |
| `git push --force` | Diskualifikasi |
| `git rebase` pada commit yang sudah di-push | Diskualifikasi |
| Squash merge | Diskualifikasi |
| `git commit --amend` setelah push | Diskualifikasi |
| Mengubah tanggal commit | Diskualifikasi |
| Menghapus atau mem-private repo sebelum pengumuman | Submission tidak sah |
| Mengubah kode atau deployment setelah code freeze | Diskualifikasi |

Kalau ada commit yang salah, perbaiki dengan **commit baru**. Riwayat yang berantakan tapi jujur
jauh lebih aman daripada riwayat rapi yang ditulis ulang.
