---
name: fastapi-domain-service
description: Cara menambah atau mengubah endpoint backend Logicodix dari ujung ke ujung. Gunakan saat membuat route baru, mengubah service, atau memindahkan logika yang terlanjur ditulis di router. Memuat urutan pengerjaan, pembagian lapisan, pola dependency, dan daftar periksa sebelum endpoint dianggap jadi.
---

# Menambah endpoint di Logicodix

## Urutan pengerjaan, dari dalam ke luar

Selalu dari lapisan terdalam. Menulis router lebih dulu hampir selalu berakhir dengan logika
bisnis yang terjebak di sana.

1. **`domain/`** jika ada aturan murni baru. Tulis testnya di `tests/unit/`, tanpa database.
2. **`models/`** jika ada tabel atau kolom baru, beserta migrasinya (lihat skill
   `sqlmodel-alembic-migrations`).
3. **`schemas/`** untuk bentuk request dan response.
4. **`services/`** untuk orkestrasi: baca database, panggil `domain/`, tulis hasilnya.
5. **`api/v1/`** untuk route: dependency, panggil service, kembalikan response.
6. **`tests/regression/test_r5_rbac.py`** tambahkan barisnya. R5 akan merah sampai itu dilakukan.

## Pola router

```python
@router.post("/proposals/{proposal_id}/pledges", status_code=201,
             response_model=PledgeOut)
async def buat_pledge_endpoint(
    proposal_id: UUID,
    body: PledgeIn,
    investor: User = Depends(require_role(Role.INVESTOR)),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> Pledge:
    proposal = await ambil_proposal_terkunci(session, proposal_id)
    return await buat_pledge(session, investor, proposal, body.amount, clock)
```

Router hanya merangkai. Tidak ada `if`, tidak ada perhitungan, tidak ada query. Kalau sebuah
router mulai punya percabangan, itu tanda logikanya salah tempat.

## Peran dan kepemilikan adalah dua pemeriksaan berbeda

`require_role(Role.INVESTOR)` memastikan **jenis** penggunanya. Itu tidak memastikan investor ini
berhak atas sumber daya ini.

```python
# Peran benar, kepemilikan salah. Ini yang paling sering lolos dari guard.
if campaign.investor_id != user.id:
    raise ForbiddenError("bukan_pemilik", "Campaign ini bukan milik Anda.")
```

Untuk sumber daya yang keberadaannya pun tidak boleh diketahui, lempar `NotFoundError`.

Setiap endpoint butuh **dua** baris di matriks RBAC: satu untuk peran yang salah, satu untuk peran
benar tapi bukan pemilik.

## Operasi yang menyentuh uang

Wajib memakai `ambil_proposal_terkunci()`, bukan `session.get(Proposal, ...)`. Fungsi itu memakai
`SELECT ... FOR UPDATE`, dan tanpanya dua request bersamaan sama-sama membaca sisa yang sama lalu
sama-sama lolos.

Ada test yang memindai `services/` untuk `session.get(Proposal` dan menolaknya.

Entri ledger dan perubahan status harus berada di **satu transaksi**. Tidak boleh ada keadaan di
mana milestone `disbursed` tapi entri ledger-nya gagal tertulis.

## Daftar periksa sebelum endpoint dianggap jadi

- [ ] Test ditulis lebih dulu dan pernah merah karena alasan yang benar
- [ ] Logika bisnis ada di `domain/` atau `services/`, bukan di router
- [ ] Peran **dan** kepemilikan diperiksa
- [ ] Error memakai subclass `DomainError`, bukan `HTTPException`
- [ ] Endpoint daftar punya urutan deterministik, seri diputus `created_at` lalu `id`
- [ ] Baris baru ditambahkan ke `RBAC_MATRIX`, dan `test_r5_setiap_route_punya_baris_di_matriks` hijau
- [ ] Kalau menyentuh uang: baris proposal terkunci, entri ledger punya `idempotency_key`
- [ ] Kalau menyentuh status: transisinya lewat `domain/transitions.py` (lihat skill `state-machine-guard`)
- [ ] `make test-regression` hijau
- [ ] Endpoint didokumentasikan di `.claude/prd/10-api-contract.md`

## Tanda logika salah tempat

| Yang terlihat | Artinya |
| --- | --- |
| Router punya lebih dari satu `if` | Logikanya milik service |
| Service menghitung sesuatu dari angka saja | Perhitungan itu milik `domain/` |
| Test butuh database untuk menguji sebuah aturan | Aturannya belum murni |
| Dua endpoint punya blok validasi yang mirip | Validasinya milik `domain/` |
