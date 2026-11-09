"""Router hanya merangkai. Query dan orkestrasi milik services/."""

import ast
import pathlib

import pytest

API = pathlib.Path(__file__).parents[2] / "app" / "api"
BERKAS_ROUTER = sorted(API.glob("**/*.py"))

# Metode session yang berarti router sedang menyentuh database sendiri.
METODE_SESSION = {
    "scalar",
    "scalars",
    "execute",
    "exec",
    "add",
    "add_all",
    "get",
    "flush",
    "commit",
    "refresh",
    "delete",
    "merge",
}


def _pelanggaran(pohon: ast.AST) -> list[str]:
    temuan: list[str] = []
    for node in ast.walk(pohon):
        if not isinstance(node, ast.Call):
            continue
        fungsi = node.func
        # session.<apa pun yang menyentuh database>
        if (
            isinstance(fungsi, ast.Attribute)
            and isinstance(fungsi.value, ast.Name)
            and fungsi.value.id == "session"
            and fungsi.attr in METODE_SESSION
        ):
            temuan.append(f"baris {node.lineno}: session.{fungsi.attr}()")
        # select(...) dirakit di router, apa pun modelnya
        if isinstance(fungsi, ast.Name) and fungsi.id == "select":
            temuan.append(f"baris {node.lineno}: select()")
    return temuan


@pytest.mark.parametrize("berkas", BERKAS_ROUTER, ids=lambda p: p.name)
def test_router_does_not_touch_database_directly(berkas: pathlib.Path) -> None:
    temuan = _pelanggaran(ast.parse(berkas.read_text()))
    assert not temuan, (
        f"{berkas.name} menyentuh database langsung:\n  "
        + "\n  ".join(temuan)
        + "\nPindahkan ke services/. Router hanya merangkai."
    )


def test_this_guard_actually_catches_something() -> None:
    """Pagar yang tidak pernah terbukti bisa merah mungkin tidak memagari apa pun."""
    contoh = ast.parse(
        "async def r(session):\n    return await session.scalar(select(Campaign))\n"
    )
    assert len(_pelanggaran(contoh)) == 2
