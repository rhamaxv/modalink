# Fase 02. Auth dan RBAC

**Hasil:** register, login, JWT berisi role, dan guard yang memeriksa **peran sekaligus
kepemilikan**. Regression test R5 berdiri beserta pemeriksa cakupan route.

Auth ditangani sendiri di FastAPI, bukan dioutsource ke penyedia managed ([D-14](../docs/decisions.md)):
role guard jadi dependency biasa yang bisa diuji langsung, tanpa stub tambahan.

**Spec terkait:** [07-business-rules BR-01..BR-05](../prd/07-business-rules.md), [10-api-contract](../prd/10-api-contract.md), [12-non-functional](../prd/12-non-functional.md)

## Struktur file

```
backend/app/
  models/__init__.py
  models/user.py
  schemas/auth.py
  services/auth.py        # hash, verifikasi, terbitkan token
  api/deps.py             # current_user, require_role, require_owner
  api/v1/auth.py
backend/tests/
  unit/test_auth_token.py
  integration/test_auth.py
  regression/test_r5_rbac.py
```

---

### Task 1: Model user dan migrasi

**Files:**
- Create: `backend/app/models/user.py`, `backend/alembic/versions/xxxx_users.py`
- Test: `backend/tests/integration/test_user_model.py`

**Interfaces:**
- Produces: `User` (SQLModel table), enum `Role` dengan nilai `investor`, `umkm`, `community`.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_user_model.py
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.user import Role, User

async def test_br02_email_unik_lintas_peran(db):
    db.add(User(email="a@x.id", password_hash="h", name="A", role=Role.INVESTOR))
    await db.flush()
    db.add(User(email="a@x.id", password_hash="h", name="B", role=Role.UMKM))
    with pytest.raises(IntegrityError):
        await db.flush()

async def test_email_disimpan_lowercase(db):
    u = User(email="Budi@Contoh.ID", password_hash="h", name="Budi", role=Role.UMKM)
    db.add(u)
    await db.flush()
    assert u.email == "budi@contoh.id"
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_user_model.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'app.models.user'`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/models/user.py
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4
from pydantic import field_validator
from sqlmodel import Field, SQLModel

class Role(StrEnum):
    INVESTOR = "investor"
    UMKM = "umkm"
    COMMUNITY = "community"

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    name: str
    role: Role
    created_at: datetime = Field(default_factory=lambda: __import__("app.domain.clock", fromlist=["SystemClock"]).SystemClock().now())

    @field_validator("email")
    @classmethod
    def lowercase(cls, v: str) -> str:
        return v.strip().lower()
```

Ganti impor dinamis di `created_at` dengan impor biasa `from app.domain.clock import SystemClock`
begitu tidak ada siklus impor; bentuk di atas hanya untuk menegaskan bahwa waktu tetap berasal
dari `clock.py` ([BR-60](../prd/07-business-rules.md)).

- [ ] **Step 4: Buat migrasi dan jalankan**

```bash
cd backend && alembic revision --autogenerate -m "users" && alembic upgrade head
```

