"""CLI (D1, D2, D14-D16).

  .venv/Scripts/python.exe -B -m moneylab.controlled_read run --task <TASK_ID> --project-key <PROJECT_KEY>
      --session <SESSION> --selector <SELECTOR> --profile <PROFILE> --attempt <ATTEMPT>
  .venv/Scripts/python.exe -B -m moneylab.controlled_read status --task <TASK_ID> --attempt <ATTEMPT>
  .venv/Scripts/python.exe -B -m moneylab.controlled_read precheck --task <TASK_ID> --project-key <PROJECT_KEY>
      --session <SESSION> --profile <PROFILE>   (AUTO-09: no record, not a status target)

Each call prints exactly one canonical JSON document plus LF to stdout and nothing to stderr. A defined
failure is a document with exit code 2; an undefined exception propagates without output and is never
turned into a success. The only child processes are `git rev-parse --show-toplevel` and `git check-ignore`.

The approval is one chat message (D3). This program cannot see it and does not authenticate it: input that
matches the grammar is not evidence of approval, so every document says `approval: NOT_VERIFIED_BY_PROGRAM`.
`-B` only stops bytecode writes; it is not write isolation."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from moneylab.controlled_read import SUCCEEDED, ControlledReadError, profiles, store, transcript
from moneylab.controlled_read import selector as grammar
from moneylab.workstate import collect
from moneylab.workstate.collect import WorkstateError


def _package_root() -> Path:
    here = Path(__file__).resolve().parent
    root = here.parents[2]
    if (root / "src" / "moneylab" / "controlled_read").resolve() != here:
        raise ControlledReadError("ENVIRONMENT_INVALID")
    return root


def confirmed_root(root: Path | None = None) -> Path:
    """D2 cwd rule: the checkout root computed from the package location (or the test seam) must be the
    top level of its git worktree."""
    base = _package_root() if root is None else Path(root)
    if not base.is_dir():
        raise ControlledReadError("ENVIRONMENT_INVALID")
    try:
        top = collect.run_git(base, "rev-parse", ["--show-toplevel"])[1].decode("utf-8").strip()
    except (WorkstateError, UnicodeDecodeError):
        raise ControlledReadError("ENVIRONMENT_INVALID") from None
    if not top or os.path.normcase(os.path.realpath(top)) != os.path.normcase(os.path.realpath(base)):
        raise ControlledReadError("ENVIRONMENT_INVALID")
    return base


def confirmed_home(home: Path | None = None) -> Path:
    """D4: Path.home() (it follows environment variables) must be absolute. Its parents are not checked."""
    try:
        base = Path.home() if home is None else Path(home)
    except (RuntimeError, KeyError, OSError):
        raise ControlledReadError("ENVIRONMENT_INVALID") from None
    if not base.is_absolute():
        raise ControlledReadError("ENVIRONMENT_INVALID")
    return base


def _process(args: grammar.RunArgs, home: Path, known: dict[str, Any]) -> dict[str, Any]:
    """ERRATA-001 E2: open and measure, process, then re-hash after a success or a defined processing
    failure. A time-out ends at once without re-hashing. The re-hash result can replace the processing one."""
    deadline = transcript.Deadline()
    target = known["target"]
    try:
        selected = grammar.parse_selector(args.selector)
        profile = profiles.PROFILES[args.profile]
        profiles.check_kind(profile, selected.kind)
        session = transcript.open_session(home, args.project_key, args.session_id, target, deadline)
    except ControlledReadError as exc:  # the prefix was not established: measured fields stay null
        return store.result_document(exc.code, **known)
    try:
        outcome: str = SUCCEEDED
        body = b""
        try:
            text = transcript.select_text(session.prefix, selected, deadline)
            body = profiles.extract(profile, text)
        except ControlledReadError as exc:
            if exc.code == "TIME_LIMIT_EXCEEDED":
                target["prefix_check"] = transcript.INCOMPLETE
                return store.result_document(exc.code, **known)
            outcome = exc.code
        replaced, check = session.rehash(deadline)
        target["prefix_check"] = check
    finally:
        session.handle.close()
    if replaced is not None:
        return store.result_document(replaced, **known)
    if outcome != SUCCEEDED:
        return store.result_document(outcome, **known)
    return store.result_document(SUCCEEDED, values=profiles.values(body), **known)


def _run(argv: list[str], root: Path | None, home: Path | None) -> dict[str, Any]:
    try:
        args = grammar.parse_run(argv)
    except ControlledReadError as exc:  # E1.3: no identifying field is filled and nothing is echoed
        return store.result_document(exc.code)
    known: dict[str, Any] = {
        "task_id": args.task_id, "attempt": args.attempt,
        "target": store.target(args.project_key, args.session_id, args.selector),
        "profile": store.profile_ref(args.profile)}
    try:
        base = confirmed_root(root)
        home_dir = confirmed_home(home)
        directory = store.prepare_attempt(base, args.task_id, args.attempt)
    except ControlledReadError as exc:
        return store.result_document(exc.code, **known)
    try:
        store.create_record(directory / store.INTENT_NAME, store.intent_document(args, store.utc_now()))
    except ControlledReadError as exc:  # E3.2: the session is not opened
        return store.result_document(exc.code, record=store.store_failure("intent", exc), **known)
    result = _process(args, home_dir, known)
    try:
        store.create_record(directory / store.RESULT_NAME, store.stored_result_document(result, store.utc_now()))
    except ControlledReadError as exc:  # E3.3: never a success, whatever final_created says
        return store.result_document(exc.code, record=store.store_failure("result", exc), **known)
    return result


def _status(argv: list[str], root: Path | None) -> dict[str, Any]:
    try:
        args = grammar.parse_status(argv)
    except ControlledReadError as exc:
        return store.status_error_document(exc.code)
    try:
        base = confirmed_root(root)
    except ControlledReadError as exc:
        return store.status_error_document(exc.code, task_id=args.task_id, attempt=args.attempt)
    return store.status_document(base, args.task_id, args.attempt)


PASSED = "PASSED"
FAILED = "FAILED"
NOT_REACHED = "NOT_REACHED"


def _precheck(argv: list[str], root: Path | None, home: Path | None) -> dict[str, Any]:
    """AUTO-09 D7: scan the whole prefix for candidate text blocks of the profile, and only when exactly one
    exists check it on the run path and return its run selector. Nothing is recorded (D3)."""
    try:
        args = grammar.parse_precheck(argv)
    except ControlledReadError as exc:  # P1: nothing is echoed
        return store.precheck_document(exc.code)
    target: dict[str, Any] = {"project_key": args.project_key, "session_id": args.session_id, "prefix_bytes": None,
                              "prefix_sha256": None, "line_count": None, "trailing_partial_bytes": None,
                              "prefix_check": None}
    checks = {"scan": NOT_REACHED, "selected": NOT_REACHED}
    known: dict[str, Any] = {"task_id": args.task_id, "target": target, "profile": store.profile_ref(args.profile),
                             "checks": checks}
    try:
        confirmed_root(root)
        home_dir = confirmed_home(home)
    except ControlledReadError as exc:  # P2
        return store.precheck_document(exc.code, **known)
    profile = profiles.PROFILES[args.profile]
    deadline = transcript.Deadline()
    try:
        session = transcript.open_session(home_dir, args.project_key, args.session_id, target, deadline)
    except ControlledReadError as exc:  # P3: the prefix was not established, measured fields stay null
        return store.precheck_document(exc.code, **known)
    count: int | None = None
    found: str | None = None
    measured: dict[str, Any] | None = None
    try:
        try:
            candidates = transcript.scan_candidates(
                session.prefix, profile.kinds, lambda text: profiles.marker_line_present(profile, text), deadline)
        except ControlledReadError as exc:
            checks["scan"] = FAILED
            if exc.code == "TIME_LIMIT_EXCEEDED":  # P5: no re-hash
                target["prefix_check"] = transcript.INCOMPLETE
                return store.precheck_document(exc.code, **known)
            outcome = exc.code  # P4
        else:
            checks["scan"] = PASSED
            count = len(candidates)
            if count == 0:
                outcome = "PRECHECK_NO_CANDIDATE"  # P6
            elif count > 1:
                outcome = "PRECHECK_MULTIPLE_CANDIDATES"  # P7
            else:
                only = candidates[0]
                written = grammar.format_selector(only.kind, only.ident, only.text_index)
                if written is None:
                    outcome = "PRECHECK_SELECTOR_UNREPRESENTABLE"  # P8
                else:
                    try:
                        selected = grammar.parse_selector(written)
                        profiles.check_kind(profile, selected.kind)
                        text = transcript.select_text(session.prefix, selected, deadline)
                        measured = profiles.values(profiles.extract(profile, text))
                    except ControlledReadError as exc:
                        checks["selected"] = FAILED
                        if exc.code == "TIME_LIMIT_EXCEEDED":  # P10: no re-hash
                            target["prefix_check"] = transcript.INCOMPLETE
                            return store.precheck_document(exc.code, candidate_count=1, **known)
                        outcome = exc.code  # P9
                    else:
                        checks["selected"] = PASSED
                        outcome = store.PRECHECK_OK  # P11 unless the re-hash replaces it
                        found = written
        replaced, check = session.rehash(deadline)  # R
        target["prefix_check"] = check
    finally:
        session.handle.close()
    if replaced is not None:
        return store.precheck_document(replaced, **known)
    if outcome != store.PRECHECK_OK:
        return store.precheck_document(outcome, candidate_count=count, **known)
    return store.precheck_document(outcome, candidate_count=count, selector=found, values=measured, **known)


def run(argv: list[str], *, root: Path | None = None, home: Path | None = None) -> dict[str, Any]:
    """The one output document of a call. `root` and `home` are test seams."""
    if argv[:1] == ["status"]:
        return _status(argv, root)
    if argv[:1] == ["precheck"]:
        return _precheck(argv, root, home)
    return _run(argv, root, home)


def exit_code(document: dict[str, Any]) -> int:
    return int(document["exit_code"]) if "exit_code" in document else 0


def main(argv: list[str] | None = None, *, root: Path | None = None, home: Path | None = None) -> int:
    document = run(sys.argv[1:] if argv is None else list(argv), root=root, home=home)
    data = store.canonical_bytes(document)
    sys.stdout.flush()
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()
    return exit_code(document)


if __name__ == "__main__":
    sys.exit(main())
