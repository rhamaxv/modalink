# Router internal memagari endpoint yang memajukan jam global tanpa autentikasi.
# Default ENV karena itu harus tertutup: deployment yang lupa menyetelnya tidak
# boleh membuka pemaju jam ke internet.
from app.config import Settings
from app.main import create_app


def _paths(app) -> set[str]:
    hasil = set()
    sisa = list(app.routes)
    while sisa:
        route = sisa.pop()
        sisa.extend(getattr(getattr(route, "original_router", None), "routes", []))
        path = getattr(route, "path", None)
        if path:
            hasil.add(path)
    return hasil


def test_default_env_menutup_router_internal(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    s = Settings(
        _env_file=None, database_url="postgresql+asyncpg://x/y", jwt_secret="x"
    )
    assert s.env == "prod", (
        "default ENV permisif: deployment yang lupa menyetelnya membuka "
        "/internal/clock/tick tanpa autentikasi"
    )


def test_internal_tidak_terdaftar_di_prod(monkeypatch):
    monkeypatch.setattr("app.main.settings.env", "prod")
    paths = _paths(create_app())
    assert not [p for p in paths if "/internal/" in p]


def test_internal_terdaftar_di_dev(monkeypatch):
    # Sisi sebaliknya diuji juga: pagar yang selalu menutup tidak membuktikan
    # bahwa ENV-lah yang memagarinya.
    monkeypatch.setattr("app.main.settings.env", "dev")
    paths = _paths(create_app())
    assert [p for p in paths if "/internal/" in p]


def test_variabel_kosong_tidak_menimpa_default():
    """Variabel environment yang tidak diset tapi tetap diteruskan tiba sebagai
    string kosong. Tanpa penolakan ini, `GEMINI_MODEL: ${GEMINI_MODEL}` di
    compose membuat scoring memanggil model bernama "" dan setiap proposal
    menggantung di scoring_status=failed sementara container sehat."""
    import pytest

    from app.config import Settings

    for medan in ("gemini_model", "scoring_engine"):
        with pytest.raises(ValueError):
            Settings(
                _env_file=None,
                database_url="postgresql+asyncpg://x/y",
                jwt_secret="x" * 32,
                **{medan: ""},
            )
