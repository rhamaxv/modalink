# Fase 12. Deploy ke VPS

**Hasil:** aplikasi berjalan di VPS, dapat diakses juri lewat browser dengan HTTPS, dan tetap
hidup sepanjang masa penilaian.

**Ini wajib, bukan opsional.** Panitia menyatakan "Web: aplikasi wajib sudah di-deploy dan dapat
diakses melalui browser". Repositori yang kodenya bagus tapi aplikasinya tidak bisa dibuka
dinyatakan tidak memenuhi persyaratan demonstrasi.

**Spec terkait:** [aturan-lomba.md](../docs/aturan-lomba.md), [12-non-functional](../prd/12-non-functional.md)

## Struktur file

```
backend/Dockerfile
frontend/Dockerfile
docker-compose.prod.yml
Caddyfile                  # reverse proxy + HTTPS otomatis
.env.example               # nama variabel saja, tanpa nilai
deploy/README.md           # langkah deploy, dirujuk README utama
```

---

### Task 1: Dockerfile backend dan frontend

**Files:**
- Create: `backend/Dockerfile`, `frontend/Dockerfile`, `.dockerignore`

- [ ] **Step 1: Tulis Dockerfile backend**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# Migrasi dijalankan saat start, bukan saat build, supaya image tidak butuh database.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

- [ ] **Step 2: Tulis Dockerfile frontend**

```dockerfile
# frontend/Dockerfile
FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
CMD ["node", "server.js"]
```

`output: "standalone"` wajib diset di `next.config.ts`, kalau tidak folder `standalone` tidak
dihasilkan dan tahap runner gagal.

- [ ] **Step 3: Uji build lokal**

Run: `docker build -t logicodix-backend ./backend && docker build -t logicodix-frontend ./frontend`
Expected: keduanya sukses

- [ ] **Step 4: Uji image backend benar-benar jalan**

Run: `docker run --rm -e DATABASE_URL=... -p 8000:8000 logicodix-backend` lalu `curl localhost:8000/health`
Expected: `{"status":"ok","database":"ok"}`

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile frontend/Dockerfile .dockerignore
git commit -m "chore: add production Dockerfiles for backend and frontend"
```

---

### Task 2: Compose produksi dan reverse proxy

**Files:**
- Create: `docker-compose.prod.yml`, `Caddyfile`, `.env.example`

Caddy dipilih karena HTTPS-nya otomatis lewat Let's Encrypt tanpa konfigurasi sertifikat manual.
Dengan waktu tersisa, itu menghemat setengah hari dibanding nginx plus certbot.

- [ ] **Step 1: Tulis compose produksi**

```yaml
# docker-compose.prod.yml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      retries: 20
    restart: unless-stopped

  backend:
    build: ./backend
    environment:
      ENV: prod
      DATABASE_URL: ${DATABASE_URL}
      JWT_SECRET: ${JWT_SECRET}
      SCORING_ENGINE: ${SCORING_ENGINE}
      GEMINI_API_KEY: ${GEMINI_API_KEY}
    depends_on:
      db: { condition: service_healthy }
    restart: unless-stopped

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_BASE: ${NEXT_PUBLIC_API_BASE}
    depends_on: [backend]
    restart: unless-stopped

  caddy:
    image: caddy:2-alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddydata:/data
    depends_on: [frontend, backend]
    restart: unless-stopped

