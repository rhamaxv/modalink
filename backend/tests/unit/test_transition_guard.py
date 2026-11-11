"""Hanya app/services/status.py yang boleh memanggil apply_* dari luar domain,
atau menulis status lewat assignment langsung.

Pagar pertama ada karena hasil apply_* adalah enum domain, bukan enum kolom,
dan menulisnya langsung ke kolom gagal tanpa bersuara.

Pagar kedua (assignment langsung) ada karena pagar pertama ternyata buta
terhadap bentuk yang justru menyebabkan double-spend (review Finding 1b):
`proposal.status = ProposalStatus(baru.value)` di services/pledge.py tidak
memanggil apply_proposal sama sekali -- ia menulis hasil compute_funding_status
langsung ke kolom, sehingga PROPOSAL_MAP dan aturan status terminalnya tidak
pernah dibaca. test_r1_transitions.py yang menguji "status terminal tidak
punya jalan keluar" tetap hijau karena ia menguji PROPOSAL_MAP, bukan baris
ini -- invariannya diuji di satu-satunya tempat yang tidak bisa bocor,
dan tidak diuji di tempat yang sebenarnya bocor."""

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

# Atribut yang dikuasai salah satu dari empat mesin status terpusat
# (domain/transitions.py). "status" sengaja tidak mencakup Pledge: PledgeStatus
# cuma dua nilai tanpa matriks transisi (lihat docstring cancel_pledge di
# services/pledge.py), jadi assignment literal ke anggota PledgeStatus
# dikecualikan secara eksplisit di bawah, bukan lewat nama variabel yang
# mudah luput kalau pemanggilnya diganti nama.
GOVERNED_STATUS_ATTRS = {"status", "scoring_status", "review_status"}
# Enum status yang TIDAK punya matriks transisi, jadi assignment literal ke
# anggotanya memang bukan pelanggaran. Dua-duanya sekelas: PledgeStatus cuma
# active/cancelled (lihat docstring cancel_pledge di services/pledge.py), dan
# KycStatus cuma verified/rejected yang ditentukan sekali dari hasil
# pemeriksaan bentuk, tanpa perpindahan antar keadaan (services/kyc.py).
# Dikecualikan lewat nama enumnya, bukan lewat nama berkas: berkas yang
# dikecualikan akan ikut melewatkan status yang SUNGGUH dikuasai mesin
# transisi kalau suatu saat ditulis di sana.
EXEMPT_ENUM_CLASSES = {"PledgeStatus", "KycStatus"}


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


def _is_exempt_pledge_assignment(value: ast.AST) -> bool:
    return (
        isinstance(value, ast.Attribute)
        and isinstance(value.value, ast.Name)
        and value.value.id in EXEMPT_ENUM_CLASSES
    )


def _direct_status_assignments(tree: ast.AST) -> set[str]:
    """Nama atribut yang ditulis lewat `x.atribut = ...` langsung, bukan
    lewat advance_*. Menangkap persis bentuk yang dipakai Finding 1b:
    `proposal.status = ProposalStatus(baru.value)`."""
    hits = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and target.attr in GOVERNED_STATUS_ATTRS
                and not _is_exempt_pledge_assignment(node.value)
            ):
                hits.add(target.attr)
    return hits


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


def test_no_direct_status_assignment_outside_services_status():
    violations = {}
    for f in APP.rglob("*.py"):
        rel = f.relative_to(APP).as_posix()
        if rel.startswith("domain/") or rel in ALLOWED:
            continue
        hits = _direct_status_assignments(ast.parse(f.read_text()))
        if hits:
            violations[rel] = sorted(hits)
    assert not violations, (
        "Status ditulis lewat assignment langsung di luar app/services/status.py: "
        f"{violations}. Pakai advance_proposal/advance_milestone/advance_campaign/"
        "advance_report dari modul itu, supaya PROPOSAL_MAP (termasuk aturan status "
        "terminal) selalu dibaca sebelum status ditulis (BR-25, Finding 1b)."
    )


def test_this_guard_actually_detects_a_violation():
    """Tanpa test ini, pagar di atas bisa hijau karena detektornya rusak."""
    synthetic = ast.parse("def f(p, e):\n    p.status = apply_proposal(p.status, e)\n")
    assert _callers(synthetic) == {"apply_proposal"}


def test_this_guard_also_detects_direct_status_assignment():
    """Pagar kedua harus terbukti merah terhadap persis bentuk yang
    menyebabkan Finding 1b, dan terbukti tidak false-positive terhadap
    pengecualian Pledge yang sudah didokumentasikan."""
    synthetic = ast.parse(
        "def recompute(proposal, baru):\n"
        "    proposal.status = ProposalStatus(baru.value)\n"
    )
    assert _direct_status_assignments(synthetic) == {"status"}

    pledge_exception = ast.parse(
        "def cancel_pledge(pledge):\n    pledge.status = PledgeStatus.CANCELLED\n"
    )
    assert _direct_status_assignments(pledge_exception) == set()
