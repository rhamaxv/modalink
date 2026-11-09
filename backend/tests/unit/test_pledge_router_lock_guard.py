"""RF-1 lewat jalur HTTP: router pledge wajib memanggil get_locked_proposal,
bukan get_proposal() yang tidak terkunci (app/services/proposal.py).

test_proposal_lock_guard.py memagari services/, bukan api/: get_proposal
diimpor dan dipakai endpoint lain (rescore, scoring) secara sah, jadi
melarangnya di seluruh app/api/ akan salah sasaran. Pagar ini AST, hanya
atas app/api/v1/pledges.py, dan hanya atas dua fungsi route pledge --
investor sungguhan hanya pernah lewat sini, bukan lewat
tests/integration/test_pledge_concurrency.py yang memanggil service secara
langsung dan tidak pernah menyentuh router ini sama sekali.
"""

import ast
import pathlib

import pytest

PLEDGES_ROUTER = pathlib.Path(__file__).parents[2] / "app" / "api" / "v1" / "pledges.py"


def _route_functions(tree: ast.AST) -> dict[str, ast.AsyncFunctionDef]:
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name in {"create_pledge_endpoint", "cancel_pledge_endpoint"}
    }


def _calls_name(function_node: ast.AsyncFunctionDef, target_name: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == target_name
        for node in ast.walk(function_node)
    )


@pytest.mark.parametrize(
    "route_name", ["create_pledge_endpoint", "cancel_pledge_endpoint"]
)
def test_pledge_route_fetches_proposal_via_locked_fetch(route_name: str) -> None:
    tree = ast.parse(PLEDGES_ROUTER.read_text())
    routes = _route_functions(tree)
    assert route_name in routes, f"{route_name} tidak ditemukan di api/v1/pledges.py."

    function_node = routes[route_name]
    assert _calls_name(function_node, "get_locked_proposal"), (
        f"{route_name} tidak memanggil get_locked_proposal(): jalur HTTP yang "
        "sungguhan dilewati investor tidak terbukti memakai baris proposal "
        "yang terkunci (RF-1)."
    )
    assert not _calls_name(function_node, "get_proposal"), (
        f"{route_name} memanggil get_proposal(), yang tidak mengunci baris "
        "proposal (app/services/proposal.py). Dua request pledge bersamaan "
        "lewat endpoint ini akan sama-sama lolos pengecekan sisa dana yang sama."
    )


def test_guard_actually_catches_the_one_line_swap() -> None:
    """Pagar yang tidak pernah terbukti bisa merah mungkin tidak memagari
    apa pun: simulasikan tepat swap satu baris yang disebut review f06-b."""
    swapped = ast.parse(
        "async def create_pledge_endpoint(proposal_id, body, investor, session, clock):\n"
        "    proposal = await get_proposal(session, proposal_id)\n"
        "    return await create_pledge(session, investor, proposal, body.amount, clock)\n"
    )
    function_node = next(
        node for node in ast.walk(swapped) if isinstance(node, ast.AsyncFunctionDef)
    )
    assert _calls_name(function_node, "get_proposal")
    assert not _calls_name(function_node, "get_locked_proposal")