volumes: { pgdata: {}, caddydata: {} }
```

`ENV: prod` membuat router internal tidak didaftarkan, sehingga endpoint jam virtual dan seed
tidak terbuka di publik ([BR-63](../prd/07-business-rules.md)).

`restart: unless-stopped` pada keempat service penting: panitia mewajibkan layanan tetap aktif
sepanjang penilaian, dan VPS bisa reboot kapan saja.

- [ ] **Step 2: Tulis Caddyfile**

```
{$DOMAIN} {
    handle /api/* {
        reverse_proxy backend:8000
    }
    handle {
        reverse_proxy frontend:3000
    }
}
```

- [ ] **Step 3: Tulis `.env.example`**

Wajib ada, dan **hanya nama variabel tanpa nilai asli**
([aturan-lomba.md](../docs/aturan-lomba.md)):

```
# Database
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
DATABASE_URL=

# Aplikasi
ENV=
JWT_SECRET=
DOMAIN=
NEXT_PUBLIC_API_BASE=

# AI
SCORING_ENGINE=
GEMINI_API_KEY=
GEMINI_MODEL=
```

- [ ] **Step 4: Pastikan `.env` tidak pernah ter-commit**

Run: `git check-ignore -v .env && git log --all --full-history -- .env`
Expected: baris pertama menunjukkan `.gitignore` menangkapnya, baris kedua kosong

- [ ] **Step 5: Commit**

```bash
git add docker-compose.prod.yml Caddyfile .env.example
git commit -m "chore: add production compose stack with Caddy and HTTPS"
```

---

### Task 3: Deploy pertama ke VPS

**Files:**
- Create: `deploy/README.md`

- [ ] **Step 1: Siapkan VPS**

```bash
# Di VPS, sebagai root
apt update && apt install -y docker.io docker-compose-plugin git
ufw allow 22 && ufw allow 80 && ufw allow 443 && ufw enable
```

- [ ] **Step 2: Arahkan domain**

Buat A record yang menunjuk ke IP VPS. HTTPS Caddy butuh domain yang sudah resolve, jadi ini
dikerjakan lebih dulu dan diberi waktu propagasi.

- [ ] **Step 3: Clone dan jalankan**

```bash
git clone <url-repo> /opt/logicodix && cd /opt/logicodix
cp .env.example .env    # lalu isi nilainya langsung di VPS, tidak pernah di-commit
docker compose -f docker-compose.prod.yml up -d --build
```

- [ ] **Step 4: Verifikasi dari luar, bukan dari dalam VPS**

```bash
curl -sS https://<domain>/api/v1/health
curl -sSI https://<domain> | head -1
```

Expected: health mengembalikan `{"status":"ok","database":"ok"}`, halaman utama `200`.

Diuji dari mesin lain, karena `curl localhost` di dalam VPS melewati firewall dan DNS, dua hal
yang justru paling sering salah.

- [ ] **Step 5: Buat akun demonstrasi**

Panitia mewajibkan akun demonstrasi karena aplikasi memakai autentikasi, dan juri tidak boleh
diminta mendaftar sendiri. Buat satu akun per peran lewat endpoint register, lalu catat
kredensialnya untuk README.

| Peran | Email | Password |
| --- | --- | --- |
| Investor | `investor@demo.logicodix` | dicatat di README |
| UMKM | `umkm@demo.logicodix` | dicatat di README |
| Komunitas | `warga@demo.logicodix` | dicatat di README |

Password akun demo **boleh** ada di README. Itu akun demonstrasi, bukan kredensial rahasia, dan
panitia memang memintanya.

- [ ] **Step 6: Isi data demo**

Seed dijalankan sekali lewat `docker compose exec backend python -m app.seed.demo`, bukan lewat
endpoint, karena router internal tidak terdaftar di `ENV=prod`.

- [ ] **Step 7: Tulis `deploy/README.md`**

Langkah di atas, ditulis ulang supaya bisa diulang dari nol. Dirujuk dari README utama sebagai
panduan instalasi.

- [ ] **Step 8: Commit**

```bash
git add deploy/README.md
git commit -m "docs: add VPS deployment guide"
```

---

### Task 4: Jaga layanan tetap hidup sampai penilaian selesai

Panitia mewajibkan layanan pendukung, **termasuk kuota API**, tetap aktif selama penilaian.
Penilaian berlangsung sampai pengumuman finalis 21 November, dan Grand Final 29 November.

- [ ] **Step 1: Pastikan restart otomatis setelah reboot**

Run: `sudo reboot`, tunggu, lalu `curl https://<domain>/api/v1/health` dari luar
Expected: hidup kembali tanpa intervensi

- [ ] **Step 2: Siapkan jalur aman saat kuota Gemini habis**

Kuota Gemini free tier bisa habis saat juri mencoba berkali-kali. Kalau itu terjadi, proposal
baru akan berstatus `scoring_status = failed`, yang benar secara aturan tapi buruk saat dinilai.

Mitigasinya: data seed sudah memuat enam proposal yang **sudah punya hasil scoring tersimpan**,
jadi panel skor AI tetap terlihat penuh meski pemanggilan baru gagal. Juri melihat fitur AI
bekerja, dan proposal baru yang mereka buat sendiri menunjukkan penanganan kegagalan yang benar.

- [ ] **Step 3: Catat tanggal kedaluwarsa apa pun yang bisa kedaluwarsa**

Domain, sertifikat (otomatis diperbarui Caddy), dan kuota API. Ditulis di `deploy/README.md`.

- [ ] **Step 4: Jangan sentuh deployment setelah code freeze**

Setelah 14 November 23.59, deployment **tidak boleh diubah** kecuali memulihkan ketersediaan
layanan tanpa mengubah kode, fitur, atau data. Mengubahnya untuk memengaruhi penilaian adalah
bentuk pelanggaran yang disebut eksplisit di guidebook.

## Gerbang keluar fase 12

- [ ] `https://<domain>` terbuka dari jaringan lain, bukan hanya dari VPS
- [ ] `https://<domain>/api/v1/health` mengembalikan status database `ok`
- [ ] Sertifikat HTTPS valid, tidak ada peringatan browser
- [ ] `ENV=prod` membuat router internal tidak terdaftar, diuji dengan `curl` ke `/api/v1/internal/clock/tick` yang harus `404`
- [ ] Ketiga akun demonstrasi bisa login dari browser
- [ ] Data seed tampil, panel skor AI terisi
- [ ] Stack hidup kembali sendiri setelah VPS di-reboot
- [ ] `.env` tidak pernah masuk riwayat git
