# 09. Data Model

PostgreSQL 16, SQLModel sebagai definisi, Alembic untuk migrasi. Seluruh nominal adalah `BIGINT`
rupiah utuh ([BR-50](07-business-rules.md)).

Constraint yang bisa ditegakkan di database **ditegakkan di database**. Validasi di Python adalah
lapisan pertama untuk pesan error yang enak dibaca, bukan satu-satunya penjaga.

---

## `users`

| Kolom | Tipe | Catatan |
| --- | --- | --- |
| `id` | UUID PK | |
| `email` | TEXT | `UNIQUE`, disimpan lowercase |
| `password_hash` | TEXT | argon2, tidak pernah keluar dari API |
| `name` | TEXT | |
| `role` | ENUM | `investor`, `umkm`, `community` |
| `created_at` | TIMESTAMPTZ | |

## `campaigns`

| Kolom | Tipe | Catatan |
| --- | --- | --- |
| `id` | UUID PK | |
| `investor_id` | UUID FK -> `users.id` | |
| `title`, `description` | TEXT | |
| `sector` | ENUM | daftar sektor tetap |
| `target_amount` | BIGINT | `CHECK > 0` |
| `apply_deadline` | TIMESTAMPTZ | Batas pengajuan proposal |
| `funding_deadline` | TIMESTAMPTZ | Batas dana terkumpul. `CHECK funding_deadline > apply_deadline` |
| `score_threshold` | SMALLINT | `CHECK BETWEEN 0 AND 100`, default 60 |
| `status` | ENUM | `open`, `closed` |
| `created_at` | TIMESTAMPTZ | |

Index: `(status, sector)` untuk daftar publik.

## `proposals`

| Kolom | Tipe | Catatan |
| --- | --- | --- |
| `id` | UUID PK | |
| `campaign_id` | UUID FK -> `campaigns.id` | |
| `umkm_id` | UUID FK -> `users.id` | |
| `business_name` | TEXT | |
| `business_profile`, `fund_usage_plan`, `business_projection` | TEXT | |
| `requested_amount` | BIGINT | `CHECK > 0` |
| `status` | ENUM | `submitted`, `listed`, `partially_funded`, `rejected`, `funded`, `failed`, `completed` |
| `scoring_status` | ENUM | `pending`, `processing`, `done`, `failed` |
| `lead_investor_id` | UUID FK -> `users.id` NULL | dihitung ulang tiap pledge berubah |
| `funded_at` | TIMESTAMPTZ NULL | |
| `created_at` | TIMESTAMPTZ | |

Constraint yang menegakkan [BR-13](07-business-rules.md):

```sql
CREATE UNIQUE INDEX uq_proposal_aktif_per_umkm_per_campaign
  ON proposals (campaign_id, umkm_id)
  WHERE status NOT IN ('rejected', 'failed');
```

Partial unique index ini adalah alasan test berjalan di Postgres dan bukan SQLite
([D-10](../docs/decisions.md)): SQLite tidak punya padanannya yang setara.

Index: `(campaign_id, status)` dan `(umkm_id, created_at DESC)`.

## `proposal_milestones`

| Kolom | Tipe | Catatan |
| --- | --- | --- |
| `id` | UUID PK | |
| `proposal_id` | UUID FK -> `proposals.id` | |
| `seq` | SMALLINT | `UNIQUE (proposal_id, seq)`, `CHECK >= 1` |
| `title`, `description` | TEXT | |
| `amount` | BIGINT | `CHECK > 0` |
| `status` | ENUM | `pending`, `reported`, `disbursed` |
| `disbursed_at` | TIMESTAMPTZ NULL | |

Aturan "jumlah `amount` sama dengan `requested_amount`" ([BR-14](07-business-rules.md)) adalah
invarian lintas baris, jadi ditegakkan di service saat submit, bukan oleh `CHECK` per baris.
Regression test memeriksanya setelah setiap submit.

## `milestone_reports`

| Kolom | Tipe | Catatan |
| --- | --- | --- |
| `id` | UUID PK | |
| `milestone_id` | UUID FK -> `proposal_milestones.id` | |
| `umkm_id` | UUID FK -> `users.id` | |
| `narrative` | TEXT | |
| `metrics` | JSONB NULL | pasangan label dan angka |
| `review_status` | ENUM | `pending`, `approved`, `rejected` |
| `reviewed_by` | UUID FK -> `users.id` NULL | |
| `reviewer_note` | TEXT NULL | wajib saat `rejected` |
| `submitted_at`, `reviewed_at` | TIMESTAMPTZ | |

