"""Single-command lease, REVOKED marker and PR text of taskctl (GOV-AUTOMATION-03 D4-D5).

A state-changing command creates LEASE with create-new, verifies the ledger, writes one event and then
deletes LEASE only if it still holds its own lease_id. Creation races are decided by the hard link of
`atomic_create_new_bytes`: the second creator fails with FileExistsError. There is no TTL, renewal or
automatic reclaim. A LEASE left by an interrupted command stops every state change until the user sends
CLEAR_LEASE; its presence says nothing about whether the owner is alive.

D4 (ERRATA-001 F-3): LEASE, REVOKED and pr_text.md are inspected with lstat before every read or write. A link,
a junction or another reparse point there, broken or not, and any non-regular entry is PATH_INVALID; it is never
followed and never taken for an absent file. The parent chain is checked by the caller (`check_dir`,
`read_events`). A change between the check and the use is not prevented.
"""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

from moneylab.taskctl.ledger import (
    CONCURRENT,
    INVALID,
    IO_ERROR,
    PATH_INVALID,
    TaskctlError,
    create_new,
    is_code,
    is_hex32,
    is_utc,
    sha256_hex,
)
from moneylab.workstate.collect import WorkstateError, check_tree_path

LEASE_SCHEMA = "moneylab.taskctl.lease/1"
REVOKED_SCHEMA = "moneylab.taskctl.revoked/1"
MAX_MARKER_BYTES = 256
MAX_PR_TEXT_BYTES = 64 * 1024

LEASE_PRESENT = "LEASE_PRESENT"
LEASE_NOT_OWNER = "LEASE_NOT_OWNER"
LEASE_MISMATCH = "LEASE_MISMATCH"
LEASE_ABSENT = "LEASE_ABSENT"
PR_TEXT_EXISTS = "PR_TEXT_EXISTS"


def _marker(payload: dict[str, Any]) -> bytes:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    if len(data) > MAX_MARKER_BYTES:
        raise TaskctlError(INVALID, "marker too large")
    return data


def present(directory: Path, name: str) -> bool:
    """True for a regular file `name` in `directory`, False when nothing is there. Links, junctions, reparse
    points (broken ones too) and other entries raise PATH_INVALID."""
    try:
        return check_tree_path(Path(directory), name, PATH_INVALID, require_regular=True) is not None
    except WorkstateError as exc:
        raise TaskctlError(PATH_INVALID, exc.detail) from exc


def read_lease(directory: Path) -> dict[str, Any] | None:
    path = directory / "LEASE"
    if not present(directory, "LEASE"):
        return None
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise TaskctlError(IO_ERROR, f"LEASE could not be read: {type(exc).__name__}") from exc
    try:
        lease = json.loads(raw.decode("ascii")) if len(raw) <= MAX_MARKER_BYTES else None
    except (UnicodeDecodeError, ValueError):
        lease = None
    if (not isinstance(lease, dict) or set(lease) != {"schema", "lease_id", "utc", "command"}
            or lease["schema"] != LEASE_SCHEMA or not is_hex32(lease["lease_id"]) or not is_utc(lease["utc"])
            or not is_code(lease["command"])):
        return {"schema": "UNREADABLE", "lease_id": None}
    return lease


def acquire(directory: Path, command: str, utc: str) -> str:
    """Create LEASE. An existing LEASE (left behind or held by another command) is LEASE_PRESENT."""
    if present(directory, "LEASE"):
        raise TaskctlError(LEASE_PRESENT, "a LEASE exists; whether its owner is alive is unknown")
    lease_id = secrets.token_hex(16)
    data = _marker({"schema": LEASE_SCHEMA, "lease_id": lease_id, "utc": utc, "command": command})
    try:
        create_new(directory / "LEASE", data, "LEASE")
    except TaskctlError as exc:
        if exc.code == CONCURRENT:
            raise TaskctlError(LEASE_PRESENT, "a LEASE exists; whether its owner is alive is unknown") from exc
        raise
    return lease_id


def release(directory: Path, lease_id: str) -> None:
    """Delete LEASE only when it still holds `lease_id`."""
    lease = read_lease(directory)
    if lease is None or lease.get("lease_id") != lease_id:
        raise TaskctlError(LEASE_NOT_OWNER, "LEASE is not held by this command")
    try:
        os.unlink(directory / "LEASE")
    except OSError as exc:
        raise TaskctlError(IO_ERROR, f"LEASE could not be deleted: {type(exc).__name__}") from exc


def delete_cleared(directory: Path, lease_id: str) -> None:
    """lease-clear: delete the LEASE whose id the user named in CLEAR_LEASE (after LEASE_CLEARED is written)."""
    release(directory, lease_id)


def revoked(directory: Path) -> bool:
    return present(directory, "REVOKED")


def write_revoked(directory: Path, utc: str) -> bool:
    """Create the REVOKED marker. Returns False when it already existed. taskctl never deletes it."""
    if present(directory, "REVOKED"):
        return False
    try:
        create_new(directory / "REVOKED", _marker({"schema": REVOKED_SCHEMA, "utc": utc}), "REVOKED")
    except TaskctlError as exc:
        if exc.code == CONCURRENT:
            return False
        raise
    return True


def check_pr_text(data: bytes, expected_sha256: str) -> None:
    if len(data) > MAX_PR_TEXT_BYTES or b"\r" in data:
        raise TaskctlError(INVALID, "PR text must be LF-only and at most 64 KiB")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TaskctlError(INVALID, "PR text is not UTF-8") from exc
    if sha256_hex(data) != expected_sha256:
        raise TaskctlError(INVALID, "PR text hash does not match --sha256")


def write_pr_text(directory: Path, data: bytes) -> None:
    if present(directory, "pr_text.md"):
        raise TaskctlError(PR_TEXT_EXISTS, "pr_text.md already exists and is never replaced")
    try:
        create_new(directory / "pr_text.md", data, "pr_text.md")
    except TaskctlError as exc:
        if exc.code == CONCURRENT:
            raise TaskctlError(PR_TEXT_EXISTS, "pr_text.md already exists and is never replaced") from exc
        raise


def read_pr_text_sha256(directory: Path) -> str | None:
    if not present(directory, "pr_text.md"):
        return None
    try:
        return sha256_hex((directory / "pr_text.md").read_bytes())
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise TaskctlError(IO_ERROR, f"pr_text.md could not be read: {type(exc).__name__}") from exc
