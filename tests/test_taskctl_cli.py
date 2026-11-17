"""taskctl CLI on temporary Git repositories (GOV-AUTOMATION-03 D1, D3, D6, D7). Offline."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from moneylab.taskctl import __main__ as M
from moneylab.taskctl import lease as LS
from moneylab.taskctl import ledger as LG

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

TASK = "PILOT-X"
NOW = datetime(2026, 11, 16, 12, 0, 0, tzinfo=UTC)
N1 = "a" * 32
N2 = "b" * 32
SETUP = ["python -m venv .venv"]
CHECKS = {"TEST_TARGETED": "python -m pytest tests/test_x.py", "TEST_FULL": "python -m pytest",
          "LINT": "ruff check", "TYPECHECK": "mypy"}


def work_order(**overrides: str) -> str:
    keys = {"DELEGATION_SCHEMA": "moneylab.delegation/1", "LEDGER_TASK_ID": TASK, "BUDGET_TIME_SECONDS": "14400",
            "BUDGET_FIX": "5", "BUDGET_PYTEST": "3", "BUDGET_SAME_FAIL": "2", "REQUIRED_CI": "pytest",
            "PR_TITLE": "pilot change", "SETUP_COMMAND_1": SETUP[0], "CHECK_COMMAND_1": CHECKS["TEST_TARGETED"],
            "CHECK_COMMAND_2": CHECKS["TEST_FULL"], "CHECK_COMMAND_3": CHECKS["LINT"],
            "CHECK_COMMAND_4": CHECKS["TYPECHECK"]}
    keys.update(overrides)
    lines = [f"{key}: {value}" for key, value in keys.items() if value != "<drop>"]
    return ("# Work Order: PILOT-X\n\n## ALLOWED_FILES\n\n- A src/pkg/new.py\n- M README.md\n\n## DELEGATION\n\n"
            + "\n".join(lines) + "\n\n## STOP_CONDITIONS\n\n- none\n")


def sha(text: str | bytes) -> str:
    return hashlib.sha256(text.encode("utf-8") if isinstance(text, str) else text).hexdigest()


class Repo:
    def __init__(self, root: Path) -> None:
        self.root = root

    def git(self, *args: str) -> str:
        out = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, check=True)
        return out.stdout.decode().strip()

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def commit(self, *paths: str, message: str = "c") -> str:
        self.git("add", "--", *paths)
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")


def make_repo(tmp_path: Path, wo_text: str | None = None) -> tuple[Repo, str, str]:
    repo = Repo(tmp_path / "repo")
    repo.root.mkdir()
    for args in (("init", "-q"), ("config", "user.email", "t@example.invalid"), ("config", "user.name", "t"),
                 ("config", "core.autocrlf", "false")):
        repo.git(*args)
    repo.write("README.md", "readme\n")
    repo.write(".gitignore", "data/processed/*\n!data/processed/.gitkeep\n.venv/\n")
    repo.write("data/processed/.gitkeep", "")
    repo.write("docs/tasks/OTHER/WORK_ORDER.md", "other\n")
    repo.write("src/pkg/__init__.py", "")
    base = repo.commit("README.md", ".gitignore", "data/processed/.gitkeep", "docs/tasks/OTHER/WORK_ORDER.md",
                       "src/pkg/__init__.py", message="base")
    repo.git("update-ref", "refs/remotes/origin/main", base)
    repo.write(f"docs/tasks/{TASK}/WORK_ORDER.md", wo_text if wo_text is not None else work_order())
    c1 = repo.commit(f"docs/tasks/{TASK}/WORK_ORDER.md", message="wo")
    return repo, base, c1


class Taskctl:
    def __init__(self, repo: Repo, monkeypatch: pytest.MonkeyPatch) -> None:
        self.repo = repo
        self.now = NOW
        monkeypatch.setattr(M, "_now", lambda: self.now)

    def __call__(self, *args: str, stdin: bytes = b"") -> dict:
        command = list(args[:1]) + (list(args[1:2]) if args[:1] == ("step",) else [])
        rest = list(args[len(command):])
        result = M.run([*command, "--task-id", TASK, "--repo", str(self.repo.root), *rest], stdin)
        json.dumps(result)  # always serializable
        assert result["authority"] == "NONE"
        return result

    def init(self, base: str, c1: str, expires: datetime | None = None) -> dict:
        wo = self.repo.root / f"docs/tasks/{TASK}/WORK_ORDER.md"
        expires = expires or NOW + timedelta(hours=8)
        return self("init", "--wo-sha256", sha(wo.read_bytes()), "--base", base,
                    "--expires-utc", expires.strftime("%Y-%m-%dT%H:%M:%SZ"), "--session-nonce", N1)

    def start(self, step: str, nonce: str = N1) -> dict:
        digest = sha("\n".join(SETUP)) if step == "SETUP_ENV" else sha(CHECKS[step]) if step in CHECKS else "c" * 64
        return self("step", "start", "--step", step, "--session-nonce", nonce, "--input-sha256", digest)

    def end(self, step: str, result: str = "ok", nonce: str = N1, *extra: str) -> dict:
        return self("step", "end", "--step", step, "--session-nonce", nonce, "--result", result, *extra)

    def run_step(self, step: str, action=None) -> None:
        assert self.start(step)["code"] == "OK"
        if action:
            action()
        out = self.end(step)
        assert out["code"] == "OK", out

    def phase(self, to: str, *extra: str) -> dict:
        return self("phase-set", "--to", to, *extra)


@pytest.fixture
def env(tmp_path, monkeypatch):
    repo, base, c1 = make_repo(tmp_path)
    return repo, base, c1, Taskctl(repo, monkeypatch)


def to_setup_done(repo: Repo, base: str, c1: str, tc: Taskctl) -> None:
    assert tc.init(base, c1)["code"] == "OK"
    tc.run_step("SETUP_ENV", lambda: (repo.root / ".venv").mkdir())
    assert tc.phase("SETUP_DONE")["code"] == "OK"


def implement(repo: Repo) -> None:
    repo.write("src/pkg/new.py", "x = 1\n")
    repo.write("README.md", "readme 2\n")


def to_committed(repo: Repo, base: str, c1: str, tc: Taskctl) -> str:
    to_setup_done(repo, base, c1, tc)
    tc.run_step("IMPLEMENT", lambda: implement(repo))
    for step in ("TEST_TARGETED", "LINT", "TYPECHECK", "TEST_FULL", "LOCAL_AUDIT"):
        tc.run_step(step)
    holder: dict[str, str] = {}
    tc.run_step("LOCAL_COMMIT", lambda: holder.update(i=repo.commit("src/pkg/new.py", "README.md", message="impl")))
    return holder["i"]


def to_local_done(repo: Repo, base: str, c1: str, tc: Taskctl) -> str:
    i = to_committed(repo, base, c1, tc)
    tc.run_step("CLEAN_E2E")
    assert tc.phase("LOCAL_DONE")["code"] == "OK"
    return i


PR_BODY = b"body\n"
PUBLISH_EXPIRES = "2026-11-16T20:00:00Z"


def to_ready(repo: Repo, base: str, c1: str, tc: Taskctl) -> tuple[str, str]:
    i = to_local_done(repo, base, c1, tc)
    assert tc("pr-text", "--sha256", sha(PR_BODY), stdin=PR_BODY)["code"] == "OK"
    assert tc.phase("READY_TO_PUBLISH")["code"] == "OK"
    return i, repo.git("rev-parse", f"{i}^{{tree}}")


def record_publish(tc: Taskctl, c1: str, i: str, tree: str, base: str) -> dict:
    return tc("record-message", "--kind", "PUBLISH", "--wo-c1", c1, "--head", i, "--tree", tree, "--base", base,
              "--pr-text-sha256", sha(PR_BODY), "--expires-utc", PUBLISH_EXPIRES)


def to_publishing(repo: Repo, base: str, c1: str, tc: Taskctl) -> tuple[str, str]:
    i, tree = to_ready(repo, base, c1, tc)
    out = record_publish(tc, c1, i, tree, base)
    assert out["code"] == "OK", out
    assert tc.phase("PUBLISHING")["code"] == "OK"
    return i, tree


def remote_args(values: list[str]) -> list[str]:
    return [x for value in values for x in ("--remote", value)]


def publish_remotes(i: str, base: str, merge: str) -> dict[str, list[str]]:
    return {"PUSH": [f"pushed_head={i}"], "PR_CREATE": ["pr_number=7"],
            "CI_WAIT": ["run_id=9", f"run_head_sha={i}", "required_conclusion=success"], "PREMERGE_CHECK": [],
            "MERGE": [f"merge_sha={merge}", f"merge_parents={base},{i}"]}


def run_publish(tc: Taskctl, remotes: dict[str, list[str]], steps: tuple[str, ...]) -> None:
    for step in steps:
        assert tc.start(step)["code"] == "OK"
        out = tc.end(step, "ok", N1, *remote_args(remotes[step]))
        assert out["code"] == "OK", out


def good_merge(repo: Repo, base: str, i: str, tree: str) -> str:
    return repo.git("commit-tree", tree, "-p", base, "-p", i, "-m", "merge")


def to_merged(repo: Repo, base: str, c1: str, tc: Taskctl, make_merge=good_merge) -> tuple[str, str, str]:
    i, tree = to_publishing(repo, base, c1, tc)
    merge = make_merge(repo, base, i, tree)
    run_publish(tc, publish_remotes(i, base, merge), ("PUSH", "PR_CREATE", "CI_WAIT", "PREMERGE_CHECK", "MERGE"))
    assert tc.phase("MERGED")["code"] == "OK"
    return i, tree, merge


# ------------------------------------------------------------------------------------------- happy path


@needs_git
def test_full_delegation_path_reaches_complete(env):
    repo, base, c1, tc = env
    i = to_local_done(repo, base, c1, tc)
    text = b"PR body\n"
    assert tc("pr-text", "--sha256", sha(text), stdin=text)["code"] == "OK"
    assert tc.phase("READY_TO_PUBLISH")["code"] == "OK"
    draft = tc("publish-draft")["publish_draft"]
    fields = dict(part.split("=", 1) for part in draft.split()[3:])
    assert draft.startswith(f"PUBLISH: {TASK} WO@{c1} HEAD={i} ")
    tree = repo.git("rev-parse", f"{i}^{{tree}}")
    assert fields["TREE"] == tree and fields["BASE"] == base and fields["PR_TEXT_SHA256"] == sha(text)
    out = tc("record-message", "--kind", "PUBLISH", "--wo-c1", c1, "--head", i, "--tree", tree, "--base", base,
             "--pr-text-sha256", sha(text), "--expires-utc", fields["EXPIRES_UTC"])
    assert out["code"] == "OK", out
    assert tc.phase("PUBLISHING")["code"] == "OK"
    merge = repo.git("commit-tree", tree, "-p", base, "-p", i, "-m", "merge")
    remotes = {"PUSH": [f"pushed_head={i}"], "PR_CREATE": ["pr_number=7"],
               "CI_WAIT": ["run_id=9", f"run_head_sha={i}", "required_conclusion=success"], "PREMERGE_CHECK": [],
               "MERGE": [f"merge_sha={merge}", f"merge_parents={base},{i}"]}
    for step, values in remotes.items():
        assert tc.start(step)["code"] == "OK"
        extra = [x for value in values for x in ("--remote", value)]
        out = tc.end(step, "ok", N1, *extra)
        assert out["code"] == "OK", out
    assert tc.phase("MERGED")["code"] == "OK"
    repo.git("update-ref", "refs/remotes/origin/main", merge)
    assert tc.start("POST_MERGE_AUDIT")["code"] == "OK"
    out = tc.end("POST_MERGE_AUDIT", "ok", N1, "--remote", f"merge_sha={merge}", "--remote",
                 f"merge_tree_recomputed={tree}")
    assert out["code"] == "OK", out
    assert tc.phase("AUDITED")["code"] == "OK"
    assert tc.phase("TERMINAL", "--terminal-status", "COMPLETE", "--violations", "1")["code"] == "INVALID_TRANSITION"
    assert tc.phase("TERMINAL", "--terminal-status", "COMPLETE", "--violations", "0")["code"] == "OK"
    status = tc("status")
    assert status["phase"] == "TERMINAL" and "TERMINAL" in status["blockers"]
    assert tc.start("IMPLEMENT")["code"] == "TERMINAL"


@needs_git
def test_publish_fields_must_match_current_state(env):
    repo, base, c1, tc = env
    i = to_local_done(repo, base, c1, tc)
    text = b"body\n"
    tc("pr-text", "--sha256", sha(text), stdin=text)
    tc.phase("READY_TO_PUBLISH")
    tree = repo.git("rev-parse", f"{i}^{{tree}}")
    out = tc("record-message", "--kind", "PUBLISH", "--wo-c1", c1, "--head", c1, "--tree", tree, "--base", base,
             "--pr-text-sha256", sha(text), "--expires-utc", "2026-11-16T20:00:00Z")
    assert out["code"] == "PUBLISH_MISMATCH"
    assert tc.phase("PUBLISHING")["code"] == "INVALID_TRANSITION"


@needs_git
def test_remote_values_are_checked_against_publish(env):
    repo, base, c1, tc = env
    i = to_local_done(repo, base, c1, tc)
    text = b"body\n"
    tc("pr-text", "--sha256", sha(text), stdin=text)
    tc.phase("READY_TO_PUBLISH")
    tree = repo.git("rev-parse", f"{i}^{{tree}}")
    tc("record-message", "--kind", "PUBLISH", "--wo-c1", c1, "--head", i, "--tree", tree, "--base", base,
       "--pr-text-sha256", sha(text), "--expires-utc", "2026-11-16T20:00:00Z")
    tc.phase("PUBLISHING")
    assert tc.start("PR_CREATE")["code"] == "INVALID_TRANSITION"  # order
    tc.start("PUSH")
    assert tc.end("PUSH", "ok", N1, "--remote", f"pushed_head={c1}")["code"] == "PUBLISH_MISMATCH"
    assert tc.end("PUSH", "ok", N1, "--remote", "url=https://x")["code"] == "REMOTE_INVALID"
    assert tc.end("PUSH", "ok", N1)["code"] == "REMOTE_INVALID"
    assert tc.end("PUSH", "fail", N1)["code"] == "OK"


# ------------------------------------------------------------------------------------------- init


@needs_git
def test_init_checks(tmp_path, monkeypatch):
    repo, base, c1 = make_repo(tmp_path)
    tc = Taskctl(repo, monkeypatch)
    assert tc("init", "--wo-sha256", "0" * 64, "--base", base, "--expires-utc", "2026-11-16T20:00:00Z",
              "--session-nonce", N1)["code"] == "CONTRACT_MISMATCH"
    assert tc("init", "--wo-sha256", "0" * 64, "--base", c1, "--expires-utc", "2026-11-16T20:00:00Z",
              "--session-nonce", N1)["code"] == "BASE_MISMATCH"
    assert tc.init(base, c1, expires=NOW - timedelta(seconds=1))["code"] == "EXPIRED"
    repo.write("README.md", "dirty\n")
    assert tc.init(base, c1)["code"] == "NOT_CLEAN"
    repo.git("checkout", "--", "README.md")
    repo.git("update-ref", "refs/remotes/origin/main", c1)
    assert tc.init(base, c1)["code"] == "BASE_MISMATCH"
    repo.git("update-ref", "refs/remotes/origin/main", base)
    assert tc.init(base, c1)["code"] == "OK"
    assert tc.init(base, c1)["code"] == "LEDGER_EXISTS"
    assert tc("init", "--wo-sha256", "x", "--base", base, "--expires-utc", "z", "--session-nonce", N1)["code"] == \
        "INVALID"


@needs_git
def test_init_requires_c1_to_add_only_the_work_order(tmp_path, monkeypatch):
    repo, base, c1 = make_repo(tmp_path)
    repo.write("src/pkg/extra.py", "")
    repo.git("reset", "-q", "--soft", base)
    repo.commit(f"docs/tasks/{TASK}/WORK_ORDER.md", "src/pkg/extra.py", message="wo+extra")
    tc = Taskctl(repo, monkeypatch)
    assert tc.init(base, "")["code"] == "CONTRACT_MISMATCH"


@needs_git
@pytest.mark.parametrize("override", [
    {"BUDGET_FIX": "6"}, {"BUDGET_FIX": "x"}, {"LEDGER_TASK_ID": "OTHER"}, {"REQUIRED_CI": "<drop>"},
    {"DELEGATION_SCHEMA": "moneylab.delegation/2"}, {"CHECK_COMMAND_1": "<drop>"}, {"EXTRA_KEY": "1"},
    {"PR_TITLE": "x" * 201},
])
def test_init_rejects_invalid_delegation(tmp_path, monkeypatch, override):
    repo, base, c1 = make_repo(tmp_path, work_order(**override))
    assert Taskctl(repo, monkeypatch).init(base, c1)["code"] == "DELEGATION_INVALID"


@needs_git
def test_init_rejects_duplicate_and_malformed_delegation_lines(tmp_path, monkeypatch):
    text = work_order().replace("REQUIRED_CI: pytest", "REQUIRED_CI: pytest\nREQUIRED_CI: other")
    repo, base, c1 = make_repo(tmp_path, text)
    assert Taskctl(repo, monkeypatch).init(base, c1)["code"] == "DELEGATION_INVALID"


@needs_git
def test_init_rejects_free_text_in_delegation(tmp_path, monkeypatch):
    text = work_order().replace("REQUIRED_CI: pytest", "REQUIRED_CI: pytest\nfree text")
    repo, base, c1 = make_repo(tmp_path, text)
    assert Taskctl(repo, monkeypatch).init(base, c1)["code"] == "DELEGATION_INVALID"


# ------------------------------------------------------------------------------------------- phases


@needs_git
def test_transitions_require_their_events(env):
    repo, base, c1, tc = env
    assert tc("status")["code"] == "LEDGER_MISSING"
    assert tc.init(base, c1)["code"] == "OK"
    assert tc.phase("SETUP_DONE")["code"] == "INVALID_TRANSITION"
    assert tc.phase("LOCAL_DONE")["code"] == "INVALID_TRANSITION"
    tc.run_step("SETUP_ENV", lambda: (repo.root / ".venv").mkdir())
    assert tc.start("IMPLEMENT")["code"] == "INVALID_TRANSITION"  # phase is still DELEGATED
    assert tc.phase("SETUP_DONE")["code"] == "OK"
    assert tc.phase("LOCAL_DONE")["code"] == "INVALID_TRANSITION"
    tc.run_step("IMPLEMENT", lambda: implement(repo))
    tc.run_step("TEST_TARGETED")
    assert tc.start("LOCAL_COMMIT")["code"] == "INVALID_TRANSITION"  # LOCAL_AUDIT must come right before
    assert tc.phase("READY_TO_PUBLISH")["code"] == "INVALID_TRANSITION"
    assert tc.phase("TERMINAL", "--terminal-status", "COMPLETE", "--violations", "0")["code"] == "INVALID_TRANSITION"
    assert tc.phase("TERMINAL", "--terminal-status", "STOPPED")["code"] == "INVALID"
    assert tc.phase("TERMINAL", "--terminal-status", "STOPPED", "--code", "OPERATOR_STOP")["code"] == "OK"


@needs_git
def test_local_done_requires_checks_after_the_last_implement(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    tc.run_step("IMPLEMENT", lambda: implement(repo))
    for step in ("TEST_TARGETED", "LINT", "TYPECHECK", "TEST_FULL"):
        tc.run_step(step)
    tc.run_step("IMPLEMENT", lambda: repo.write("src/pkg/new.py", "x = 2\n"))
    tc.run_step("LOCAL_AUDIT")
    holder: dict[str, str] = {}
    tc.run_step("LOCAL_COMMIT", lambda: holder.update(i=repo.commit("src/pkg/new.py", "README.md")))
    tc.run_step("CLEAN_E2E")
    assert tc.phase("LOCAL_DONE")["code"] == "INVALID_TRANSITION"


# ------------------------------------------------------------------------------------------- sessions


@needs_git
def test_open_step_rules_and_unknown_after_restart(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    assert tc.start("IMPLEMENT")["code"] == "OK"
    assert tc.start("TEST_TARGETED")["code"] == "STEP_OPEN"
    assert tc.phase("LOCAL_DONE")["code"] == "STEP_OPEN"  # STOPPED is allowed here since ERRATA-001 (T16)
    assert tc.end("TEST_TARGETED")["code"] == "STEP_NOT_OPEN"
    assert tc.end("IMPLEMENT", "ok", N2)["code"] == "SESSION_MISMATCH"
    status = tc("status")
    resume = dict(part.split("=", 1) for part in status["resume_draft"].split()[2:])
    # new session: the open IMPLEMENT of the previous session has an unknown result
    out = tc("record-message", "--kind", "RESUME", "--wo-sha256", resume["WO_SHA256"], "--delegation-id",
             resume["DELEGATION_ID"], "--phase", resume["PHASE"], "--head", resume["HEAD"], "--session-nonce", N2)
    assert out["code"] == "UNKNOWN_STEP" and out["status"] == "UNKNOWN"


@needs_git
def test_unknown_step_from_previous_session_blocks_everything_but_stop(env, monkeypatch):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    status = tc("status")
    resume = dict(part.split("=", 1) for part in status["resume_draft"].split()[2:])
    assert tc("record-message", "--kind", "RESUME", "--wo-sha256", resume["WO_SHA256"], "--delegation-id",
              resume["DELEGATION_ID"], "--phase", resume["PHASE"], "--head", resume["HEAD"],
              "--session-nonce", N1)["code"] == "SESSION_MISMATCH"
    assert tc("record-message", "--kind", "RESUME", "--wo-sha256", resume["WO_SHA256"], "--delegation-id",
              resume["DELEGATION_ID"], "--phase", resume["PHASE"], "--head", resume["HEAD"],
              "--session-nonce", N2)["code"] == "OK"
    assert tc.start("IMPLEMENT", N2)["code"] == "OK"
    # simulate a third session: write a RESUME by hand is not possible (open step), so the open step of N2 is
    # unknown to any later nonce; a step end with the old nonce N1 is refused
    assert tc.end("IMPLEMENT", "ok", N1)["code"] == "SESSION_MISMATCH"
    assert tc.end("IMPLEMENT", "ok", N2)["code"] == "OK"


@needs_git
def test_resume_requires_unchanged_state(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    repo.write("src/pkg/new.py", "changed between sessions\n")
    status = tc("status")
    resume = dict(part.split("=", 1) for part in status["resume_draft"].split()[2:])
    out = tc("record-message", "--kind", "RESUME", "--wo-sha256", resume["WO_SHA256"], "--delegation-id",
             resume["DELEGATION_ID"], "--phase", resume["PHASE"], "--head", resume["HEAD"], "--session-nonce", N2)
    assert out["code"] == "STATE_CHANGED"
    out = tc("record-message", "--kind", "RESUME", "--wo-sha256", "0" * 64, "--delegation-id",
             resume["DELEGATION_ID"], "--phase", resume["PHASE"], "--head", resume["HEAD"], "--session-nonce", N2)
    assert out["code"] == "CONTRACT_MISMATCH"


# ------------------------------------------------------------------------------------------- revoke, expiry


@needs_git
def test_revoke_refuses_changes_but_allows_reads_end_and_stop(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    assert tc.start("IMPLEMENT")["code"] == "OK"
    assert tc("revoke")["code"] == "OK"
    assert tc("revoke")["newly_revoked"] is False
    assert tc("status")["code"] == "OK" and "REVOKED" in tc("status")["blockers"]
    assert tc("check", "--read-only", "--phase", "SETUP_DONE")["status"] in ("OK", "STOP")
    assert tc.end("IMPLEMENT")["code"] == "OK"  # closing the open step of this session is allowed
    assert tc.start("TEST_TARGETED")["code"] == "REVOKED"
    assert tc.phase("LOCAL_DONE")["code"] == "REVOKED"
    assert tc.phase("TERMINAL", "--terminal-status", "STOPPED", "--code", "REVOKED")["code"] == "OK"


@needs_git
def test_expiry_refuses_changes_but_allows_reads(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    tc.now = NOW + timedelta(hours=9)
    assert tc.start("IMPLEMENT")["code"] == "EXPIRED"
    assert tc("status")["code"] == "OK"
    assert tc("verify-ledger")["code"] == "OK"
    assert tc.phase("TERMINAL", "--terminal-status", "STOPPED", "--code", "EXPIRED")["code"] == "OK"


# ------------------------------------------------------------------------------------------- budget


@needs_git
def test_budget_time_boundary(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    tc.now = NOW + timedelta(seconds=4 * 3600 - 1)
    assert tc.start("IMPLEMENT")["code"] == "OK"
    assert tc.end("IMPLEMENT")["code"] == "OK"
    tc.now = NOW + timedelta(seconds=4 * 3600)
    assert tc.start("TEST_TARGETED")["code"] == "BUDGET_TIME"


@needs_git
def test_budget_full_pytest_boundary(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    for _ in range(3):
        tc.run_step("TEST_FULL")
    assert tc.start("TEST_FULL")["code"] == "BUDGET_PYTEST"


@needs_git
def test_budget_fix_and_same_failure_boundaries(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    for n in range(5):
        tc.start("TEST_TARGETED")
        assert tc.end("TEST_TARGETED", "fail", N1, "--failure-sig", f"{n:064x}")["code"] == "OK"
        assert tc.start("IMPLEMENT")["code"] == "OK", n
        tc.end("IMPLEMENT")
    tc.start("TEST_TARGETED")
    tc.end("TEST_TARGETED", "fail", N1, "--failure-sig", "f" * 64)
    assert tc.start("IMPLEMENT")["code"] == "BUDGET_FIX"
    tc.start("LINT")
    tc.end("LINT", "fail", N1, "--failure-sig", "f" * 64)
    assert tc.start("LINT")["code"] == "BUDGET_SAME_FAIL"


@needs_git
def test_same_failure_limit_counts_only_identical_signatures(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    tc.start("TEST_TARGETED")
    tc.end("TEST_TARGETED", "fail", N1, "--failure-sig", "1" * 64)
    tc.start("LINT")
    tc.end("LINT", "fail", N1, "--failure-sig", "2" * 64)
    assert tc.start("IMPLEMENT")["code"] == "OK"


# ------------------------------------------------------------------------------------------- authority


@needs_git
def test_no_progress_without_delegate_and_copied_ledger_is_rejected(tmp_path, monkeypatch):
    repo, base, c1 = make_repo(tmp_path)
    tc = Taskctl(repo, monkeypatch)
    assert tc.phase("SETUP_DONE")["code"] == "LEDGER_MISSING"
    assert tc.init(base, c1)["code"] == "OK"
    src = repo.root / "data/processed/taskctl" / TASK
    shutil.copytree(src, repo.root / "data/processed/taskctl/PILOT-Y")
    out = M.run(["status", "--task-id", "PILOT-Y", "--repo", str(repo.root)])
    assert out["code"] == "LEDGER_TASK" and out["authority"] == "NONE"


@needs_git
def test_main_prints_one_canonical_json_line(tmp_path, monkeypatch, capsys):
    repo, base, c1 = make_repo(tmp_path)
    monkeypatch.setattr(M, "_now", lambda: NOW)
    code = M.main(["status", "--task-id", TASK, "--repo", str(repo.root)])
    out = capsys.readouterr().out
    assert out.endswith("\n") and out.count("\n") == 1
    assert json.loads(out)["code"] == "LEDGER_MISSING" and code == 3
    assert M.main(["nonsense"]) == 2


# ------------------------------------------------------------------------------------------- ERRATA-001 T1-T21
# Every repository, commit, ref and file below lives in tmp_path. Each test checks the code and the ledger.


def ledger_dir(repo: Repo) -> Path:
    return repo.root / LG.LEDGER_ROOT / TASK


def event_files(repo: Repo) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted((ledger_dir(repo) / "events").iterdir())}


def resume(tc: Taskctl, nonce: str = N2) -> dict:
    fields = dict(part.split("=", 1) for part in tc("status")["resume_draft"].split()[2:])
    return tc("record-message", "--kind", "RESUME", "--wo-sha256", fields["WO_SHA256"], "--delegation-id",
              fields["DELEGATION_ID"], "--phase", fields["PHASE"], "--head", fields["HEAD"], "--session-nonce", nonce)


def stop(tc: Taskctl, code: str) -> dict:
    return tc.phase("TERMINAL", "--terminal-status", "STOPPED", "--code", code)


@needs_git
def test_t01_setup_env_end_with_a_new_commit_is_head_mismatch(env):
    repo, base, c1, tc = env
    assert tc.init(base, c1)["code"] == "OK"
    assert tc.start("SETUP_ENV")["code"] == "OK"
    repo.write("README.md", "on top of C1\n")
    repo.commit("README.md", message="extra")
    assert tc.end("SETUP_ENV")["code"] == "HEAD_MISMATCH"


@needs_git
def test_t02_setup_env_end_with_an_allowed_new_file_is_not_clean(env):
    repo, base, c1, tc = env
    assert tc.init(base, c1)["code"] == "OK"
    assert tc.start("SETUP_ENV")["code"] == "OK"
    repo.write("src/pkg/new.py", "x = 1\n")
    assert tc.end("SETUP_ENV")["code"] == "NOT_CLEAN"


@needs_git
def test_t03_local_audit_that_changed_files_cannot_end_ok(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    tc.run_step("IMPLEMENT", lambda: implement(repo))
    assert tc.start("LOCAL_AUDIT")["code"] == "OK"
    repo.write("README.md", "changed during the audit\n")
    assert tc.end("LOCAL_AUDIT")["code"] == "STATE_CHANGED"
    assert tc.end("LOCAL_AUDIT", "fail")["code"] == "OK"


@needs_git
def test_t04_clean_e2e_with_a_changed_allowed_file_is_state_changed(env):
    repo, base, c1, tc = env
    to_committed(repo, base, c1, tc)
    assert tc.start("CLEAN_E2E")["code"] == "OK"
    repo.write("README.md", "changed during the clean check\n")
    assert tc.end("CLEAN_E2E")["code"] == "STATE_CHANGED"


@needs_git
def test_t05_clean_e2e_with_an_untracked_outside_file_is_untracked(env):
    repo, base, c1, tc = env
    to_committed(repo, base, c1, tc)
    assert tc.start("CLEAN_E2E")["code"] == "OK"
    repo.write("notes.txt", "outside ALLOWED_FILES\n")
    assert tc.end("CLEAN_E2E")["code"] == "UNTRACKED"


@needs_git
def test_t06_push_with_a_local_change_is_state_changed(env):
    repo, base, c1, tc = env
    i, _ = to_publishing(repo, base, c1, tc)
    assert tc.start("PUSH")["code"] == "OK"
    repo.write("README.md", "changed during push\n")
    assert tc.end("PUSH", "ok", N1, "--remote", f"pushed_head={i}")["code"] == "STATE_CHANGED"


@needs_git
def test_t07_merge_with_a_local_change_is_state_changed(env):
    repo, base, c1, tc = env
    i, tree = to_publishing(repo, base, c1, tc)
    merge = good_merge(repo, base, i, tree)
    remotes = publish_remotes(i, base, merge)
    run_publish(tc, remotes, ("PUSH", "PR_CREATE", "CI_WAIT", "PREMERGE_CHECK"))
    assert tc.start("MERGE")["code"] == "OK"
    repo.write("src/pkg/new.py", "x = 3\n")
    assert tc.end("MERGE", "ok", N1, *remote_args(remotes["MERGE"]))["code"] == "STATE_CHANGED"


def audit(tc: Taskctl, merge: str, tree: str) -> dict:
    assert tc.start("POST_MERGE_AUDIT")["code"] == "OK"
    return tc.end("POST_MERGE_AUDIT", "ok", N1, "--remote", f"merge_sha={merge}", "--remote",
                  f"merge_tree_recomputed={tree}")


@needs_git
def test_t08_post_merge_audit_with_origin_main_not_the_merge(env):
    repo, base, c1, tc = env
    _, tree, merge = to_merged(repo, base, c1, tc)  # origin/main stays BASE
    out = audit(tc, merge, tree)
    assert out["code"] == "PUBLISH_MISMATCH" and "origin/main" in out["detail"]


@needs_git
def test_t09_post_merge_audit_with_parents_in_the_wrong_order(env):
    repo, base, c1, tc = env

    def swapped(repo, base, i, tree):
        return repo.git("commit-tree", tree, "-p", i, "-p", base, "-m", "merge")

    _, tree, merge = to_merged(repo, base, c1, tc, swapped)
    repo.git("update-ref", "refs/remotes/origin/main", merge)
    out = audit(tc, merge, tree)
    assert out["code"] == "PUBLISH_MISMATCH" and "parents or tree" in out["detail"]


@needs_git
def test_t10_post_merge_audit_with_a_different_merge_tree(env):
    repo, base, c1, tc = env

    def base_tree_merge(repo, base, i, tree):
        return repo.git("commit-tree", repo.git("rev-parse", f"{base}^{{tree}}"), "-p", base, "-p", i, "-m", "m")

    _, tree, merge = to_merged(repo, base, c1, tc, base_tree_merge)
    repo.git("update-ref", "refs/remotes/origin/main", merge)
    out = audit(tc, merge, tree)
    assert out["code"] == "PUBLISH_MISMATCH" and "parents or tree" in out["detail"]


@needs_git
def test_t11_post_merge_audit_with_a_wrong_recomputed_tree(env):
    repo, base, c1, tc = env
    _, _, merge = to_merged(repo, base, c1, tc)
    repo.git("update-ref", "refs/remotes/origin/main", merge)
    out = audit(tc, merge, repo.git("rev-parse", f"{base}^{{tree}}"))
    assert out["code"] == "PUBLISH_MISMATCH" and "recomputed merge tree" in out["detail"]


@needs_git
def test_t12_ready_to_publish_without_pr_text(env):
    repo, base, c1, tc = env
    to_local_done(repo, base, c1, tc)
    assert tc.phase("READY_TO_PUBLISH")["code"] == "INVALID_TRANSITION"


@needs_git
def test_t13_merged_without_all_publish_steps(env):
    repo, base, c1, tc = env
    i, tree = to_publishing(repo, base, c1, tc)
    run_publish(tc, publish_remotes(i, base, good_merge(repo, base, i, tree)), ("PUSH", "PR_CREATE"))
    assert tc.phase("MERGED")["code"] == "INVALID_TRANSITION"


@needs_git
def test_t14_audited_without_post_merge_audit(env):
    repo, base, c1, tc = env
    to_merged(repo, base, c1, tc)
    assert tc.phase("AUDITED")["code"] == "INVALID_TRANSITION"


@needs_git
def test_t15_t16_t17_open_step_resume_refused_stop_keeps_it_then_terminal(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    assert tc.start("IMPLEMENT", N1)["code"] == "OK"
    before = event_files(repo)
    # T15: RESUME with an open step is refused as UNKNOWN_STEP (exit 4); the ledger does not change
    out = resume(tc, N2)
    assert out["code"] == "UNKNOWN_STEP" and out["status"] == "UNKNOWN" and M._exit_code(out) == 4
    assert event_files(repo) == before
    # T16: STOPPED is recorded as one PHASE event; the open STEP_START stays without a STEP_END
    assert stop(tc, "UNKNOWN_STEP")["code"] == "OK"
    after = event_files(repo)
    assert len(after) == len(before) + 1 and all(after[name] == data for name, data in before.items())
    events = LG.read_events(repo.root, TASK)
    last = events[-1][0]
    assert last["kind"] == "PHASE" and last["payload"] == {"from": "SETUP_DONE", "to": "TERMINAL",
                                                          "terminal_status": "STOPPED", "code": "UNKNOWN_STEP",
                                                          "violations": None}
    starts = [e for e, _, _ in events if e["kind"] == "STEP_START" and e["payload"]["step"] == "IMPLEMENT"]
    ends = [e for e, _, _ in events if e["kind"] == "STEP_END" and e["payload"]["start_seq"] == starts[-1]["seq"]]
    assert starts[-1]["payload"]["session_nonce"] == N1 and ends == []
    assert [e["kind"] for e, _, _ in events].count("RESUME") == 0  # the nonce was not replaced
    status = tc("status")
    assert status["phase"] == "TERMINAL" and status["open_step"]["step"] == "IMPLEMENT"
    # T17: after TERMINAL nothing changes the ledger
    frozen = event_files(repo)
    assert tc.end("IMPLEMENT", "ok", N1)["code"] == "TERMINAL"
    assert tc.end("IMPLEMENT", "fail", N1)["code"] == "TERMINAL"
    assert tc.start("TEST_TARGETED")["code"] == "TERMINAL"
    assert resume(tc, N2)["code"] == "TERMINAL"
    assert stop(tc, "OPERATOR_STOP")["code"] == "TERMINAL"
    assert event_files(repo) == frozen


@needs_git
def test_t18_stop_with_open_step_and_left_lease_is_lease_present(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    assert tc.start("IMPLEMENT")["code"] == "OK"
    LS.acquire(ledger_dir(repo), "STEP_START", "2026-11-16T12:00:00Z")
    lease = (ledger_dir(repo) / "LEASE").read_bytes()
    before = event_files(repo)
    assert stop(tc, "UNKNOWN_STEP")["code"] == "LEASE_PRESENT"
    assert (ledger_dir(repo) / "LEASE").read_bytes() == lease and event_files(repo) == before


@needs_git
def test_t19_stop_with_open_step_and_revoked(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    assert tc.start("IMPLEMENT")["code"] == "OK"
    assert tc("revoke")["code"] == "OK"
    assert stop(tc, "REVOKED")["code"] == "OK"
    assert tc("status")["open_step"]["step"] == "IMPLEMENT"


@needs_git
def test_t20_stop_with_open_step_after_expiry(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    assert tc.start("IMPLEMENT")["code"] == "OK"
    tc.now = NOW + timedelta(hours=9)
    assert stop(tc, "EXPIRED")["code"] == "OK"
    assert tc("status")["open_step"]["step"] == "IMPLEMENT"


@needs_git
def test_t21_stop_on_an_invalid_ledger_is_refused_without_writing(env):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    assert tc.start("IMPLEMENT")["code"] == "OK"
    (ledger_dir(repo) / "events" / "000002.json").unlink()
    before = event_files(repo)
    assert stop(tc, "UNKNOWN_STEP")["code"] == "LEDGER_GAP"
    assert event_files(repo) == before and not (ledger_dir(repo) / "LEASE").exists()


# ------------------------------------------------------------------------------------------- D6 per-step failures
# One refused end per step that had none (F-4). A refused end writes nothing: the events stay byte for byte and
# the step stays open in the current session.


def assert_refused_end(tc: Taskctl, repo: Repo, step: str, code: str, *extra: str) -> None:
    before = event_files(repo)
    out = tc.end(step, "ok", N1, *extra)
    assert out["code"] == code, out
    assert event_files(repo) == before
    open_step = tc("status")["open_step"]
    assert open_step["step"] == step and open_step["current_session"] is True


@needs_git
@pytest.mark.parametrize("step", ["TEST_FULL", "LINT", "TYPECHECK"])
def test_d6_check_step_refuses_a_changed_worktree(env, step):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    tc.run_step("IMPLEMENT", lambda: implement(repo))
    assert tc.start(step)["code"] == "OK"
    repo.write("src/pkg/new.py", "changed by a check\n")
    assert_refused_end(tc, repo, step, "STATE_CHANGED")


@needs_git
@pytest.mark.parametrize("step", ["TEST_TARGETED", "TEST_FULL", "LINT", "TYPECHECK", "LOCAL_AUDIT"])
def test_d6_check_and_audit_steps_refuse_changed_ignored_entries(env, step):
    repo, base, c1, tc = env
    to_setup_done(repo, base, c1, tc)
    tc.run_step("IMPLEMENT", lambda: implement(repo))
    assert tc.start(step)["code"] == "OK"
    repo.write("data/processed/other/out.json", "{}")  # an ignored entry outside the ledger
    assert_refused_end(tc, repo, step, "STATE_CHANGED")


@needs_git
@pytest.mark.parametrize("step", ["PR_CREATE", "CI_WAIT", "PREMERGE_CHECK"])
def test_d6_publish_step_refuses_a_local_change(env, step):
    repo, base, c1, tc = env
    i, tree = to_publishing(repo, base, c1, tc)
    remotes = publish_remotes(i, base, good_merge(repo, base, i, tree))
    order = ("PUSH", "PR_CREATE", "CI_WAIT", "PREMERGE_CHECK")
    run_publish(tc, remotes, order[:order.index(step)])
    assert tc.start(step)["code"] == "OK"
    repo.write("README.md", f"changed during {step}\n")
    assert_refused_end(tc, repo, step, "STATE_CHANGED", *remote_args(remotes[step]))


@needs_git
def test_d6_ci_wait_refuses_another_head_and_a_failed_conclusion(env):
    repo, base, c1, tc = env
    i, tree = to_publishing(repo, base, c1, tc)
    remotes = publish_remotes(i, base, good_merge(repo, base, i, tree))
    run_publish(tc, remotes, ("PUSH", "PR_CREATE"))
    assert tc.start("CI_WAIT")["code"] == "OK"
    assert_refused_end(tc, repo, "CI_WAIT", "PUBLISH_MISMATCH",
                       *remote_args(["run_id=9", f"run_head_sha={c1}", "required_conclusion=success"]))
    assert_refused_end(tc, repo, "CI_WAIT", "PUBLISH_MISMATCH",
                       *remote_args(["run_id=9", f"run_head_sha={i}", "required_conclusion=failure"]))
    assert tc.end("CI_WAIT", "ok", N1, *remote_args(remotes["CI_WAIT"]))["code"] == "OK"


# ------------------------------------------------------------------------------------------- D6 transition conditions


@needs_git
def test_setup_done_requires_the_state_of_the_setup_env_end(env):
    repo, base, c1, tc = env
    assert tc.init(base, c1)["code"] == "OK"
    tc.run_step("SETUP_ENV", lambda: (repo.root / ".venv").mkdir())
    repo.write("src/pkg/new.py", "after SETUP_ENV\n")
    before = event_files(repo)
    assert tc.phase("SETUP_DONE")["code"] == "INVALID_TRANSITION"
    assert event_files(repo) == before


@needs_git
def test_ready_to_publish_requires_a_clean_implementation_commit(env):
    repo, base, c1, tc = env
    to_local_done(repo, base, c1, tc)
    assert tc("pr-text", "--sha256", sha(PR_BODY), stdin=PR_BODY)["code"] == "OK"
    repo.write("README.md", "dirty after the commit\n")
    before = event_files(repo)
    assert tc.phase("READY_TO_PUBLISH")["code"] == "INVALID_TRANSITION"
    assert event_files(repo) == before


@needs_git
def test_audited_to_closed_with_violation_needs_at_least_one_violation(env):
    repo, base, c1, tc = env
    _, tree, merge = to_merged(repo, base, c1, tc)
    repo.git("update-ref", "refs/remotes/origin/main", merge)
    assert audit(tc, merge, tree)["code"] == "OK"
    assert tc.phase("AUDITED")["code"] == "OK"
    before = event_files(repo)
    assert tc.phase("TERMINAL", "--terminal-status", "CLOSED_WITH_VIOLATION", "--violations", "0")["code"] == \
        "INVALID_TRANSITION"
    assert event_files(repo) == before
    assert tc.phase("TERMINAL", "--terminal-status", "CLOSED_WITH_VIOLATION", "--violations", "1")["code"] == "OK"
    last = LG.read_events(repo.root, TASK)[-1][0]
    assert last["payload"] == {"from": "AUDITED", "to": "TERMINAL", "terminal_status": "CLOSED_WITH_VIOLATION",
                               "code": None, "violations": 1}