- [ ] **Step 5: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_user_model.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models backend/alembic/versions
git commit -m "feat: add user model with unique lowercase email"
```

---

### Task 2: Hash password dan terbitkan token

**Files:**
- Create: `backend/app/services/auth.py`
- Test: `backend/tests/unit/test_auth_token.py`

**Interfaces:**
- Produces: `hash_password(raw) -> str`, `verify_password(raw, hashed) -> bool`,
  `issue_token(user_id, role) -> str`, `decode_token(token) -> TokenClaims`.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/unit/test_auth_token.py
import pytest
from app.services.auth import decode_token, hash_password, issue_token, verify_password
from uuid import uuid4

def test_br03_hash_tidak_pernah_sama_dengan_password_asli():
    h = hash_password("rahasia123")
    assert h != "rahasia123"
    assert h.startswith("$argon2")

def test_verify_password_benar_dan_salah():
    h = hash_password("rahasia123")
    assert verify_password("rahasia123", h) is True
    assert verify_password("rahasia124", h) is False

def test_token_membawa_sub_dan_role():
    uid = uuid4()
    claims = decode_token(issue_token(uid, "investor"))
    assert claims.sub == uid
    assert claims.role == "investor"

def test_token_kedaluwarsa_ditolak():
    uid = uuid4()
    kedaluwarsa = issue_token(uid, "investor", ttl_hours=-1)
    with pytest.raises(ValueError, match="kedaluwarsa"):
        decode_token(kedaluwarsa)

def test_token_dengan_tanda_tangan_lain_ditolak():
    import jwt
    palsu = jwt.encode({"sub": str(uuid4()), "role": "investor"}, "kunci-lain", algorithm="HS256")
    with pytest.raises(ValueError):
        decode_token(palsu)
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/unit/test_auth_token.py -v`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/services/auth.py
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.config import settings
from app.domain.clock import SystemClock

_hasher = PasswordHasher()
_clock = SystemClock()

@dataclass(frozen=True, slots=True)
class TokenClaims:
    sub: UUID
    role: str

def hash_password(raw: str) -> str:
    return _hasher.hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, raw)
    except VerifyMismatchError:
        return False

def issue_token(user_id: UUID, role: str, ttl_hours: int | None = None) -> str:
    ttl = settings.jwt_ttl_hours if ttl_hours is None else ttl_hours
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": _clock.now() + timedelta(hours=ttl),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

def decode_token(token: str) -> TokenClaims:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token kedaluwarsa.") from None
    except jwt.InvalidTokenError:
        raise ValueError("Token tidak sah.") from None
    return TokenClaims(sub=UUID(payload["sub"]), role=payload["role"])
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/unit/test_auth_token.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add argon2 hashing and role-bearing JWT"
```

---

### Task 3: Endpoint register, login, me

**Files:**
- Create: `backend/app/schemas/auth.py`, `backend/app/api/v1/auth.py`
- Test: `backend/tests/integration/test_auth.py`

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_auth.py
import pytest

async def test_register_lalu_login(client):
    daftar = await client.post("/api/v1/auth/register", json={
        "email": "investor@contoh.id", "password": "rahasia123",
        "name": "Sari", "role": "investor",
    })
    assert daftar.status_code == 201

    masuk = await client.post("/api/v1/auth/login", json={
        "email": "investor@contoh.id", "password": "rahasia123",
    })
    assert masuk.status_code == 200
    assert masuk.json()["token_type"] == "bearer"

async def test_br03_password_hash_tidak_pernah_dikembalikan(client):
    res = await client.post("/api/v1/auth/register", json={
        "email": "a@contoh.id", "password": "rahasia123", "name": "A", "role": "umkm",
    })
    assert "password_hash" not in res.text
    assert "rahasia123" not in res.text

async def test_login_salah_password_tidak_membocorkan_apakah_email_ada(client):
    await client.post("/api/v1/auth/register", json={
        "email": "a@contoh.id", "password": "rahasia123", "name": "A", "role": "umkm",
    })
    ada = await client.post("/api/v1/auth/login",
                            json={"email": "a@contoh.id", "password": "salah"})
    tidak_ada = await client.post("/api/v1/auth/login",
                                  json={"email": "z@contoh.id", "password": "salah"})
    assert ada.status_code == tidak_ada.status_code == 401
    assert ada.json() == tidak_ada.json()

async def test_br05_endpoint_me_butuh_token(client):
    assert (await client.get("/api/v1/auth/me")).status_code == 401
```

Test ketiga menutup kebocoran yang mudah terjadi: pesan "email tidak ditemukan" vs "password
salah" memberi tahu penyerang email mana yang terdaftar.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_auth.py -v`
Expected: FAIL dengan `404 Not Found` di semua test

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/api/v1/auth.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.db.session import get_session
from app.errors import DomainError
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from app.services.auth import hash_password, issue_token, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

