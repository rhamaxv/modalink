"""Service yang menyentuh uang wajib memakai get_locked_proposal (RF-1), dan
setiap fungsi yang mengubah pledge wajib memanggil recompute_funding_status
di transaksi yang sama (R2b, D-05)."""

import ast
import pathlib

import pytest

BASIS = pathlib.Path(__file__).parents[2] / "app" / "services"

# "milestone.py" ikut terdaftar di sini supaya pagar ini otomatis mencakupnya
# begitu fase 07 membuatnya; difilter lewat exists() di bawah karena file itu
# belum ada sekarang, dan .read_text() pada file yang tidak ada akan meledak
# dengan alasan yang salah (FileNotFoundError, bukan pelanggaran pagar).
SERVICE_UANG = [
    n for n in ("pledge.py", "milestone.py", "ledger.py") if (BASIS / n).exists()
]


def _memanggil_session_get_proposal(pohon: ast.AST) -> bool:
    for node in ast.walk(pohon):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "session"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "Proposal"
        ):
            return True
    return False


@pytest.mark.parametrize("nama", SERVICE_UANG)
def test_money_service_does_not_fetch_proposal_via_session_get(nama: str) -> None:
    # AST, bukan regex atas teks mentah berkas: regex atas teks mentah bisa
    # false positive kena docstring yang justru menjelaskan pagar ini (lihat
    # docstring get_locked_proposal di pledge.py yang menyebut
    # "session.get(Proposal, ...)" sebagai contoh yang DILARANG).
    pohon = ast.parse((BASIS / nama).read_text())
    assert not _memanggil_session_get_proposal(pohon), (
        f"{nama} mengambil Proposal dengan session.get. "
        "Pakai get_locked_proposal() supaya barisnya terkunci (RF-1)."
    )


def _memanggil(fungsi: ast.FunctionDef, nama_target: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == nama_target
        for node in ast.walk(fungsi)
    )


@pytest.mark.parametrize("nama_fungsi", ["create_pledge", "cancel_pledge"])
def test_pledge_mutation_calls_recompute_funding_status(nama_fungsi: str) -> None:
    """R2b belum punya regression suite tersendiri (Task 6 fase ini). Sampai
    itu ada, inilah satu-satunya hal yang secara struktural mencegah
    create_pledge/cancel_pledge lupa memanggil recompute_funding_status
    dalam transaksi yang sama -- lupa memanggilnya berarti status funding
    melenceng dari jumlah pledge sebenarnya tanpa satu pun error muncul."""
    pohon = ast.parse((BASIS / "pledge.py").read_text())
    kandidat = [
        n
        for n in ast.walk(pohon)
        if isinstance(n, ast.AsyncFunctionDef) and n.name == nama_fungsi
    ]
    assert kandidat, f"Fungsi {nama_fungsi} tidak ditemukan di services/pledge.py."
    assert _memanggil(kandidat[0], "recompute_funding_status"), (
        f"{nama_fungsi} tidak memanggil recompute_funding_status (R2b): status "
        "funding bisa melenceng dari jumlah pledge sebenarnya."
    )


def test_pagar_ini_benar_benar_menangkap_sesuatu() -> None:
    """Pagar yang tidak pernah terbukti bisa merah mungkin tidak memagari apa pun."""
    contoh = ast.parse(
        "async def create_pledge(session, proposal):\n"
        "    proposal = await session.get(Proposal, proposal.id)\n"
    )
    assert _memanggil_session_get_proposal(contoh)

    # Docstring yang menyebut pola itu sebagai contoh terlarang, bukan
    # memanggilnya, tidak boleh ikut membuat pagar ini merah (false positive
    # yang justru menimpa guard ini sebelum ditulis AST, lihat riwayat diff).
    contoh_docstring_saja = ast.parse(
        '"""Jangan pakai session.get(Proposal, ...) di sini."""\n'
        "async def get_locked_proposal(session, proposal_id):\n"
        "    return await session.scalar(select(Proposal))\n"
    )
    assert not _memanggil_session_get_proposal(contoh_docstring_saja)

    contoh_tanpa_recompute = ast.parse(
        "async def cancel_pledge(session, proposal, pledge, clock):\n"
        "    pledge.status = PledgeStatus.CANCELLED\n"
    )
    fungsi = next(
        n
        for n in ast.walk(contoh_tanpa_recompute)
        if isinstance(n, ast.AsyncFunctionDef)
    )
    assert not _memanggil(fungsi, "recompute_funding_status")
