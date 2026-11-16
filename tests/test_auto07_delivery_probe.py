"""AUTO-07: offline checks of the fixed delivery probe.

The probe file is only read as bytes and parsed. It is never run, imported or evaluated here.
The content hash ties the file to the reviewed bytes; the AST check records the reviewed structure.
Neither check is a guarantee about what happens when the probe runs.
"""
import ast
import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "tools" / "auto07_delivery_probe.py"
PROBE_CONTENT_SHA256 = "c56693d156fa09a1cf9334574e4454b1bee33f4e3977ee17e46569d639181622"
EXPECTED_TEXT = "AUTO07_DELIVERY_PROBE_OK"
EXPECTED_EXIT = 7


def _probe_bytes() -> bytes:
    assert PROBE.is_file(), "probe file is missing: tools/auto07_delivery_probe.py"
    return PROBE.read_bytes()


def _is_constant(node: ast.expr, value: object, kind: type) -> bool:
    """A literal of exactly `kind` (so True is not accepted where the int 7 is expected)."""
    return isinstance(node, ast.Constant) and type(node.value) is kind and node.value == value


def test_probe_content_hash_matches_reviewed_bytes():
    content = _probe_bytes().replace(b"\r\n", b"\n")  # a CRLF checkout has the same content
    assert hashlib.sha256(content).hexdigest() == PROBE_CONTENT_SHA256


def test_probe_ast_is_exactly_the_reviewed_structure():
    tree = ast.parse(_probe_bytes().decode("utf-8"))
    assert len(tree.body) == 3
    imp, out, end = tree.body

    assert isinstance(imp, ast.Import)
    assert [(a.name, a.asname) for a in imp.names] == [("sys", None)]

    assert isinstance(out, ast.Expr) and isinstance(out.value, ast.Call)
    call = out.value
    assert isinstance(call.func, ast.Name) and call.func.id == "print"
    assert len(call.args) == 1 and call.keywords == []
    assert _is_constant(call.args[0], EXPECTED_TEXT, str)

    assert isinstance(end, ast.Expr) and isinstance(end.value, ast.Call)
    call = end.value
    assert isinstance(call.func, ast.Attribute) and call.func.attr == "exit"
    assert isinstance(call.func.value, ast.Name) and call.func.value.id == "sys"
    assert len(call.args) == 1 and call.keywords == []
    assert _is_constant(call.args[0], EXPECTED_EXIT, int)
