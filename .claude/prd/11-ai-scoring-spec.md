# 11. Spesifikasi AI Scoring

Provider: **Google Gemini**, model `gemini-2.5-flash`, dipanggil lewat **Instructor** untuk
mendapat output terstruktur yang divalidasi Pydantic.

Seluruhnya berada di belakang protocol `ScoringEngine`, dengan `MockScoringEngine` deterministik
untuk semua test ([D-07](../docs/decisions.md)).

---

## Schema output

```python
class RedFlag(BaseModel):
    code: str
    severity: Literal["info", "warning", "critical"]
    message: str
    evidence: str        # kutipan dari isi proposal, bukan parafrase

class Brief(BaseModel):
    strengths: list[str] = Field(min_length=1, max_length=5)
    risks: list[str] = Field(min_length=1, max_length=5)
    recommendation: str

class ProposalScore(BaseModel):
    fit_score: int = Field(ge=0, le=40)
    data_quality_score: int = Field(ge=0, le=30)
    impact_score: int = Field(ge=0, le=30)
    red_flags: list[RedFlag] = Field(max_length=8)
    brief: Brief
```

Tidak ada field `total` di schema ini, dan itu disengaja. Total dihitung di Python
([BR-70](07-business-rules.md)). Kalau model mengembalikannya, Pydantic akan mengabaikannya.

Batas rentang pada tiap komponen bukan dekorasi: kalau model mengembalikan `fit_score: 95`,
Instructor akan mengulang pemanggilan dengan pesan validasi, dan kalau tetap gagal,
[BR-74](07-business-rules.md) berlaku.

## Rubrik

### Kecocokan kriteria (0 sampai 40)

Seberapa cocok proposal dengan kriteria campaign.

| Rentang | Arti |
| --- | --- |
| 32 sampai 40 | Sektor tepat, dana diminta masuk akal terhadap target campaign, kebutuhan sesuai fokus campaign |
| 20 sampai 31 | Sektor berdekatan, atau dana diminta jauh dari kisaran wajar campaign |
| 0 sampai 19 | Sektor tidak relevan, atau proposal jelas salah alamat |

### Kualitas data (0 sampai 30)

Seberapa lengkap dan konsisten isian proposal. Ini menilai **isian**, bukan usahanya.

| Rentang | Arti |
| --- | --- |
| 24 sampai 30 | Semua field terisi spesifik, angka saling konsisten, rencana penggunaan dana terinci |
| 15 sampai 23 | Terisi tapi umum, atau ada angka yang tidak saling mendukung |
| 0 sampai 14 | Terasa template, banyak kalimat tanpa isi, atau angka saling bertentangan |

### Potensi dampak (0 sampai 30)

Seberapa besar dampak yang masuk akal dari dana yang diminta.

| Rentang | Arti |
| --- | --- |
| 24 sampai 30 | Dampak jelas, terukur, dan sebanding dengan skala usaha |
| 15 sampai 23 | Dampak masuk akal tapi tidak terukur |
| 0 sampai 14 | Dampak tidak dijelaskan, atau klaimnya jauh melebihi skala usaha |

## Red flag

Kode red flag tetap, supaya bisa diuji dan dirujuk:

| Kode | Level | Dipicu oleh |
| --- | --- | --- |
| `projeksi_tidak_realistis` | `critical` | Proyeksi pendapatan melonjak jauh di luar skala usaha yang dijelaskan |
| `angka_tidak_konsisten` | `critical` | Angka di proyeksi bertentangan dengan angka di profil atau rencana dana |
| `isian_template` | `warning` | Isian terasa generik, tidak menyebut hal spesifik tentang usaha ini |
| `rencana_dana_kabur` | `warning` | Rencana penggunaan dana tidak merinci porsi per pos |
| `sektor_tidak_cocok` | `warning` | Jenis usaha tidak sesuai sektor campaign |
| `profil_tipis` | `info` | Profil usaha memenuhi panjang minimum tapi sedikit isinya |

`evidence` wajib berupa kutipan dari isi proposal. Red flag tanpa kutipan tidak bisa
dipertanggungjawabkan ke UMKM yang proposalnya ditolak ([US-U3](02-personas-user-stories.md)).

## Verdict

Diputuskan **oleh kode**, bukan oleh model ([BR-71](07-business-rules.md)):

```python
total = fit_score + data_quality_score + impact_score

if any(f.severity == "critical" for f in red_flags):
    verdict = "rejected"
elif total < campaign.score_threshold:
    verdict = "rejected"
else:
    verdict = "listed"
```

Urutannya penting: red flag kritis menolak tanpa memandang total
([BR-72](07-business-rules.md)).

## Prompt

Disimpan sebagai file di `backend/app/ai/prompts/score_proposal.md`, bukan sebagai string di
dalam kode Python. Alasannya: prompt adalah konten yang sering direvisi, dan diff-nya harus bisa
dibaca tanpa menembus kode.

Isinya memuat:

1. Peran dan batasan: menilai, bukan memutuskan; menolak mengarang angka yang tidak ada di proposal.
2. Kriteria campaign: sektor, dana target, deskripsi.
3. Isi proposal, lengkap dengan nama field, supaya kutipan `evidence` bisa dirujuk ke field asalnya.
4. Rubrik di atas, apa adanya.
5. Instruksi bahwa `evidence` harus kutipan persis, bukan parafrase.

Prompt **tidak** memuat `score_threshold`. Model tidak perlu tahu ambangnya, supaya penilaiannya
tidak condong menyesuaikan ambang.

## Mode kegagalan

| Yang terjadi | Hasilnya |
| --- | --- |
| Timeout atau error jaringan | `scoring_status = failed`, proposal tetap `submitted` |
| Output tidak lolos validasi setelah retry Instructor | sama seperti di atas |
| API key tidak ada | sama seperti di atas, plus log peringatan saat startup |
| Job terpicu dua kali | Transisi kedua tidak ditulis karena compare-and-set ([BR-75](07-business-rules.md)) |

Tidak ada mode kegagalan yang menghasilkan `rejected`. Itu diuji oleh regression test **R6**.

## MockScoringEngine

Deterministik, tanpa jaringan, dipakai oleh seluruh unit dan integration test.

Aturannya sederhana dan sengaja dibuat bisa diprediksi dari isi proposal:

- Skor dasar dihitung dari panjang dan kelengkapan field.
- Teks yang memuat penanda `[[RED_FLAG:critical]]` menghasilkan red flag kritis.
- Teks yang memuat penanda `[[SCORE:n]]` memaksa total menjadi `n`, untuk menguji perbatasan
  threshold dengan tepat.

Penanda itu hanya dikenali oleh mock, tidak pernah dikirim ke Gemini.

## Contract test

Satu file, `backend/tests/contract/test_gemini_scoring.py`, ditandai `@pytest.mark.live` dan
di-skip secara default. Dijalankan dengan `make test-live` saat ada perubahan pada prompt atau
schema.

Yang diuji:

1. Output lolos validasi `ProposalScore`.
2. Tiga proposal uji (bagus, biasa, red flag) menghasilkan urutan total skor yang benar.
3. Proposal dengan proyeksi berlebihan memicu red flag berlevel `critical`.
4. Setiap `evidence` benar-benar muncul sebagai substring di isi proposal.

Poin keempat adalah yang paling sering jebol saat prompt diubah, dan paling berguna.