class KredensialSalah(DomainError):
    status = 401

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
async def register(body: RegisterIn, session: AsyncSession = Depends(get_session)) -> User:
    sudah_ada = await session.scalar(select(User).where(User.email == body.email.lower()))
    if sudah_ada:
        raise DomainError("email_terpakai", "Email ini sudah terdaftar.")
    user = User(
        email=body.email, password_hash=hash_password(body.password),
        name=body.name, role=body.role,
    )
    session.add(user)
    await session.flush()
    return user

@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, session: AsyncSession = Depends(get_session)) -> TokenOut:
    user = await session.scalar(select(User).where(User.email == body.email.lower()))
    # Pesan yang sama untuk email tak dikenal maupun password salah, supaya tidak
    # membocorkan email mana yang terdaftar.
    if user is None or not verify_password(body.password, user.password_hash):
        raise KredensialSalah("kredensial_salah", "Email atau password salah.")
    return TokenOut(access_token=issue_token(user.id, user.role))
```

`UserOut` tidak memuat `password_hash`, dan itulah yang membuat test kedua lolos.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_auth.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add register, login and me endpoints"
```

---

### Task 4: Guard peran dan kepemilikan

**Files:**
- Create: `backend/app/api/deps.py`
- Test: `backend/tests/integration/test_deps.py`

**Interfaces:**
- Produces: `current_user(...) -> User`, `require_role(*roles) -> Callable`,
  `require_owner(get_owner_id) -> Callable`. Dipakai oleh **setiap** router di fase berikutnya.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_deps.py
async def test_br04_role_diverifikasi_ulang_ke_database(client, db, investor):
    """Token lama dengan role yang sudah berubah tidak boleh lolos."""
    from app.models.user import Role
    investor.user.role = Role.COMMUNITY
    await db.flush()

    res = await client.post("/api/v1/campaigns", headers=investor.headers, json={})
    assert res.status_code == 403

async def test_peran_salah_ditolak_403_bukan_401(client, umkm):
    res = await client.post("/api/v1/campaigns", headers=umkm.headers, json={})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "peran_tidak_berhak"

async def test_tanpa_token_ditolak_401(client):
    assert (await client.post("/api/v1/campaigns", json={})).status_code == 401
```

Test pertama adalah [BR-04](../prd/07-business-rules.md): role di dalam token tidak dipercaya
begitu saja.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_deps.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/api/deps.py
from collections.abc import Callable
from typing import Annotated
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.errors import DomainError, ForbiddenError
from app.models.user import Role, User
from app.services.auth import decode_token

class TidakTerautentikasi(DomainError):
    status = 401

async def current_user(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise TidakTerautentikasi("tidak_terautentikasi", "Token tidak ada.")
    try:
        claims = decode_token(authorization.removeprefix("Bearer "))
    except ValueError as exc:
        raise TidakTerautentikasi("token_tidak_sah", str(exc)) from None

    user = await session.get(User, claims.sub)
    if user is None:
        raise TidakTerautentikasi("token_tidak_sah", "Akun tidak ditemukan.")
    return user

def require_role(*roles: Role) -> Callable[[User], User]:
    def guard(user: User = Depends(current_user)) -> User:
        # Peran dibaca dari baris database, bukan dari klaim token (BR-04).
        if user.role not in roles:
            raise ForbiddenError("peran_tidak_berhak", "Peran Anda tidak berhak atas aksi ini.")
        return user
    return guard
```

`require_owner` ditambahkan di fase 03 saat ada sumber daya pertama yang punya pemilik.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_deps.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add role guard that revalidates against the database"
```

---

### Task 5: Regression R5, matriks RBAC dan pemeriksa cakupan

**Files:**
- Create: `backend/tests/regression/test_r5_rbac.py`

Bagian paling berharga dari task ini bukan matriksnya, melainkan test terakhir: yang memastikan
**tidak ada route yang terlewat dari matriks**.

- [ ] **Step 1: Tulis matriks dan pemeriksa cakupan**

```python
# backend/tests/regression/test_r5_rbac.py
"""R5: setiap endpoint kali setiap peran, plus kasus peran benar tapi bukan pemilik."""
import pytest

