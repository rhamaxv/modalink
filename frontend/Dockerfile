FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Repo ini tidak punya folder public/ (favicon dkk dilayani dari app/), tapi
# tahap runner di bawah tetap meng-copy-nya; tanpa baris ini COPY itu gagal
# begitu seseorang membangun ulang tanpa folder tersebut.
RUN mkdir -p public
# NEXT_PUBLIC_* di-inline ke bundle client saat build, bukan dibaca saat
# container start. Mengirimnya lewat `environment:` di compose saja tidak
# berpengaruh; harus masuk sebagai build arg di sini. Kosong pun aman: kode
# frontend default ke path relatif /api/v1 yang pas untuk setup Caddy
# satu-domain di docker-compose.prod.yml.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
CMD ["node", "server.js"]
