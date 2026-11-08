"""Pagar arsitektur: domain/ tidak boleh tahu soal database, HTTP, atau jam sistem."""
import ast
import pathlib

import pytest

APP = pathlib.Path(__file__).parents[2] / "app"
DOMAIN = APP / "domain"
TERLARANG = {"sqlmodel", "sqlalchemy", "fastapi", "httpx", "asyncpg"}
FILE_DOMAIN = sorted(DOMAIN.glob("*.py"))

# services/ dan api/ belum lahir di fase ini untuk sebagian cabang; glob kosong
# berarti parametrize kosong, bukan error, sehingga pagar tetap aktif begitu
# fase berikutnya menambah berkas di sana.
FILE_SERVICES = sorted(APP.glob("services/**/*.py"))
FILE_API = sorted(APP.glob("api/**/*.py"))

@pytest.mark.parametrize("berkas", FILE_DOMAIN, ids=lambda p: p.name)
def test_domain_tidak_mengimpor_database_atau_http(berkas):
    pohon = ast.parse(berkas.read_text())
    diimpor = {
        (node.module or "").split(".")[0]
        for node in ast.walk(pohon)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(pohon)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    bocor = diimpor & TERLARANG
    assert not bocor, f"{berkas.name} mengimpor {bocor}; pindahkan logikanya ke services/"

@pytest.mark.parametrize("berkas", FILE_DOMAIN, ids=lambda p: p.name)
def test_br60_hanya_clock_yang_boleh_memanggil_datetime_now(berkas):
    if berkas.name == "clock.py":
        pytest.skip("clock.py adalah satu-satunya yang berhak")
    assert "datetime.now(" not in berkas.read_text(), (
        f"{berkas.name} memanggil datetime.now() langsung. Pakai Clock (BR-60)."
    )

@pytest.mark.parametrize("berkas", FILE_SERVICES, ids=lambda p: p.name)
def test_br60_services_tidak_memanggil_datetime_now(berkas):
    assert "datetime.now(" not in berkas.read_text(), (
        f"{berkas.name} memanggil datetime.now() langsung. Pakai Clock (BR-60)."
    )

@pytest.mark.parametrize("berkas", FILE_API, ids=lambda p: p.name)
def test_br60_api_tidak_memanggil_datetime_now(berkas):
    assert "datetime.now(" not in berkas.read_text(), (
        f"{berkas.name} memanggil datetime.now() langsung. Pakai Clock (BR-60)."
    )