Banyak baris per milestone. Revisi adalah baris baru, bukan penimpaan
([BR-46](07-business-rules.md)).

## `scoring_results`

Append-only. Satu baris per percobaan scoring ([BR-76](07-business-rules.md)).

| Kolom | Tipe | Catatan |
| --- | --- | --- |
| `id` | UUID PK | |
| `proposal_id` | UUID FK -> `proposals.id` | |
| `engine_name` | TEXT | `gemini` atau `mock` |
| `model_name` | TEXT | misal `gemini-2.5-flash` |
| `fit_score` | SMALLINT | `CHECK BETWEEN 0 AND 40` |
| `data_quality_score` | SMALLINT | `CHECK BETWEEN 0 AND 30` |
| `impact_score` | SMALLINT | `CHECK BETWEEN 0 AND 30` |
| `total_score` | SMALLINT | dihitung di Python, disimpan untuk pengurutan |
| `red_flags` | JSONB | daftar `{code, severity, evidence}` |
| `brief` | JSONB | `{strengths[], risks[], recommendation}` |
| `threshold_used` | SMALLINT | ambang yang berlaku saat itu |
| `verdict` | ENUM | `listed`, `rejected` |
| `latency_ms` | INTEGER | |
| `created_at` | TIMESTAMPTZ | |

Index: `(proposal_id, created_at DESC)`. Skor yang dipakai di UI adalah baris terbaru.

## `pledges`

| Kolom | Tipe | Catatan |
| --- | --- | --- |
| `id` | UUID PK | |
| `proposal_id` | UUID FK -> `proposals.id` | |
| `investor_id` | UUID FK -> `users.id` | |
| `amount` | BIGINT | `CHECK > 0` |
| `status` | ENUM | `active`, `cancelled` |
| `created_at` | TIMESTAMPTZ | dipakai sebagai pemutus seri lead investor |

Index: `(proposal_id, status)`.

## `ledger_entries`

Append-only ([BR-51](07-business-rules.md)). Tidak ada kolom `balance` di mana pun di skema ini.

| Kolom | Tipe | Catatan |
| --- | --- | --- |
| `id` | UUID PK | |
| `proposal_id` | UUID FK -> `proposals.id` | |
| `entry_type` | ENUM | `pledge_in`, `refund_out`, `disbursement_out` |
| `amount` | BIGINT | `CHECK > 0`, selalu positif; arah ada di `entry_type` |
| `ref_type`, `ref_id` | TEXT, UUID | asal kejadian: pledge atau milestone |
| `actor_id` | UUID FK -> `users.id` NULL | |
| `idempotency_key` | TEXT | `UNIQUE` |
| `created_at` | TIMESTAMPTZ | |

Pola `idempotency_key`: `pledge:{pledge_id}`, `refund:{pledge_id}`, `disburse:{milestone_id}`.
Unique constraint inilah yang membuat [BR-48](07-business-rules.md) ditegakkan oleh database,
bukan oleh harapan.

Index: `(proposal_id, created_at)`.

## `votes`

| Kolom | Tipe | Catatan |
| --- | --- | --- |
| `id` | UUID PK | |
| `proposal_id` | UUID FK -> `proposals.id` | |
| `user_id` | UUID FK -> `users.id` | |
| `created_at` | TIMESTAMPTZ | |

`UNIQUE (proposal_id, user_id)` ([BR-32](07-business-rules.md)). Membatalkan vote menghapus baris.

## `comments`

| Kolom | Tipe | Catatan |
| --- | --- | --- |
| `id` | UUID PK | |
| `proposal_id` | UUID FK -> `proposals.id` | |
| `user_id` | UUID FK -> `users.id` | |
| `body` | TEXT | `CHECK length(body) BETWEEN 1 AND 500` |
| `created_at`, `deleted_at` | TIMESTAMPTZ | |

## `system_clock`

Satu baris saja, untuk demo deadline yang deterministik ([D-06](../docs/decisions.md)).

| Kolom | Tipe | Catatan |
| --- | --- | --- |
| `id` | SMALLINT PK | `CHECK id = 1`, memaksa tabel ini punya satu baris |
| `virtual_now` | TIMESTAMPTZ NULL | NULL berarti memakai jam asli |

## Diagram relasi, ringkas

```
users ──< campaigns ──< proposals ──< proposal_milestones ──< milestone_reports
  │                        │  │
  │                        │  └──< scoring_results
  ├──< pledges >───────────┤
  ├──< votes >─────────────┤
  └──< comments >──────────┤
                           └──< ledger_entries
```
