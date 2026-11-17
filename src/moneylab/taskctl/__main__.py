"""CLI of taskctl (GOV-AUTOMATION-03 D3): `python -m moneylab.taskctl <command> --task-id T [options]`.

Every outcome is one `moneylab.taskctl.result/1` canonical JSON line on stdout. Exit codes: 0 OK, 3 STOP,
4 UNKNOWN, 2 INVALID. `authority` is always "NONE": the output is a display, not a permission, and taskctl
cannot authenticate the user messages whose fields the agent passes in.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from moneylab.taskctl import check as C
from moneylab.taskctl import lease as L
from moneylab.taskctl.ledger import (
    INVALID,
    LEDGER_EXISTS,
    LEDGER_ROOT,
    OK,
    PATH_INVALID,
    TaskctlError,
    append_event,
    check_dir,
    format_utc,
    is_hex32,
    is_hex40,
    is_hex64,
    is_utc,
    parse_utc,
    read_events,
    sha256_hex,
    task_dir,
)

RESULT_SCHEMA = "moneylab.taskctl.result/1"
UNKNOWN_CODES = {C.UNKNOWN_STEP}


def _now() -> datetime:
    """Seam for tests."""
    return datetime.now(UTC)


def _result(command: str, code: str, **fields: Any) -> dict[str, Any]:
    status = "OK" if code == OK else "UNKNOWN" if code in UNKNOWN_CODES else "INVALID" if code == INVALID else "STOP"
    out = {"schema": RESULT_SCHEMA, "command": command, "status": status, "code": code, "phase": None,
           "open_step": None, "budget": None, "authority": "NONE"}
    out.update(fields)
    return out


def _exit_code(result: dict[str, Any]) -> int:
    return {"OK": 0, "STOP": 3, "UNKNOWN": 4, "INVALID": 2}[result["status"]]


# ------------------------------------------------------------------------------------------- shared


class Session:
    """A verified ledger plus the Work Order it was delegated under."""

    def __init__(self, root: Path, task_id: str) -> None:
        self.root = root
        self.task_id = task_id
        self.directory = task_dir(root, task_id)
        self.events = read_events(root, task_id)
        self.ctx = C.replay(task_id, self.events)
        self.contract = C.load_contract(root, task_id, self.ctx.delegate["c1"])
        C.state_matches_contract(self.ctx, self.contract)

    def snapshot(self) -> C.Snapshot:
        return C.collect(self.root, self.contract.allowed)

    def budget(self, now: datetime) -> dict[str, Any]:
        return C.budget_report(self.ctx, self.contract.delegation["budget"], now)

    def unknown_steps(self) -> list[C.Step]:
        return [step for step in self.ctx.open_steps if step.nonce != self.ctx.nonce]

    def blockers(self, now: datetime) -> list[str]:
        """Reasons that refuse a state change (D6), in a fixed order."""
        found = []
        if L.revoked(self.directory):
            found.append(C.REVOKED)
        if now > self.ctx.expires():
            found.append(C.EXPIRED)
        if self.ctx.phase == "TERMINAL":
            found.append(C.TERMINAL)
        if L.read_lease(self.directory) is not None:
            found.append(L.LEASE_PRESENT)
        if self.unknown_steps():
            found.append(C.UNKNOWN_STEP)
        return found

    def summary(self, now: datetime) -> dict[str, Any]:
        open_steps = self.ctx.open_steps
        budget = {k: v for k, v in self.budget(now).items() if not k.startswith("_")}
        return {"phase": self.ctx.phase, "budget": budget,
                "open_step": {"step": open_steps[0].name, "start_seq": open_steps[0].start_seq,
                              "current_session": open_steps[0].nonce == self.ctx.nonce} if open_steps else None}


def _write(session: Session, command: str, kind: str, payload: dict[str, Any], now: datetime) -> None:
    """D5 order: create LEASE, re-verify the ledger, write one event, delete the own LEASE."""
    lease_id = L.acquire(session.directory, command, format_utc(now))
    events = read_events(session.root, session.task_id)
    if [sha for _, sha, _ in events] != [sha for _, sha, _ in session.events]:
        raise TaskctlError(C.STATE_CHANGED, "the ledger changed while this command ran")
    append_event(session.root, session.task_id, events, kind, format_utc(now), payload)
    L.release(session.directory, lease_id)


def _refuse_if(blockers: list[str], allowed: set[str]) -> None:
    for code in blockers:
        if code not in allowed:
            raise TaskctlError(code, "state changes are refused")


# ------------------------------------------------------------------------------------------- commands


def cmd_init(root: Path, args: argparse.Namespace, now: datetime) -> dict[str, Any]:
    for value, check, name in ((args.wo_sha256, is_hex64, "--wo-sha256"), (args.base, is_hex40, "--base"),
                               (args.expires_utc, is_utc, "--expires-utc"),
                               (args.session_nonce, is_hex32, "--session-nonce")):
        if not check(value):
            raise TaskctlError(INVALID, f"{name} is not valid")
    if check_dir(root, f"{LEDGER_ROOT}/{args.task_id}"):
        raise TaskctlError(LEDGER_EXISTS, "a ledger already exists for this task")
    if parse_utc(args.expires_utc) <= now:
        raise TaskctlError(C.EXPIRED, "the delegation has already expired")
    head = C.rev(root, "HEAD")
    if head is None:
        raise TaskctlError(C.HEAD_MISMATCH, "no HEAD")
    _, parents = C.commit_info(root, head)
    if parents != [args.base]:
        raise TaskctlError(C.BASE_MISMATCH, "HEAD's parent is not BASE")
    before, after = C.tree_files(root, args.base), C.tree_files(root, head)
    diff = {path for path in set(before) | set(after) if before.get(path) != after.get(path)}
    wo = C.wo_path(args.task_id)
    if diff != {wo} or wo in before:
        raise TaskctlError(C.CONTRACT_MISMATCH, "C1 must add exactly the Work Order")
    if C.rev(root, "refs/remotes/origin/main") != args.base:
        raise TaskctlError(C.BASE_MISMATCH, "origin/main is not BASE")
    contract = C.load_contract(root, args.task_id, head)
    if contract.wo_sha256 != args.wo_sha256:
        raise TaskctlError(C.CONTRACT_MISMATCH, "Work Order hash differs from WO_SHA256")
    snapshot = C.collect(root, contract.allowed)
    C.check_scope(snapshot)
    if not C.is_clean(snapshot.state):
        raise TaskctlError(C.NOT_CLEAN, "the worktree is not clean")
    if not check_dir(root, "data/processed"):
        raise TaskctlError(PATH_INVALID, "data/processed is missing")
    directory = task_dir(root, args.task_id)
    try:
        (directory / "events").mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise TaskctlError(LEDGER_EXISTS, "a ledger already exists for this task") from exc
    except OSError as exc:
        raise TaskctlError(PATH_INVALID, f"ledger directory could not be created: {type(exc).__name__}") from exc
    payload = {"c1": head, "wo_sha256": args.wo_sha256, "base": args.base, "expires_utc": args.expires_utc,
               "session_nonce": args.session_nonce, "delegation_sha256": C.delegation_sha256(contract.delegation),
               "state": snapshot.state}
    lease_id = L.acquire(directory, "INIT", format_utc(now))
    append_event(root, args.task_id, [], "DELEGATE", format_utc(now), payload)
    L.release(directory, lease_id)
    return _result("init", OK, phase="DELEGATED")


def cmd_publish(session: Session, args: argparse.Namespace, now: datetime) -> dict[str, Any]:
    _refuse_if(session.blockers(now), set())
    ctx = session.ctx
    if ctx.phase != "READY_TO_PUBLISH" or ctx.publish is not None:
        raise TaskctlError(C.INVALID_TRANSITION, "PUBLISH is recorded only in READY_TO_PUBLISH, once")
    snapshot = session.snapshot()
    pr_sha = L.read_pr_text_sha256(session.directory)
    head = snapshot.state["head"]
    checks = [(args.wo_c1, ctx.delegate["c1"]), (args.head, ctx.commit_i), (args.head, head),
              (args.tree, snapshot.state["tree"]), (args.base, ctx.delegate["base"]),
              (args.pr_text_sha256, pr_sha), (args.pr_text_sha256, (ctx.pr_text or {}).get("sha256"))]
    if any(given != expected for given, expected in checks) or not C.is_clean(snapshot.state):
        raise TaskctlError(C.PUBLISH_MISMATCH, "PUBLISH fields differ from the current state")
    if not is_utc(args.expires_utc) or parse_utc(args.expires_utc) <= now:
        raise TaskctlError(C.EXPIRED, "PUBLISH has expired")
    payload = {"wo_c1": args.wo_c1, "head": args.head, "tree": args.tree, "base": args.base,
               "pr_text_sha256": args.pr_text_sha256, "expires_utc": args.expires_utc}
    _write(session, "PUBLISH", "PUBLISH", payload, now)
    return _result("record-message", OK, phase=ctx.phase)


def cmd_resume(session: Session, args: argparse.Namespace, now: datetime) -> dict[str, Any]:
    _refuse_if(session.blockers(now), set())
    ctx = session.ctx
    if ctx.open_steps:
        raise TaskctlError(C.UNKNOWN_STEP, "an open step of an earlier session has an unknown result")
    if not is_hex32(args.session_nonce) or args.session_nonce in ctx.nonces:
        raise TaskctlError(C.SESSION_MISMATCH, "RESUME needs a new session nonce")
    snapshot = session.snapshot()
    checks = [(args.wo_sha256, ctx.delegate["wo_sha256"]), (args.delegation_id, ctx.delegation_id),
              (args.phase, ctx.phase), (args.head, snapshot.state["head"])]
    if any(given != expected for given, expected in checks):
        raise TaskctlError(C.CONTRACT_MISMATCH, "RESUME fields differ from the ledger or the worktree")
    C.check_scope(snapshot)
    if snapshot.state != ctx.last_state:
        raise TaskctlError(C.STATE_CHANGED, "the state differs from the last recorded step")
    payload = {"wo_sha256": args.wo_sha256, "delegation_id": args.delegation_id, "phase": args.phase,
               "head": args.head, "session_nonce": args.session_nonce, "state": snapshot.state}
    _write(session, "RESUME", "RESUME", payload, now)
    return _result("record-message", OK, phase=ctx.phase)


def cmd_step_start(session: Session, args: argparse.Namespace, now: datetime) -> dict[str, Any]:
    _refuse_if(session.blockers(now), set())
    ctx = session.ctx
    if args.session_nonce != ctx.nonce:
        raise TaskctlError(C.SESSION_MISMATCH, "not the current session nonce")
    if ctx.open_steps:
        raise TaskctlError(C.STEP_OPEN, "a step is still open")
    if args.step not in C.LOCAL_STEPS + C.PUBLISH_STEPS + ("SETUP_ENV", "POST_MERGE_AUDIT"):
        raise TaskctlError(INVALID, "unknown step")
    if not is_hex64(args.input_sha256):
        raise TaskctlError(INVALID, "--input-sha256 is not valid")
    commands = session.contract.delegation
    if args.step == "SETUP_ENV":
        expected = {sha256_hex("\n".join(commands["setup_commands"]).encode("utf-8"))}
    elif args.step in C.CHECK_STEPS:
        expected = {sha256_hex(text.encode("utf-8")) for text in commands["check_commands"]}
    else:
        expected = None
    if expected is not None and args.input_sha256 not in expected:
        raise TaskctlError(C.CONTRACT_MISMATCH, "the command hash is not a DELEGATION command")
    C.allowed_step(ctx, args.step)
    C.check_budget_for_start(session.budget(now), args.step)
    snapshot = session.snapshot()
    C.check_pre(ctx, args.step, snapshot)
    payload = {"step": args.step, "session_nonce": args.session_nonce, "input_sha256": args.input_sha256,
               "pre_state": snapshot.state}
    _write(session, "STEP_START", "STEP_START", payload, now)
    return _result("step start", OK, phase=ctx.phase)


def _parse_remote(items: list[str]) -> dict[str, Any]:
    remote: dict[str, Any] = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep or key in remote:
            raise TaskctlError(C.REMOTE_INVALID, "--remote takes KEY=VALUE once per key")
        if key in ("pr_number", "run_id"):
            remote[key] = int(value) if value.isdigit() else value
        elif key == "merge_parents":
            remote[key] = value.split(",")
        else:
            remote[key] = value
    if remote:
        remote["agent_reported"] = True
    return remote


def cmd_step_end(session: Session, args: argparse.Namespace, now: datetime) -> dict[str, Any]:
    _refuse_if(session.blockers(now), {C.REVOKED, C.EXPIRED})
    ctx = session.ctx
    if args.session_nonce != ctx.nonce:
        raise TaskctlError(C.SESSION_MISMATCH, "not the current session nonce")
    open_steps = [step for step in ctx.open_steps if step.nonce == ctx.nonce and step.name == args.step]
    if len(open_steps) != 1:
        raise TaskctlError(C.STEP_NOT_OPEN, "no open step of this name in the current session")
    step = open_steps[0]
    if args.failure_sig is not None and not is_hex64(args.failure_sig):
        raise TaskctlError(INVALID, "--failure-sig is not valid")
    remote = _parse_remote(args.remote or [])
    snapshot = session.snapshot()
    if args.result == "ok":
        C.check_post(session.root, ctx, step, snapshot, remote)
    payload = {"step": step.name, "start_seq": step.start_seq, "session_nonce": ctx.nonce, "result": args.result,
               "failure_sig": args.failure_sig, "post_state": snapshot.state, "remote": remote}
    try:
        _write(session, "STEP_END", "STEP_END", payload, now)
    except TaskctlError as exc:
        if exc.code == INVALID and remote:
            raise TaskctlError(C.REMOTE_INVALID, exc.detail) from exc
        raise
    return _result("step end", OK, phase=ctx.phase)


def cmd_phase_set(session: Session, args: argparse.Namespace, now: datetime) -> dict[str, Any]:
    ctx = session.ctx
    stopping = args.to == "TERMINAL" and args.terminal_status == "STOPPED"
    if stopping:
        # ERRATA-001: STOPPED is allowed with open steps of any nonce. Their STEP_START stays without a STEP_END
        # (result unknown); no STEP_END is synthesized and the nonce is not replaced.
        _refuse_if(session.blockers(now), {C.REVOKED, C.EXPIRED, C.UNKNOWN_STEP})
        if not args.code or not isinstance(args.code, str):
            raise TaskctlError(INVALID, "STOPPED needs --code")
    else:
        _refuse_if(session.blockers(now), set())
        if ctx.open_steps:
            raise TaskctlError(C.STEP_OPEN, "a step is still open")
        if args.to != "TERMINAL":
            report = session.budget(now)
            if report["elapsed_seconds"] >= report["time_limit_seconds"]:
                raise TaskctlError(C.BUDGET_TIME, "total elapsed time limit reached")
        C.check_transition(ctx, args.to, session.snapshot(), args.terminal_status, args.violations)
    payload = {"from": ctx.phase, "to": args.to, "terminal_status": args.terminal_status,
               "code": args.code if stopping else None, "violations": args.violations}
    _write(session, "PHASE", "PHASE", payload, now)
    return _result("phase-set", OK, phase=args.to)


def cmd_pr_text(session: Session, args: argparse.Namespace, now: datetime, data: bytes) -> dict[str, Any]:
    _refuse_if(session.blockers(now), set())
    if session.ctx.phase != "LOCAL_DONE" or session.ctx.pr_text is not None:
        raise TaskctlError(C.INVALID_TRANSITION, "PR text is written once, in LOCAL_DONE")
    if not is_hex64(args.sha256):
        raise TaskctlError(INVALID, "--sha256 is not valid")
    L.check_pr_text(data, args.sha256)
    if L.read_pr_text_sha256(session.directory) is not None:  # D4 path check before the LEASE is created
        raise TaskctlError(L.PR_TEXT_EXISTS, "pr_text.md already exists and is never replaced")
    lease_id = L.acquire(session.directory, "PR_TEXT", format_utc(now))
    events = read_events(session.root, session.task_id)
    L.write_pr_text(session.directory, data)
    append_event(session.root, session.task_id, events, "PR_TEXT", format_utc(now),
                 {"sha256": args.sha256, "bytes": len(data)})
    L.release(session.directory, lease_id)
    return _result("pr-text", OK, phase=session.ctx.phase)


def cmd_lease_clear(root: Path, args: argparse.Namespace, now: datetime) -> dict[str, Any]:
    if not is_hex32(args.lease_id):
        raise TaskctlError(INVALID, "--lease-id is not valid")
    session = Session(root, args.task_id)
    lease = L.read_lease(session.directory)
    if lease is None:
        raise TaskctlError(L.LEASE_ABSENT, "there is no LEASE")
    if lease.get("lease_id") != args.lease_id:
        raise TaskctlError(L.LEASE_MISMATCH, "LEASE does not hold the named id")
    append_event(root, args.task_id, session.events, "LEASE_CLEARED", format_utc(now), {"lease_id": args.lease_id})
    L.delete_cleared(session.directory, args.lease_id)
    return _result("lease-clear", OK, phase=session.ctx.phase)


def cmd_revoke(root: Path, args: argparse.Namespace, now: datetime) -> dict[str, Any]:
    directory = task_dir(root, args.task_id)
    if not check_dir(root, f"{LEDGER_ROOT}/{args.task_id}"):
        raise TaskctlError("LEDGER_MISSING", "no ledger for this task")
    created = L.write_revoked(directory, format_utc(now))
    return _result("revoke", OK, revoked=True, newly_revoked=created)


def cmd_status(session: Session, now: datetime, command: str) -> dict[str, Any]:
    ctx = session.ctx
    summary = session.summary(now)
    head = C.rev(session.root, "HEAD")
    resume = (f"RESUME: {session.task_id} WO_SHA256={ctx.delegate['wo_sha256']} "
              f"DELEGATION_ID={ctx.delegation_id} PHASE={ctx.phase} HEAD={head}")
    lease = L.read_lease(session.directory)
    blockers = session.blockers(now)
    return _result(command, OK, phase=summary["phase"], open_step=summary["open_step"], budget=summary["budget"],
                   blockers=blockers, lease_id=lease.get("lease_id") if lease else None,
                   events=len(session.events), resume_draft=resume)


def cmd_publish_draft(session: Session, now: datetime) -> dict[str, Any]:
    ctx = session.ctx
    if ctx.phase != "READY_TO_PUBLISH" or ctx.pr_text is None or ctx.commit_i is None:
        raise TaskctlError(C.INVALID_TRANSITION, "a PUBLISH draft exists only in READY_TO_PUBLISH")
    L.read_pr_text_sha256(session.directory)  # D4: a linked or broken pr_text.md is PATH_INVALID
    tree = C.rev(session.root, ctx.commit_i + "^{tree}")
    draft = (f"PUBLISH: {session.task_id} WO@{ctx.delegate['c1']} HEAD={ctx.commit_i} TREE={tree} "
             f"BASE={ctx.delegate['base']} PR_TEXT_SHA256={ctx.pr_text['sha256']} "
             f"EXPIRES_UTC={ctx.delegate['expires_utc']}")
    return _result("publish-draft", OK, phase=ctx.phase, publish_draft=draft)


def cmd_check(session: Session, args: argparse.Namespace) -> dict[str, Any]:
    ctx = session.ctx
    snapshot = session.snapshot()
    code = C.scope_code(snapshot)
    if code is None:
        expected_head = ctx.commit_i if ctx.commit_i else ctx.delegate["c1"]
        if snapshot.state["head"] != expected_head:
            code = C.HEAD_MISMATCH
        elif snapshot.state != ctx.last_state and not ctx.open_steps:
            code = C.STATE_CHANGED
    return _result("check", code or OK, phase=ctx.phase, checked_phase=args.phase)


# ------------------------------------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m moneylab.taskctl")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name)
        p.add_argument("--task-id", required=True)
        p.add_argument("--repo", default=None)
        return p

    p = add("init")
    for name in ("--wo-sha256", "--base", "--expires-utc", "--session-nonce"):
        p.add_argument(name, required=True)
    p = add("record-message")
    p.add_argument("--kind", required=True, choices=["PUBLISH", "RESUME"])
    for name in ("--wo-c1", "--head", "--tree", "--base", "--pr-text-sha256", "--expires-utc", "--wo-sha256",
                 "--delegation-id", "--phase", "--session-nonce"):
        p.add_argument(name)
    p = add("step")
    p.add_argument("action", choices=["start", "end"])
    p.add_argument("--step", required=True)
    p.add_argument("--session-nonce", required=True)
    p.add_argument("--input-sha256")
    p.add_argument("--result", choices=["ok", "fail"])
    p.add_argument("--failure-sig")
    p.add_argument("--remote", action="append")
    p = add("phase-set")
    p.add_argument("--to", required=True)
    p.add_argument("--terminal-status", choices=["COMPLETE", "CLOSED_WITH_VIOLATION", "STOPPED"])
    p.add_argument("--code")
    p.add_argument("--violations", type=int)
    p = add("pr-text")
    p.add_argument("--sha256", required=True)
    p = add("lease-clear")
    p.add_argument("--lease-id", required=True)
    add("revoke")
    add("status")
    add("verify-ledger")
    p = add("check")
    p.add_argument("--read-only", action="store_true", required=True)
    p.add_argument("--phase", required=True)
    add("publish-draft")
    return parser


def run(argv: list[str], stdin: bytes = b"") -> dict[str, Any]:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return _result("usage", INVALID)
    command = args.command if args.command != "step" else f"step {args.action}"
    now = _now()
    try:
        root = C.confirm_root(Path(args.repo) if args.repo else Path.cwd())
        task_dir(root, args.task_id)
        if args.command == "init":
            return cmd_init(root, args, now)
        if args.command == "revoke":
            return cmd_revoke(root, args, now)
        if args.command == "lease-clear":
            return cmd_lease_clear(root, args, now)
        session = Session(root, args.task_id)
        if args.command in ("status", "verify-ledger"):
            return cmd_status(session, now, args.command)
        if args.command == "check":
            return cmd_check(session, args)
        if args.command == "publish-draft":
            return cmd_publish_draft(session, now)
        if args.command == "record-message":
            return cmd_publish(session, args, now) if args.kind == "PUBLISH" else cmd_resume(session, args, now)
        if args.command == "step":
            if args.action == "start":
                return cmd_step_start(session, args, now)
            if args.result is None:
                raise TaskctlError(INVALID, "step end needs --result")
            return cmd_step_end(session, args, now)
        if args.command == "phase-set":
            return cmd_phase_set(session, args, now)
        if args.command == "pr-text":
            return cmd_pr_text(session, args, now, stdin)
        raise TaskctlError(INVALID, "unknown command")
    except TaskctlError as exc:
        extra = {key: value for key, value in exc.extra.items() if key in ("created", "created_sha256",
                                                                            "tmp_leftover_possible")}
        return _result(command, exc.code, detail=exc.detail, **extra)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    stdin = sys.stdin.buffer.read() if argv[:1] == ["pr-text"] else b""
    result = run(argv, stdin)
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")
    sys.stdout.flush()
    return _exit_code(result)


if __name__ == "__main__":
    sys.exit(main())
