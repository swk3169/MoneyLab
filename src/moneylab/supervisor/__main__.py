"""Read-only CLI: `python -m moneylab.supervisor [--root R] propose` (one `moneylab.context.request/1` JSON object on
stdin) and `... check` (one `moneylab.supervisor.proposal/1` JSON object on stdin).

Output is canonical JSON on stdout; there are no file arguments. Errors are printed as {"error": {"code", "detail"}}
(with the validation report for an untrusted repository). Exit codes: propose 0 PROPOSALS_CREATED or NO_CANDIDATES,
1 required-record or Supervisor fail-closed error, 2 invalid JSON or REQUEST_INVALID; check 0 CURRENT, 1 STALE_SOURCE
or STALE_CONTEXT, 2 PROPOSAL_INVALID or CHECK_REQUEST_REJECTED; an untrusted repository exits with its validation
exit code (1, or 3 for SOURCE_UNVERIFIED)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from moneylab.knowledge import REPO_ROOT, ContextRequestError, KnowledgeBase, open_knowledge_base
from moneylab.knowledge.context import REPOSITORY_UNTRUSTED, REQUEST_INVALID
from moneylab.knowledge.model import canonical_json
from moneylab.supervisor.proposal import PROPOSAL_INVALID, SupervisorError, check_proposal, propose, validate_proposal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m moneylab.supervisor", description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root (default: this checkout)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("propose", help="read one ContextRequest JSON from stdin and print a supervisor result")
    sub.add_parser("check", help="read one proposal JSON from stdin and print whether its inputs are current")
    return parser


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate key {key!r}")
        obj[key] = value
    return obj


def _reject_constant(name: str) -> Any:
    raise ValueError(f"{name} is not valid JSON")


def _read_json() -> Any:
    text = sys.stdin.buffer.read().decode("utf-8")
    return json.loads(text, object_pairs_hook=_strict_object, parse_constant=_reject_constant)


def _error(code: str, detail: str, **extra: Any) -> str:
    return canonical_json({"error": {"code": code, "detail": detail}, **extra})


def _untrusted(kb: KnowledgeBase) -> int:
    sys.stdout.write(_error(REPOSITORY_UNTRUSTED, "knowledge repository did not validate; no result",
                            validation=kb.report.to_dict()))
    return kb.report.exit_code


def propose_command(kb: KnowledgeBase) -> int:
    try:
        request = _read_json()
    except ValueError as exc:  # includes UnicodeDecodeError and JSONDecodeError
        sys.stdout.write(_error(REQUEST_INVALID, f"invalid JSON: {type(exc).__name__}: {exc}"))
        return 2
    if not kb.trusted:
        return _untrusted(kb)
    try:
        result = propose(kb, request)
    except ContextRequestError as exc:
        sys.stdout.write(_error(exc.code, exc.detail))
        return 2 if exc.code == REQUEST_INVALID else 1
    except SupervisorError as exc:
        sys.stdout.write(_error(exc.code, exc.detail))
        return 1
    sys.stdout.write(canonical_json(result))
    return 0


def check_command(kb: KnowledgeBase) -> int:
    try:
        proposal = _read_json()
    except ValueError as exc:
        sys.stdout.write(_error(PROPOSAL_INVALID, f"invalid JSON: {type(exc).__name__}: {exc}"))
        return 2
    try:
        validate_proposal(proposal)
    except SupervisorError as exc:
        sys.stdout.write(_error(exc.code, exc.detail))
        return 2
    if not kb.trusted:
        return _untrusted(kb)
    try:
        result = check_proposal(kb, proposal)
    except SupervisorError as exc:  # CHECK_REQUEST_REJECTED or PROPOSAL_INVALID
        sys.stdout.write(_error(exc.code, exc.detail))
        return 2
    sys.stdout.write(canonical_json(result))
    return 0 if result["staleness"] == "CURRENT" else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    kb, _report = open_knowledge_base(args.root)
    return propose_command(kb) if args.command == "propose" else check_command(kb)


if __name__ == "__main__":
    sys.exit(main())
