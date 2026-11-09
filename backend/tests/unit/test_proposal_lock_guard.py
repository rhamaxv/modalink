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
MONEY_SERVICES = [
    name
    for name in ("pledge.py", "milestone.py", "ledger.py")
    if (BASIS / name).exists()
]


def _calls_session_get_proposal(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
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


def _is_select_proposal_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "select"
        and bool(node.args)
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "Proposal"
    )


def _is_with_for_update_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "with_for_update"
    )


def _selects_proposal_without_lock(tree: ast.AST) -> bool:
    """True kalau ada `select(Proposal)` yang tidak diikuti `.with_for_update()`
    di manapun pada rantai pemanggilan yang sama.

    Pagar lama (`_calls_session_get_proposal`) hanya menangkap bentuk
    `session.get(Proposal, ...)`. Itu menyisakan jalan masuk yang sama
    sekali tidak terlihat: `session.scalar(select(Proposal).where(...))`
    tanpa `.with_for_update()` membaca baris proposal yang sama-sama tidak
    terkunci, cuma lewat API yang berbeda. Review f06-b membuktikan pagar
    lama lolos terhadap bentuk ini (RF-1, RF-4, RF-5).
    """
    # Setiap select(Proposal) yang muncul di dalam subtree sebuah panggilan
    # .with_for_update() dianggap terkunci: method chaining membuat
    # with_for_update() selalu jadi node paling luar dari rantainya, jadi
    # select(Proposal) yang menjadi pasangannya pasti ikut tercakup saat
    # subtree panggilan luar itu di-walk.
    guarded_ids = {
        id(inner)
        for node in ast.walk(tree)
        if _is_with_for_update_call(node)
        for inner in ast.walk(node)
        if _is_select_proposal_call(inner)
    }
    return any(
        _is_select_proposal_call(node) and id(node) not in guarded_ids
        for node in ast.walk(tree)
    )


@pytest.mark.parametrize("file_name", MONEY_SERVICES)
def test_money_service_does_not_fetch_proposal_via_session_get(file_name: str) -> None:
    # AST, bukan regex atas teks mentah berkas: regex atas teks mentah bisa
    # false positive kena docstring yang justru menjelaskan pagar ini (lihat
    # docstring get_locked_proposal di pledge.py yang menyebut
    # "session.get(Proposal, ...)" sebagai contoh yang dilarang).
    tree = ast.parse((BASIS / file_name).read_text())
    assert not _calls_session_get_proposal(tree), (
        f"{file_name} mengambil Proposal dengan session.get. "
        "Pakai get_locked_proposal() supaya barisnya terkunci (RF-1)."
    )


@pytest.mark.parametrize("file_name", MONEY_SERVICES)
def test_money_service_selects_proposal_only_with_lock(file_name: str) -> None:
    # Pelanggaran yang sebenarnya kehilangan uang: select(Proposal) tanpa
    # with_for_update() lolos dari pagar session.get di atas sepenuhnya,
    # karena bentuknya memang berbeda, bukan karena lebih tersembunyi.
    tree = ast.parse((BASIS / file_name).read_text())
    assert not _selects_proposal_without_lock(tree), (
        f"{file_name} mengambil Proposal lewat select() tanpa .with_for_update(). "
        "Pakai get_locked_proposal() supaya barisnya terkunci (RF-1, RF-4, RF-5)."
    )


def _calls(function_node: ast.FunctionDef, target_name: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == target_name
        for node in ast.walk(function_node)
    )


@pytest.mark.parametrize("function_name", ["create_pledge", "cancel_pledge"])
def test_pledge_mutation_calls_recompute_funding_status(function_name: str) -> None:
    """R2b belum punya regression suite tersendiri (Task 6 fase ini). Sampai
    itu ada, inilah satu-satunya hal yang secara struktural mencegah
    create_pledge/cancel_pledge lupa memanggil recompute_funding_status
    dalam transaksi yang sama -- lupa memanggilnya berarti status funding
    melenceng dari jumlah pledge sebenarnya tanpa satu pun error muncul."""
    tree = ast.parse((BASIS / "pledge.py").read_text())
    candidates = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name
    ]
    assert candidates, f"Fungsi {function_name} tidak ditemukan di services/pledge.py."
    assert _calls(candidates[0], "recompute_funding_status"), (
        f"{function_name} tidak memanggil recompute_funding_status (R2b): status "
        "funding bisa melenceng dari jumlah pledge sebenarnya."
    )


def test_guard_actually_catches_something() -> None:
    """Pagar yang tidak pernah terbukti bisa merah mungkin tidak memagari apa pun."""
    example = ast.parse(
        "async def create_pledge(session, proposal):\n"
        "    proposal = await session.get(Proposal, proposal.id)\n"
    )
    assert _calls_session_get_proposal(example)

    # Docstring yang menyebut pola itu sebagai contoh terlarang, bukan
    # memanggilnya, tidak boleh ikut membuat pagar ini merah (false positive
    # yang justru menimpa guard ini sebelum ditulis AST, lihat riwayat diff).
    example_docstring_only = ast.parse(
        '"""Jangan pakai session.get(Proposal, ...) di sini."""\n'
        "async def get_locked_proposal(session, proposal_id):\n"
        "    return await session.scalar(select(Proposal))\n"
    )
    assert not _calls_session_get_proposal(example_docstring_only)

    example_without_recompute = ast.parse(
        "async def cancel_pledge(session, proposal, pledge, clock):\n"
        "    pledge.status = PledgeStatus.CANCELLED\n"
    )
    function_node = next(
        node
        for node in ast.walk(example_without_recompute)
        if isinstance(node, ast.AsyncFunctionDef)
    )
    assert not _calls(function_node, "recompute_funding_status")

    # select(Proposal) dengan .with_for_update() tetap terkunci: harus tidak
    # memicu pagar baru, persis seperti bentuk sungguhan di get_locked_proposal.
    example_locked_select = ast.parse(
        "async def get_locked_proposal(session, proposal_id):\n"
        "    return await session.scalar(\n"
        "        select(Proposal).where(Proposal.id == proposal_id).with_for_update()\n"
        "    )\n"
    )
    assert not _selects_proposal_without_lock(example_locked_select)

    # Mutasi yang betul-betul kehilangan uang menurut review f06-b: tidak ada
    # session.get(Proposal, ...) sama sekali, tapi .with_for_update() dibuang
    # dari select(Proposal) yang sama.
    example_unlocked_select = ast.parse(
        "async def get_locked_proposal(session, proposal_id):\n"
        "    return await session.scalar(select(Proposal).where(Proposal.id == proposal_id))\n"
    )
    assert not _calls_session_get_proposal(example_unlocked_select)
    assert _selects_proposal_without_lock(example_unlocked_select)