# (method, path, peran atau None, status yang diharapkan)
RBAC_MATRIX: list[tuple[str, str, str | None, int]] = [
    ("POST", "/api/v1/campaigns", "investor",  422),  # 422 karena body kosong, bukan 403
    ("POST", "/api/v1/campaigns", "umkm",      403),
    ("POST", "/api/v1/campaigns", "community", 403),
    ("POST", "/api/v1/campaigns", None,        401),
    ("GET",  "/api/v1/campaigns", None,        200),  # publik (BR-05)
    # Baris ditambahkan oleh setiap fase yang menambah endpoint.
]

@pytest.mark.parametrize("method,path,peran,harapan", RBAC_MATRIX)
async def test_r5_matriks_rbac(client, akun, method, path, peran, harapan):
    headers = akun[peran].headers if peran else {}
    res = await client.request(method, path, headers=headers, json={})
    assert res.status_code == harapan, (
        f"{method} {path} sebagai {peran or 'anonim'}: "
        f"dapat {res.status_code}, harusnya {harapan}"
    )

def test_r5_setiap_route_punya_baris_di_matriks(app):
    """Endpoint baru tanpa baris baru di matriks membuat test ini merah."""
    DIKECUALIKAN = {"/health", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    terdaftar = {
        (metode, route.path)
        for route in app.routes
        if getattr(route, "methods", None)
        for metode in route.methods
        if metode not in {"HEAD", "OPTIONS"} and route.path not in DIKECUALIKAN
    }
    di_matriks = {(m, p) for m, p, _, _ in RBAC_MATRIX}
    belum_diuji = terdaftar - di_matriks
    assert not belum_diuji, (
        "Endpoint berikut belum punya baris di RBAC_MATRIX:\n  "
        + "\n  ".join(f"{m} {p}" for m, p in sorted(belum_diuji))
    )
```

- [ ] **Step 2: Tulis fixture `akun`**

```python
# backend/tests/conftest.py (tambahan)
from dataclasses import dataclass
import pytest
from app.models.user import Role, User
from app.services.auth import hash_password, issue_token

@dataclass
class Akun:
    user: User
    headers: dict[str, str]

async def _buat_akun(db, email: str, role: Role) -> Akun:
    user = User(email=email, password_hash=hash_password("rahasia123"),
                name=email.split("@")[0], role=role)
    db.add(user)
    await db.flush()
    return Akun(user, {"Authorization": f"Bearer {issue_token(user.id, role)}"})

@pytest.fixture
async def investor(db):   return await _buat_akun(db, "investor@contoh.id", Role.INVESTOR)
@pytest.fixture
async def umkm(db):       return await _buat_akun(db, "umkm@contoh.id", Role.UMKM)
@pytest.fixture
async def community(db):  return await _buat_akun(db, "warga@contoh.id", Role.COMMUNITY)

@pytest.fixture
async def akun(investor, umkm, community):
    return {"investor": investor, "umkm": umkm, "community": community}
```

- [ ] **Step 3: Jalankan, pastikan hijau**

Run: `pytest tests/regression/test_r5_rbac.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/regression/test_r5_rbac.py backend/tests/conftest.py
git commit -m "feat: add RBAC matrix regression suite with route coverage check"
```

## Gerbang keluar fase 02

- [ ] `make test` hijau
- [ ] `make test-regression` hijau, R1 dan R5 keduanya
- [ ] Tidak ada respons yang memuat `password_hash` (diuji oleh grep di test)
- [ ] Pesan login salah identik untuk email tak dikenal maupun password salah
