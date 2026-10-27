"""Read-only CLI: `python -m moneylab.knowledge validate [--full-history]`, `... query <name> [arg]` and
`... resolve-context` (one `moneylab.context.request/1` JSON object on stdin).

Output is canonical JSON. Exit codes: 0 ok, 1 rule violation or unknown record, 2 bad arguments, 3 no violation but
sources could not be verified (SOURCE_UNVERIFIED). A query runs only on a repository that validated with exit code 0;
otherwise it prints the validation report instead of a result and exits with that code. resolve-context exits 1 for
an untrusted repository or a required-record error, 2 for invalid JSON or REQUEST_INVALID and 3 for SOURCE_UNVERIFIED;
errors are printed as {"error": {"code", "detail"}}."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from moneylab.knowledge import REPO_ROOT, open_knowledge_base
from moneylab.knowledge.context import REPOSITORY_UNTRUSTED, REQUEST_INVALID, ContextRequestError, resolve_context
from moneylab.knowledge.model import CONTEXT_MODES, KINDS, TOPICS, canonical_json
from moneylab.knowledge.query import KnowledgeBase

QUERIES = ("get", "kind", "current", "lineage", "task", "topic", "support", "open-questions", "context")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m moneylab.knowledge", description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root (default: this checkout)")
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="check all records against the 15 rules")
    v.add_argument("--full-history", action="store_true", help="also check blobs at their recorded rev (full clone)")
    q = sub.add_parser("query", help="deterministic queries over valid records")
    q.add_argument("name", choices=QUERIES)
    q.add_argument("arg", nargs="?", default=None,
                   help=f"record ID, kind {KINDS}, task ID, topic {TOPICS} or mode {CONTEXT_MODES}")
    q.add_argument("--topic", default=None, help="context: restrict to one topic")
    sub.add_parser("resolve-context", help="read one ContextRequest JSON from stdin and print its ContextPacket")
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


def _context_error(code: str, detail: str, **extra: Any) -> str:
    return canonical_json({"error": {"code": code, "detail": detail}, **extra})


def resolve_context_command(kb: KnowledgeBase) -> int:
    try:
        text = sys.stdin.buffer.read().decode("utf-8")
        request = json.loads(text, object_pairs_hook=_strict_object, parse_constant=_reject_constant)
    except ValueError as exc:  # includes UnicodeDecodeError and JSONDecodeError
        sys.stdout.write(_context_error(REQUEST_INVALID, f"invalid JSON: {type(exc).__name__}: {exc}"))
        return 2
    if not kb.trusted:  # fail closed: no packet from an invalid or unverified repository
        sys.stdout.write(_context_error(REPOSITORY_UNTRUSTED, "knowledge repository did not validate; no packet",
                                        validation=kb.report.to_dict()))
        return kb.report.exit_code
    try:
        packet = resolve_context(kb, request)
    except ContextRequestError as exc:
        sys.stdout.write(_context_error(exc.code, exc.detail))
        return 2 if exc.code == REQUEST_INVALID else 1
    sys.stdout.write(canonical_json(packet))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    kb, report = open_knowledge_base(args.root, full_history=getattr(args, "full_history", False))
    if args.command == "validate":
        sys.stdout.write(canonical_json(report.to_dict()))
        return report.exit_code
    if args.command == "resolve-context":
        return resolve_context_command(kb)
    if not kb.trusted:  # fail closed: no partial answer from an invalid or unverified repository
        sys.stdout.write(canonical_json({"error": "knowledge repository did not validate; no query result",
                                         "validation": report.to_dict()}))
        return report.exit_code
    needs_arg = {"get", "kind", "lineage", "task", "topic", "support", "context"}
    if args.name in needs_arg and args.arg is None:
        parser.error(f"query {args.name} needs an argument")
    try:
        result = {
            "get": lambda: kb.get(args.arg),
            "kind": lambda: kb.by_kind(args.arg),
            "current": kb.current,
            "lineage": lambda: kb.lineage(args.arg),
            "task": lambda: kb.task_records(args.arg),
            "topic": lambda: kb.claims_by_topic(args.arg),
            "support": lambda: kb.claim_support(args.arg),
            "open-questions": kb.open_questions,
            "context": lambda: kb.context(args.arg, args.topic),
        }[args.name]()
    except ValueError as exc:
        parser.error(str(exc))
    except KeyError as exc:
        sys.stdout.write(canonical_json({"error": str(exc).strip("'\"")}))
        return 1
    if result is None:
        sys.stdout.write(canonical_json({"error": f"no valid record {args.arg}"}))
        return 1
    sys.stdout.write(canonical_json(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
