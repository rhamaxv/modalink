"""Setiap endpoint di 10-api-contract.md harus benar-benar terdaftar di aplikasi.

Pagar ini ada karena empat endpoint baca (10-api-contract.md baris 57, 67,
73, 96) sempat hilang dari seluruh plan: kontrak menyebutnya, tidak ada task
yang membangunnya, dan tidak ada test yang menyadarinya sampai audit manual
menemukannya. Audit yang sama menemukan kontrak mendeklarasikan 30 endpoint
sementara kode hanya punya 17 -- selisih yang seharusnya pagar ini tangkap
sendiri, bukan tangan manusia yang membaca dua dokumen berdampingan.

`app.routes` TIDAK memperlihatkan route sub-router kalau dibaca secara naif:
FastAPI membungkus setiap `include_router()` jadi objek pembungkus tanpa
`.methods`/`.path` sendiri. Pagar sejenis di tests/regression/test_r5_rbac.py
pernah hijau palsu di fase ini karena persis kesalahan itu (matriks 6 baris
dari 21 route sungguhan), sampai `_semua_route` di sana ditambahkan untuk
menelusuri `original_router` secara rekursif. Helper `_terdaftar` di bawah
memakai pola yang sama, bukan `app.routes` secara langsung.
"""

import re
from pathlib import Path
from typing import Any

from app.main import app

KONTRAK = Path(__file__).resolve().parents[3] / ".claude/prd/10-api-contract.md"
POLA = re.compile(r"`(GET|POST|PATCH|PUT|DELETE) (/[a-zA-Z0-9{}/_-]+)`")


def _samakan(path: str) -> str:
    # Nama parameter berbeda antara dokumen dan kode ({id} vs {proposal_id}),
    # dan yang dibandingkan adalah bentuk route-nya, bukan ejaan parameternya.
    return re.sub(r"\{[a-zA-Z_]+\}", "{}", path.replace("/api/v1", ""))


def _semua_route(routes: list[Any]) -> list[Any]:
    """Turun ke `original_router` setiap sub-router yang disertakan lewat
    `include_router`, sama seperti helper di tests/regression/test_r5_rbac.py.
    Tanpa ini, pagar di bawah memeriksa kumpulan route yang nyaris selalu
    kosong dan tidak pernah bisa merah, apa pun yang hilang dari aplikasi."""
    hasil: list[Any] = []
    for route in routes:
        if getattr(route, "methods", None):
            hasil.append(route)
        sub_router = getattr(route, "original_router", None)
        if sub_router is not None:
            hasil.extend(_semua_route(getattr(sub_router, "routes", [])))
    return hasil


def _terdaftar() -> set[str]:
    hasil = set()
    for route in _semua_route(app.routes):
        for method in route.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            hasil.add(f"{method} {_samakan(route.path)}")
    return hasil


def test_setiap_endpoint_kontrak_terdaftar_di_aplikasi():
    terdaftar = _terdaftar()
    diminta = {
        f"{m} {_samakan(p)}": f"{m} {p}" for m, p in POLA.findall(KONTRAK.read_text())
    }
    hilang = sorted(asli for kunci, asli in diminta.items() if kunci not in terdaftar)
    assert not hilang, (
        "endpoint ini ada di 10-api-contract.md tapi tidak terdaftar di aplikasi: "
        f"{hilang}"
    )


def test_pagar_ini_benar_benar_membandingkan_sesuatu():
    # Tanpa test ini, pagar di atas bisa hijau karena kedua himpunannya
    # kosong (misalnya _semua_route rusak lagi suatu hari) atau karena regex
    # berhenti cocok setelah 10-api-contract.md diformat ulang.
    diminta = POLA.findall(KONTRAK.read_text())
    assert len(diminta) >= 25, (
        f"hanya {len(diminta)} endpoint terbaca dari kontrak; polanya berhenti cocok"
    )
    assert len(_terdaftar()) >= 20, (
        f"hanya {len(_terdaftar())} route terbaca dari aplikasi; "
        "_semua_route mungkin tidak menelusuri sub-router dengan benar"
    )
