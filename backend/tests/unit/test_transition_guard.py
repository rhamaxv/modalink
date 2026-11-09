"""Hanya app/services/status.py yang boleh memanggil apply_* dari luar domain.

Pagar ini ada karena hasil apply_* adalah enum domain, bukan enum kolom, dan
menulisnya langsung ke kolom gagal tanpa bersuara."""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
TRANSITIONS = {
    "apply_proposal",
    "apply_scoring",
    "apply_campaign",
    "apply_milestone",
    "apply_report",
}
ALLOWED = {"services/status.py"}


def _callers(tree: ast.AST) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in TRANSITIONS:
            names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute) and node.func.attr in TRANSITIONS:
            names.add(node.func.attr)
    return names


def test_apply_transitions_only_called_from_services_status():
    violations = {}
    for f in APP.rglob("*.py"):
        rel = f.relative_to(APP).as_posix()
        if rel.startswith("domain/") or rel in ALLOWED:
            continue
        used = _callers(ast.parse(f.read_text()))
        if used:
            violations[rel] = sorted(used)
    assert not violations, (
        "apply_* dipanggil di luar app/services/status.py: "
        f"{violations}. Pakai advance_* dari modul itu, karena hasil apply_* "
        "adalah enum domain dan kolom database memakai enum lain."
    )


def test_this_guard_actually_detects_a_violation():
    """Tanpa test ini, pagar di atas bisa hijau karena detektornya rusak."""
    synthetic = ast.parse("def f(p, e):\n    p.status = apply_proposal(p.status, e)\n")
    assert _callers(synthetic) == {"apply_proposal"}
