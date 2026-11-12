"""CLI (AUTO-02 D1, D13): `python -m moneylab.workstate snapshot --task-id T [--reported-gate G --reported-result
PASS|NO]` and `python -m moneylab.workstate verify --task-id T --snapshot-id ID`.

Every outcome, argument errors included, is one `moneylab.workstate.result/1` object written to stdout as
canonical JSON plus LF; nothing is written to stderr (`--help` alone prints argparse text). The output always
carries `authority: "NONE"`: a MATCH grants no permission, no gate PASS and restores no authorization."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, NoReturn

from moneylab.workstate import collect, store
from moneylab.workstate.collect import ARGUMENT_INVALID, ENVIRONMENT_INVALID, WorkstateError

RESULT_SCHEMA = "moneylab.workstate.result/1"
COMPARED = ("branch", "head", "tree", "entries", "untracked paths", "contract")
NOT_COMPARED = ("untracked file bytes", "ignored files", "git config", "hooks", "history between snapshots")
RESULT_KEYS = frozenset({"schema", "command", "status", "exit_code", "task_id", "snapshot_id", "file_sha256",
                         "final_file_created", "state_sha256_stored", "state_sha256_current", "reported",
                         "reported_status", "differences", "warnings", "error", "authority", "compared",
                         "not_compared"})


class _ArgumentError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgumentError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="python -m moneylab.workstate", description="Non-authoritative work state snapshot.",
                     exit_on_error=False)
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    snapshot = sub.add_parser("snapshot", help="store the current state of this worktree", exit_on_error=False)
    snapshot.add_argument("--task-id", required=True)
    snapshot.add_argument("--reported-gate")
    snapshot.add_argument("--reported-result")
    verify = sub.add_parser("verify", help="compare one named snapshot with the current state",
                            exit_on_error=False)
    verify.add_argument("--task-id", required=True)
    verify.add_argument("--snapshot-id", required=True)
    return parser


def _result(command: str | None, status: str, exit_code: int, **fields: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA, "command": command, "status": status, "exit_code": exit_code, "task_id": None,
        "snapshot_id": None, "file_sha256": None, "final_file_created": None, "state_sha256_stored": None,
        "state_sha256_current": None, "reported": None, "reported_status": None, "differences": [],
        "warnings": [], "error": None, "authority": "NONE", "compared": list(COMPARED),
        "not_compared": list(NOT_COMPARED)}
    unknown = set(fields) - set(result)
    if unknown:
        raise KeyError(f"unknown result fields: {sorted(unknown)}")
    result.update(fields)
    if result["reported"] is not None:
        result["reported_status"] = "REPORTED_UNVERIFIED"
    return result


def _failure(command: str | None, code: str, detail: str, **fields: Any) -> dict[str, Any]:
    return _result(command, code, 2, error={"code": code, "detail": detail}, **fields)


def _from_error(command: str, exc: WorkstateError, **fields: Any) -> dict[str, Any]:
    fields.setdefault("file_sha256", exc.file_sha256)
    if exc.final_file_created is not None:
        fields["final_file_created"] = exc.final_file_created
    return _failure(command, exc.code, exc.detail, warnings=list(exc.warnings), **fields)


def _package_root() -> Path:
    here = Path(__file__).resolve().parent
    root = here.parents[2]
    if (root / "src" / "moneylab" / "workstate").resolve() != here:
        raise WorkstateError(ENVIRONMENT_INVALID, "package is not inside <root>/src/moneylab/workstate")
    return root


def _confirmed_root(root: Path | None) -> Path:
    base = _package_root() if root is None else Path(root)
    if not base.is_dir():
        raise WorkstateError(ENVIRONMENT_INVALID, "repository root is not a directory")
    try:
        top = collect.run_git(base, "rev-parse", ["--show-toplevel"])[1].decode("utf-8").strip()
    except (WorkstateError, UnicodeDecodeError) as exc:
        raise WorkstateError(ENVIRONMENT_INVALID, "repository root could not be confirmed") from exc
    if os.path.normcase(os.path.realpath(top)) != os.path.normcase(os.path.realpath(base)):
        raise WorkstateError(ENVIRONMENT_INVALID, "root is not the top level of its git worktree")
    return base


def _snapshot(root: Path, task_id: str, reported: dict[str, str] | None) -> dict[str, Any]:
    try:
        state = collect.collect_state(root, task_id)
    except WorkstateError as exc:
        return _from_error("snapshot", exc, task_id=task_id, reported=reported)
    current = store.state_sha256(state)
    record = store.build_record(task_id, state, reported)
    try:
        outcome = store.save_record(root, record)
    except WorkstateError as exc:
        return _from_error("snapshot", exc, task_id=task_id, snapshot_id=record["snapshot_id"], reported=reported,
                           state_sha256_current=current)
    warnings = list(outcome["warnings"])
    return _result("snapshot", outcome["status"], 1 if warnings else 0, task_id=task_id,
                   snapshot_id=record["snapshot_id"], file_sha256=outcome["file_sha256"],
                   final_file_created=outcome["final_file_created"],
                   state_sha256_stored=outcome["state_sha256_stored"], state_sha256_current=current,
                   reported=reported, warnings=warnings)


def _verify(root: Path, task_id: str, snapshot_id: str) -> dict[str, Any]:
    try:
        record, file_sha = store.load_record(root, task_id, snapshot_id)
    except WorkstateError as exc:
        return _from_error("verify", exc, task_id=task_id, snapshot_id=snapshot_id)
    known = {"task_id": task_id, "snapshot_id": snapshot_id, "file_sha256": file_sha,
             "state_sha256_stored": record["state_sha256"], "reported": record["reported"]}
    try:
        state = collect.collect_state(root, task_id)
    except WorkstateError as exc:
        return _from_error("verify", exc, **known)
    current = store.state_sha256(state)
    if record["state"] == state:  # D11 step 10: the whole state decides, not the description of differences
        return _result("verify", "MATCH", 0, state_sha256_current=current, **known)
    differences = store.compare_states(record["state"], state)
    if not differences:
        differences = [{"field": "state", "stored": record["state_sha256"], "current": current}]
    return _result("verify", "MISMATCH", 1, state_sha256_current=current, differences=differences, **known)


def run(argv: list[str] | None = None, root: Path | None = None) -> dict[str, Any]:
    try:
        args = build_parser().parse_args(argv)
    except (_ArgumentError, argparse.ArgumentError):
        return _failure(None, ARGUMENT_INVALID, "invalid arguments")
    command: str = args.command
    task_id = args.task_id
    if not store.valid_task_id(task_id):
        return _failure(command, ARGUMENT_INVALID, "invalid --task-id")
    reported: dict[str, str] | None = None
    if command == "snapshot":
        gate, outcome = args.reported_gate, args.reported_result
        if (gate is None) != (outcome is None):
            return _failure(command, ARGUMENT_INVALID, "--reported-gate and --reported-result go together",
                            task_id=task_id)
        if gate is not None:
            if gate not in store.GATES or outcome not in store.RESULTS:
                return _failure(command, ARGUMENT_INVALID, "invalid --reported-gate or --reported-result",
                                task_id=task_id)
            reported = {"gate": gate, "result": outcome}
    elif not store.valid_snapshot_id(args.snapshot_id):
        return _failure(command, ARGUMENT_INVALID, "invalid --snapshot-id", task_id=task_id)
    try:
        confirmed = _confirmed_root(root)
    except WorkstateError as exc:
        return _from_error(command, exc, task_id=task_id, reported=reported)
    if command == "snapshot":
        return _snapshot(confirmed, task_id, reported)
    return _verify(confirmed, task_id, args.snapshot_id)


def _emit(result: dict[str, Any]) -> None:
    data = (store.canonical_text(result) + "\n").encode("utf-8")
    sys.stdout.flush()
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
    result = run(argv, root)
    _emit(result)
    return int(result["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
