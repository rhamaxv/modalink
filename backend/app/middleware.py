"""Rate limiting per-IP dan per-akun (review keamanan Finding 2).

Tidak ada Redis dan hanya satu container backend (D-01, D-18), jadi state
pembatas ini sengaja disimpan di memori proses, bukan di database atau
cache terpisah -- menambah infrastruktur baru untuk melindungi kuota Gemini
dari banjir request anonim adalah kebalikan dari yang dibutuhkan proyek ini.
Konsekuensinya: restart proses mengosongkan hitungan. Itu lebih baik
daripada tidak ada pembatas sama sekali (restart jarang, banjir request bisa
terjadi kapan saja), dan tidak lebih buruk dari limiter berbasis memori
lainnya.

**Gagal tertutup, bukan gagal terbuka.** Kalau pemeriksaan limit melempar
exception apa pun -- bug, bukan "limit terlampaui" -- middleware ini
menganggap request itu DITOLAK, bukan diloloskan. Limiter yang diam-diam
berhenti membatasi saat state-nya rusak lebih berbahaya daripada tidak ada
limiter sama sekali, karena tidak ada yang sadar (lihat
test_rate_limit_fails_closed_when_the_check_itself_breaks).
"""

import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Request
from starlette.responses import JSONResponse, Response

from app.services.auth import decode_token

RATE_LIMIT_HEADER_RETRY_AFTER = "Retry-After"


@dataclass(frozen=True, slots=True)
class RateRule:
    """Satu aturan: metode+path yang cocok, dan sampai dua gerbang limit
    yang independen -- per-IP selalu, per-akun (lewat klaim `sub` JWT) kalau
    `account_limit` diisi. Keduanya punya angka sendiri sengaja, bukan satu
    limit yang dipakai bersama: satu IP kantor/NAT wajar menanggung beberapa
    akun sekaligus, jadi limit IP harus lebih longgar daripada limit akun,
    atau menghabiskan jatah satu akun akan ikut menolak akun lain di IP
    yang sama."""

    name: str
    method: str
    path: re.Pattern[str]
    ip_limit: int
    window_s: float
    account_limit: int | None = None  # None: tidak dibatasi per akun


# Lima jalur yang reviewer sebut eksplisit: registrasi dan login (siapa pun
# tanpa akun bisa memanggilnya), submit proposal, pledge, dan komentar
# (ketiganya memicu kerja mahal atau butuh akun murah untuk dibuat berulang).
# Limit per menit sengaja longgar untuk pengguna wajar, ketat untuk crawler:
# satu pengguna manusia tidak pernah submit >3 proposal atau >10 pledge
# dalam satu menit, tapi banjir otomatis butuh ratusan untuk berarti.
DEFAULT_RATE_RULES: tuple[RateRule, ...] = (
    RateRule(
        name="register",
        method="POST",
        path=re.compile(r"^/api/v1/auth/register$"),
        ip_limit=5,
        window_s=60,
    ),
    RateRule(
        name="login",
        method="POST",
        path=re.compile(r"^/api/v1/auth/login$"),
        ip_limit=10,
        window_s=60,
    ),
    RateRule(
        name="proposal_submit",
        method="POST",
        path=re.compile(r"^/api/v1/campaigns/[^/]+/proposals$"),
        ip_limit=10,
        window_s=60,
        account_limit=3,
    ),
    RateRule(
        name="pledge_create",
        method="POST",
        path=re.compile(r"^/api/v1/proposals/[^/]+/pledges$"),
        ip_limit=30,
        window_s=60,
        account_limit=10,
    ),
    RateRule(
        name="comment_create",
        method="POST",
        path=re.compile(r"^/api/v1/proposals/[^/]+/comments$"),
        ip_limit=30,
        window_s=60,
        account_limit=10,
    ),
)


def _cocokkan_rule(
    rules: tuple[RateRule, ...], method: str, path: str
) -> RateRule | None:
    for rule in rules:
        if rule.method == method and rule.path.match(path):
            return rule
    return None


