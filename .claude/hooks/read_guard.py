#!/usr/bin/env python3
"""
read_guard.py — Claude Code PreToolUse hook for Read calls.

Enforces token minimization by tracking which files have been read this session
and blocking redundant re-reads of unchanged files.

Exit codes (Claude Code hook contract):
  0 = allow the tool call
  2 = block the tool call (Claude Code will not execute it)
  1 = hard error (avoided — always exit 0 or 2)

Receives JSON on stdin:
  {"tool_name": "Read", "tool_input": {"file_path": "/abs/path"}}

Environment:
  READ_GUARD_LOG — override log file path (used by tests for isolation)
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LOG = os.path.join(PROJECT_ROOT, ".claude", "hooks", "session_reads.json")
LOG_PATH = os.environ.get("READ_GUARD_LOG", DEFAULT_LOG)

# Allow a file to be re-read this many times before blocking.
# 1 = allow first read, warn on second, block on third+
WARN_THRESHOLD = 1
BLOCK_THRESHOLD = 2

# How many blocked reads before emitting a DRIFT-ALERT
DRIFT_ALERT_THRESHOLD = 3


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _file_hash(path: str) -> str:
    """Return a short content hash for path. Uses git hash-object if available,
    falls back to SHA-256 of file bytes. Returns 'UNTRACKED' if file unreadable."""
    try:
        result = subprocess.run(
            ["git", "hash-object", path],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()[:16]
    except Exception:
        pass
    # Fallback: Python hash
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return "UNTRACKED"


def _load_log() -> dict:
    try:
        with open(LOG_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "session_start": _now(),
            "reads": {},
            "blocked_count": 0,
            "drift_score": 0,
            "drift_alert": False,
        }


def _save_log(log: dict) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


def _warn(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Unparseable input — allow and move on
        return 0

    tool_name = data.get("tool_name", "")
    if tool_name != "Read":
        # Only guard Read calls — zero overhead for everything else
        return 0

    tool_input = data.get("tool_input", {})
    path = tool_input.get("file_path", "")
    if not path:
        return 0

    # Resolve to absolute path
    path = os.path.abspath(path)

    log = _load_log()
    current_hash = _file_hash(path)
    reads = log["reads"]
    rel = os.path.relpath(path, PROJECT_ROOT)

    if path not in reads:
        # First read — allow and log
        reads[path] = {
            "hash": current_hash,
            "read_count": 1,
            "first_read": _now(),
            "last_read": _now(),
        }
        _save_log(log)
        return 0

    entry = reads[path]

    if entry["hash"] != current_hash:
        # File changed since last read — reset and allow
        entry["hash"] = current_hash
        entry["read_count"] = 1
        entry["last_read"] = _now()
        _save_log(log)
        return 0

    # Same file, same hash — check thresholds
    entry["read_count"] += 1
    entry["last_read"] = _now()

    if entry["read_count"] <= BLOCK_THRESHOLD:
        # Warn but allow (second read)
        _warn(
            f"[READ-GUARD WARN] {rel} — already read this session (hash unchanged). "
            f"Use cached context instead of re-reading."
        )
        _save_log(log)
        return 0

    # Block (third+ read of same unchanged file)
    log["blocked_count"] += 1
    log["drift_score"] = log["blocked_count"]

    if log["blocked_count"] >= DRIFT_ALERT_THRESHOLD and not log["drift_alert"]:
        log["drift_alert"] = True
        _warn(
            f"[READ-GUARD DRIFT-ALERT] Drift score: {log['drift_score']}. "
            f"AUTOMATIC REORIENTATION REQUIRED. Run /reorient before continuing."
        )

    _warn(
        f"[READ-GUARD BLOCK] {rel} — read {entry['read_count']} times, hash unchanged. "
        f"BLOCKED. Drift score: {log['drift_score']}. "
        f"{'Run /reorient now.' if log['drift_alert'] else 'Use context you already have.'}"
    )

    _save_log(log)
    return 2


if __name__ == "__main__":
    sys.exit(main())
