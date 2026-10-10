"""Repository hygiene: frozen study files, test locks, raw data and what git may track.

Read-only against the real repository. The detectors themselves are exercised on temporary files
and a temporary git repository, never on the protected files.

Two layers are checked separately, because .gitignore cannot protect a file that is already tracked:
  tracking  - what git tracks or could add (forbidden paths, secrets, hidden-change flags)
  content   - the bytes of the frozen files, against pinned hashes and every run manifest

Local-only checks (data/ is git-ignored, so CI has none) skip when the data is absent.
"""

import fnmatch
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "data" / "processed" / "research"

# sha256 of the committed (LF) content. Changing a frozen file starts a new study: never edit these
# pins to make a test pass. The v0.5 DRAFT pin changes only together with an approved draft edit.
PINNED_BLOB = {
    "configs/research_v04.toml": "83866d83ae2247f9c94c4682e24ce9dc15d9db4208fedab06c26e137f824af1a",
    "docs/research_v04_preregistration.md": "6e6045e87fd6a82534dee7641bd2aa9b6ff89e9e3ac7605d5d7b0b7116139cfa",
    "docs/research_v05_preregistration_draft.md": "33e57a265acf5cd995773c0b2bfeaa260405385e5cdd4566673f80cf456fa17b",
}
# sha256 of the exact working-tree bytes (CRLF checkout) that every v0.4 run manifest records and
# that research-final compares against.
PINNED_WORKTREE = {
    "configs/research_v04.toml": "c16b22a3fe820e0f234e0c04e9ceff135cfeabb941519c6b44d47eb18229cd5f",
    "docs/research_v04_preregistration.md": "f86792c0ffa95b9f39b9f707c07b991f4a2795c87d8a7409e4aadcf84f181e74",
}
V04_RESEARCH_RUN = "session_20261009T2206KST__20261010T062347Z"  # test split never opened

FORBIDDEN_TRACKED = [
    "data/*", ".env", ".env.*", "*.bak", "*.orig", "*.backup", "*.rej", "*.reg", "*.swp", "*~", "*.log",
    "*.tmp", ".claude/settings.local.json", "*.pem", "*.key", "*.sqlite", "*.sqlite3", "*.db",
    "*.jsonl", "*.jsonl.gz", "*.parquet", "*keystore*", "*wallet*.json", "secrets/*",
]
ALLOWED_TRACKED = {"data/raw/.gitkeep", "data/processed/.gitkeep", ".env.example"}
MAX_TRACKED_BYTES = 1_000_000