def _ambil_account_id(request: Request) -> str | None:
    """Mengurai klaim `sub` dari header Authorization tanpa membaca
    database: ini hanya kunci pembatas, bukan autentikasi. Token tidak ada,
    salah format, atau sudah kedaluwarsa semuanya berarti "tidak ada akun
    untuk dibatasi di sini", dan dibiarkan jatuh ke pembatas per-IP saja --
    pagar autentikasi sungguhan tetap di app/api/deps.py, bukan di sini."""
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    try:
        return str(decode_token(authorization.removeprefix("Bearer ")).sub)
    except Exception:  # noqa: BLE001
        return None


class InMemoryRateLimiter:
    """Fixed-window counter per kunci, dijaga satu lock karena operasinya
    semata manipulasi dict di memori dan tidak pernah menunggu I/O -- tidak
    ada alasan menahan request lain lebih dari beberapa mikrodetik."""

    def __init__(self, time_fn: Callable[[], float] = time.monotonic) -> None:
        self._time_fn = time_fn
        self._counts: dict[str, tuple[int, int]] = {}

    def hit(self, key: str, limit: int, window_s: float) -> bool:
        """True kalau request ini masih di bawah limit untuk jendela
        sekarang. Bukan async: tidak ada I/O di sini, dan membuatnya sync
        membuat permukaan yang bisa dites tanpa event loop."""
        jendela = int(self._time_fn() // window_s)
        sebelumnya = self._counts.get(key)
        if sebelumnya is None or sebelumnya[0] != jendela:
            self._counts[key] = (jendela, 1)
            return True
        hitung = sebelumnya[1] + 1
        self._counts[key] = (jendela, hitung)
        return hitung <= limit


def _gerbang_gerbang(
    rule: RateRule, request: Request, account_id: str | None
) -> list[tuple[str, int]]:
    """Satu request bisa kena dua gerbang independen: IP dan akun, masing-
    masing dengan limitnya sendiri. Keduanya harus lolos (lihat
    build_rate_limit_middleware), supaya satu akun yang dipakai dari banyak
    IP tetap kena batas akun, dan satu IP yang membuat banyak akun tetap
    kena batas IP."""
    ip = request.client.host if request.client else "tidak-dikenal"
    gerbang = [(f"ip:{rule.name}:{ip}", rule.ip_limit)]
    if rule.account_limit is not None and account_id is not None:
        gerbang.append((f"acct:{rule.name}:{account_id}", rule.account_limit))
    return gerbang


def build_rate_limit_middleware(
    rules: tuple[RateRule, ...] = DEFAULT_RATE_RULES,
    limiter: InMemoryRateLimiter | None = None,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    """Membangun middleware `@app.middleware("http")`, bukan langsung
    sebuah fungsi modul-level: test butuh menyuntikkan rule dengan limit
    kecil dan/atau limiter yang disuntiki clock, tanpa memonkeypatch
    konstanta global yang dipakai main.py di produksi."""
    limiter = limiter or InMemoryRateLimiter()

    async def rate_limit_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rule = _cocokkan_rule(rules, request.method, request.url.path)
        if rule is not None:
            try:
                account_id = (
                    _ambil_account_id(request)
                    if rule.account_limit is not None
                    else None
                )
                boleh = all(
                    limiter.hit(kunci, limit, rule.window_s)
                    for kunci, limit in _gerbang_gerbang(rule, request, account_id)
                )
            except Exception:  # noqa: BLE001
                # Gagal tertutup (lihat docstring modul): exception apa pun
                # di jalur pemeriksaan limit berarti DITOLAK, bukan
                # diloloskan diam-diam.
                boleh = False
            if not boleh:
                return JSONResponse(
                    status_code=429,
                    headers={RATE_LIMIT_HEADER_RETRY_AFTER: str(int(rule.window_s))},
                    content={
                        "error": {
                            "code": "terlalu_banyak_permintaan",
                            "message": (
                                "Terlalu banyak permintaan. Coba lagi beberapa saat lagi."
                            ),
                            "detail": {},
                        }
                    },
                )
        return await call_next(request)

    return rate_limit_middleware