SECRET_PATTERNS = [
    ("private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("aws access key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("github token", r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    ("slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("anthropic/openai key", r"\bsk-(ant-)?[A-Za-z0-9_-]{20,}"),
    ("jwt", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ("assigned secret", r"(?i)[a-z0-9_]*(secret|api[_-]?key|access[_-]?key|token|password|passwd)[a-z0-9_]*"
                        r"\s*[:=]\s*['\"][A-Za-z0-9/+_.=-]{16,}['\"]"),
    ("personal email", r"[\w.+-]+@(gmail|naver|daum|hanmail|kakao|outlook|hotmail|yahoo)\.[a-z.]+"),
    ("user home path", r"(?i)\b[a-z]:[\\/]+users[\\/]+[^\\/\s'\"]+"),
]
SCAN_EXCLUDE = {"tests/test_repo_hygiene.py"}  # holds the patterns themselves


# ------------------------------------------------------------------------------------------ helpers


def git(*args, repo: Path = REPO, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=check)


def _has_git(repo: Path = REPO) -> bool:
    try:
        return git("rev-parse", "--is-inside-work-tree", repo=repo, check=False).returncode == 0
    except OSError:
        return False


needs_git = pytest.mark.skipif(not _has_git(), reason="not a git work tree")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def forbidden_reason(path: str) -> str | None:
    """Why `path` (repo-relative, '/' separators) must not be tracked, or None."""
    if path in ALLOWED_TRACKED:
        return None
    name = path.rsplit("/", 1)[-1]
    for pattern in FORBIDDEN_TRACKED:
        if fnmatch.fnmatchcase(path, pattern) or ("/" not in pattern and fnmatch.fnmatchcase(name, pattern)):
            return pattern
    return None


def secret_hits(text: str) -> list[str]:
    return [label for label, pattern in SECRET_PATTERNS if re.search(pattern, text)]


def hidden_change_flags(repo: Path, paths) -> dict[str, str]:
    """Tracked paths whose changes git would hide: assume-unchanged (lower-case tag) or skip-worktree (S)."""
    out = git("ls-files", "-v", "--", *paths, repo=repo).stdout.decode()
    flags = {}
    for line in out.splitlines():
        tag, path = line[0], line[2:]
        if tag.islower() or tag == "S":
            flags[path] = tag
    return flags


def modified_against_head(repo: Path, path: str) -> bool:
    return git("diff", "--quiet", "HEAD", "--", path, repo=repo, check=False).returncode != 0


def line_ending_only_difference(data: bytes, expected_lf_sha: str) -> bool:
    return sha256_bytes(data.replace(b"\r\n", b"\n")) == expected_lf_sha


def addable_files() -> list[str]:
    """Tracked files plus untracked files that `git add` would pick up (not ignored)."""
    tracked = git("ls-files", "-z").stdout.decode().split("\0")
    others = git("ls-files", "-z", "--others", "--exclude-standard").stdout.decode().split("\0")
    return [p for p in tracked + others if p]


def run_manifests() -> list[tuple[Path, dict]]:
    if not RUNS.is_dir():
        return []
    return [(m.parent, json.loads(m.read_text(encoding="utf-8"))) for m in sorted(RUNS.glob("*/manifest.json"))]


needs_runs = pytest.mark.skipif(not run_manifests(), reason="no local research runs (data/ is git-ignored)")


# ------------------------------------------------------------------- detectors on temporary fixtures


@pytest.mark.parametrize("path, bad", [
    ("data/raw/upbit/x/segments/1.jsonl.gz", True), ("data/processed/research/r/manifest.json", True),
    ("data/raw/.gitkeep", False), (".env", True), (".env.local", True), (".env.example", False),
    ("docs/x.md.bak", True), ("backup.reg", True), ("notes.orig", True), (".claude/settings.local.json", True),
    ("logs/run.log", True), ("src/moneylab/cli.py", False), (".claude/settings.json", False),
    ("tests/fixtures/upbit_ws_timeline_synthetic.json", False), ("keys/id.pem", True),
])
def test_forbidden_reason_detector(path, bad):
    assert (forbidden_reason(path) is not None) == bad


@pytest.mark.parametrize("text, bad", [
    ("api_key = 'AbCdEfGhIjKlMnOpQrStUv'", True), ("UPBIT_SECRET_KEY: \"abcdefghijklmnop1234\"", True),
    ("-----BEGIN RSA PRIVATE KEY-----", True), ("token=ghp_" + "a" * 36, True), ("mail me: someone@gmail.com", True),
    ("path C:\\Users\\alice\\x", True), ("api_key = os.environ['UPBIT_KEY']", False),
    ("noreply@anthropic.com", False), ("bootstrap_seed = 20261006", False), ("C:\\MoneyLab\\.venv", False),
])
def test_secret_detector(text, bad):
    assert bool(secret_hits(text)) == bad


def test_line_ending_diagnosis(tmp_path):
    lf = b"a = 1\nb = 2\n"
    f = tmp_path / "x.toml"
    f.write_bytes(lf.replace(b"\n", b"\r\n"))
    assert sha256_path(f) != sha256_bytes(lf)
    assert line_ending_only_difference(f.read_bytes(), sha256_bytes(lf))
    f.write_bytes(b"a = 1\r\nb = 3\r\n")
    assert not line_ending_only_difference(f.read_bytes(), sha256_bytes(lf))


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_tracking_checks_on_temporary_repo(tmp_path):
    """.gitignore does not protect a tracked file; the diff and flag checks do."""
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (("init", "-q"), ("config", "user.email", "t@example.invalid"), ("config", "user.name", "t"),
                 ("config", "core.autocrlf", "false")):
        git(*args, repo=repo)
    (repo / "frozen.toml").write_text("x = 1\n", encoding="utf-8")
    git("add", "frozen.toml", repo=repo)
    git("commit", "-q", "-m", "init", repo=repo)
    (repo / ".gitignore").write_text("frozen.toml\n", encoding="utf-8")  # ignoring a tracked file changes nothing
    assert not modified_against_head(repo, "frozen.toml")
    (repo / "frozen.toml").write_text("x = 2\n", encoding="utf-8")
    assert modified_against_head(repo, "frozen.toml")
    git("update-index", "--assume-unchanged", "frozen.toml", repo=repo)
    assert git("status", "--porcelain", "--", "frozen.toml", repo=repo).stdout == b""  # git now hides it
    assert hidden_change_flags(repo, ["frozen.toml"]) == {"frozen.toml": "h"}
    git("update-index", "--no-assume-unchanged", "frozen.toml", repo=repo)
    git("update-index", "--skip-worktree", "frozen.toml", repo=repo)
    assert hidden_change_flags(repo, ["frozen.toml"]) == {"frozen.toml": "S"}


# ---------------------------------------------------------------- frozen study files (real repo)


@needs_git
@pytest.mark.parametrize("path", sorted(PINNED_BLOB))
def test_frozen_files_tracked_unmodified_and_not_hidden(path):
    assert git("ls-files", "--error-unmatch", "--", path, check=False).returncode == 0, f"{path} is not tracked"
    assert hidden_change_flags(REPO, [path]) == {}, f"{path} has assume-unchanged/skip-worktree set"
    assert not modified_against_head(REPO, path), f"{path} differs from HEAD"


@needs_git
@pytest.mark.parametrize("path", sorted(PINNED_BLOB))
def test_frozen_committed_content_is_pinned(path):
    blob = git("show", f"HEAD:{path}").stdout
    assert sha256_bytes(blob) == PINNED_BLOB[path], f"committed {path} changed: a change is a new study"


@pytest.mark.parametrize("path", sorted(PINNED_WORKTREE))
def test_frozen_worktree_bytes_match_recorded_hash(path):
    data = (REPO / path).read_bytes()
    if sha256_bytes(data) == PINNED_WORKTREE[path]:
        return
    if line_ending_only_difference(data, PINNED_BLOB[path]):
        pytest.fail(f"{path}: only line endings differ from the hash the v0.4 runs recorded; research-final "
                    "would refuse. Check out with core.autocrlf=true (CRLF) instead of changing anything.")
    pytest.fail(f"{path}: content differs from the frozen v0.4 study")


@needs_git
@pytest.mark.parametrize("path", sorted(PINNED_WORKTREE))
def test_frozen_files_check_out_with_crlf_everywhere(path):
    """Without eol=crlf a core.autocrlf=false clone gets LF bytes and research-final would refuse."""
    out = git("check-attr", "text", "eol", "--", path).stdout.decode()
    assert f"{path}: eol: crlf" in out and f"{path}: text: set" in out, out


# ------------------------------------------------------------- run manifests, test locks, raw data


@needs_runs
def test_run_manifests_match_current_study_files():
    prereg = sha256_path(REPO / "docs/research_v04_preregistration.md")
    config = sha256_path(REPO / "configs/research_v04.toml")
    for run, m in run_manifests():
        assert m["preregistration_sha256"] == prereg, run.name
        assert m["config_sha256"] == config, run.name


@needs_runs
def test_locked_test_splits_match_manifest_and_stay_unopened():
    """Hashes the locked files' bytes only; the rows are never decoded."""
    for run, m in run_manifests():
        outputs = m["outputs"]
        assert sha256_path(run / outputs["test_file"]) == outputs["test_sha256"], run.name
        assert sha256_path(run / outputs["trainval_file"]) == outputs["trainval_sha256"], run.name
        assert isinstance(m.get("test_access_count"), int), run.name
    research = dict((r.name, m) for r, m in run_manifests())
    if V04_RESEARCH_RUN in research:
        assert research[V04_RESEARCH_RUN]["test_access_count"] == 0


@needs_runs
def test_raw_datasets_match_recorded_raw_manifest():
    from moneylab.providers.upbit.research_export import raw_manifest

    current: dict[Path, str] = {}  # several runs share one dataset; hash it once
    for run, m in run_manifests():
        dataset = REPO / m["source"]["raw_dataset"].replace("\\", "/")
        if not dataset.is_dir():
            continue
        recorded = m["source"]["raw_manifest_sha256"]
        if dataset not in current:
            current[dataset] = raw_manifest(dataset)["manifest_sha256"]
        assert current[dataset] == recorded, f"raw data of {run.name} changed"
        capture = json.loads((dataset / "capture_manifest.json").read_text(encoding="utf-8"))
        if capture.get("raw_manifest_sha256"):
            assert capture["raw_manifest_sha256"] == recorded, run.name


# ------------------------------------------------------------------------ what git tracks or adds


@needs_git
def test_no_forbidden_or_large_tracked_files():
    tracked = [p for p in git("ls-files", "-z").stdout.decode().split("\0") if p]
    bad = {p: forbidden_reason(p) for p in tracked if forbidden_reason(p)}
    assert not bad, f"forbidden tracked files: {bad}"
    large = {p: (REPO / p).stat().st_size for p in tracked
             if (REPO / p).is_file() and (REPO / p).stat().st_size > MAX_TRACKED_BYTES}
    assert not large, f"tracked files over {MAX_TRACKED_BYTES} bytes: {large}"


@needs_git
def test_no_forbidden_untracked_files_that_git_add_would_pick_up():
    others = [p for p in git("ls-files", "-z", "--others", "--exclude-standard").stdout.decode().split("\0") if p]
    bad = {p: forbidden_reason(p) for p in others if forbidden_reason(p)}
    assert not bad, f"not ignored and would be added by `git add`: {bad}"


@needs_git
@pytest.mark.parametrize("path, ignored", [
    ("data/raw/upbit/research/s/KRW-BTC/state.json", True), ("data/processed/research/r/manifest.json", True),
    ("data/raw/.gitkeep", False), ("data/processed/.gitkeep", False),
    (".env", True), (".env.local", True), (".env.example", False),
    (".claude/settings.local.json", True), (".claude/settings.json", False), (".claude/hooks/guard.py", False),
    ("docs/notes.md.bak", True), ("x.orig", True), ("w32time_backup.reg", True), ("y.backup", True),
    ("logs/recorder.log", True), ("keys/a.pem", True),
])
def test_gitignore_rules(path, ignored):
    r = git("check-ignore", "-q", "--no-index", "--", path, check=False)
    assert (r.returncode == 0) == ignored, f"{path}: expected ignored={ignored}"


@needs_git
def test_no_secrets_or_personal_data_in_addable_files():
    hits = {}
    for p in addable_files():
        if p in SCAN_EXCLUDE:
            continue
        f = REPO / p
        if not f.is_file() or f.stat().st_size > MAX_TRACKED_BYTES:
            continue
        data = f.read_bytes()
        if b"\0" in data:
            continue
        found = secret_hits(data.decode("utf-8", errors="ignore"))
        if found:
            hits[p] = found
    assert not hits, f"possible secrets or personal data: {hits}"
