"""
test_token_efficiency.py

Verifies that read_guard.py enforces token-minimization rules correctly.
No Django, no Overpass, no server — pure subprocess + filesystem tests.
Target runtime: < 2 seconds.

All tests set READ_GUARD_LOG to an isolated temp file so the real
session_reads.json in the project is never touched.
"""

import json
import os
import subprocess
import sys
import tempfile
import time

import pytest

GUARD = os.path.join(
    os.path.dirname(__file__), "..", ".claude", "hooks", "read_guard.py"
)
GUARD = os.path.abspath(GUARD)


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def log_path(tmp_path):
    """Isolated log file for each test. Never touches the real session_reads.json."""
    return str(tmp_path / "session_reads.json")


@pytest.fixture
def tmp_file(tmp_path):
    """A temp file with known content for hash-change tests."""
    p = tmp_path / "subject.py"
    p.write_text("# version 1\n")
    return str(p)


def _call(tool_name, file_path, log_path):
    """Invoke read_guard.py and return (exit_code, stderr_text)."""
    payload = json.dumps({"tool_name": tool_name, "tool_input": {"file_path": file_path}})
    env = {**os.environ, "READ_GUARD_LOG": log_path}
    result = subprocess.run(
        [sys.executable, GUARD],
        input=payload, text=True, capture_output=True, env=env,
    )
    return result.returncode, result.stderr


def _load(log_path):
    with open(log_path) as f:
        return json.load(f)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestFirstRead:
    def test_allowed(self, log_path, tmp_file):
        """TC-1: First read is always allowed (exit 0)."""
        code, _ = _call("Read", tmp_file, log_path)
        assert code == 0

    def test_log_created(self, log_path, tmp_file):
        """TC-1: Log file is created on first read."""
        assert not os.path.exists(log_path)
        _call("Read", tmp_file, log_path)
        assert os.path.exists(log_path)

    def test_read_count_is_one(self, log_path, tmp_file):
        """TC-1: read_count starts at 1."""
        _call("Read", tmp_file, log_path)
        log = _load(log_path)
        assert log["reads"][tmp_file]["read_count"] == 1

    def test_no_warning_on_first_read(self, log_path, tmp_file):
        """TC-1: No warning emitted on the first read."""
        _, stderr = _call("Read", tmp_file, log_path)
        assert "READ-GUARD" not in stderr


class TestSecondRead:
    def test_allowed(self, log_path, tmp_file):
        """TC-2: Second read of same unchanged file is allowed."""
        _call("Read", tmp_file, log_path)
        code, _ = _call("Read", tmp_file, log_path)
        assert code == 0

    def test_warn_emitted(self, log_path, tmp_file):
        """TC-2: WARN is emitted on second read."""
        _call("Read", tmp_file, log_path)
        _, stderr = _call("Read", tmp_file, log_path)
        assert "READ-GUARD WARN" in stderr

    def test_read_count_is_two(self, log_path, tmp_file):
        """TC-2: read_count incremented to 2."""
        _call("Read", tmp_file, log_path)
        _call("Read", tmp_file, log_path)
        log = _load(log_path)
        assert log["reads"][tmp_file]["read_count"] == 2


class TestThirdRead:
    def test_blocked(self, log_path, tmp_file):
        """TC-3: Third read of same unchanged file is blocked (exit 2)."""
        _call("Read", tmp_file, log_path)
        _call("Read", tmp_file, log_path)
        code, _ = _call("Read", tmp_file, log_path)
        assert code == 2

    def test_block_message_in_stderr(self, log_path, tmp_file):
        """TC-3: BLOCK message appears in stderr."""
        _call("Read", tmp_file, log_path)
        _call("Read", tmp_file, log_path)
        _, stderr = _call("Read", tmp_file, log_path)
        assert "READ-GUARD BLOCK" in stderr

    def test_blocked_count_increments(self, log_path, tmp_file):
        """TC-3: blocked_count increments on each blocked read."""
        _call("Read", tmp_file, log_path)
        _call("Read", tmp_file, log_path)
        _call("Read", tmp_file, log_path)
        log = _load(log_path)
        assert log["blocked_count"] == 1

    def test_fourth_read_still_blocked(self, log_path, tmp_file):
        """TC-3: Blocking persists on subsequent reads."""
        for _ in range(4):
            _call("Read", tmp_file, log_path)
        code, _ = _call("Read", tmp_file, log_path)
        assert code == 2


class TestHashChange:
    def test_reread_after_change_allowed(self, log_path, tmp_file):
        """TC-4: Re-read is allowed after file content changes."""
        _call("Read", tmp_file, log_path)
        _call("Read", tmp_file, log_path)  # second read (warn)
        # Mutate the file so its hash changes
        with open(tmp_file, "a") as f:
            f.write("# version 2\n")
        code, _ = _call("Read", tmp_file, log_path)
        assert code == 0

    def test_count_resets_after_change(self, log_path, tmp_file):
        """TC-4: read_count resets to 1 after hash change."""
        _call("Read", tmp_file, log_path)
        _call("Read", tmp_file, log_path)
        with open(tmp_file, "a") as f:
            f.write("# changed\n")
        _call("Read", tmp_file, log_path)
        log = _load(log_path)
        assert log["reads"][tmp_file]["read_count"] == 1

    def test_new_hash_stored(self, log_path, tmp_file):
        """TC-4: The updated hash is stored after a legitimate re-read."""
        _call("Read", tmp_file, log_path)
        old_hash = _load(log_path)["reads"][tmp_file]["hash"]
        with open(tmp_file, "w") as f:
            f.write("# completely different\n")
        _call("Read", tmp_file, log_path)
        new_hash = _load(log_path)["reads"][tmp_file]["hash"]
        assert new_hash != old_hash


class TestNonReadPassthrough:
    def test_bash_always_allowed(self, log_path, tmp_file):
        """TC-5: Bash tool calls always exit 0 and never touch the log."""
        code, stderr = _call("Bash", tmp_file, log_path)
        assert code == 0
        assert "READ-GUARD" not in stderr

    def test_bash_does_not_create_log(self, log_path, tmp_file):
        """TC-5: Log file is NOT created for non-Read tools."""
        _call("Bash", tmp_file, log_path)
        assert not os.path.exists(log_path)

    def test_edit_passthrough(self, log_path, tmp_file):
        """TC-5: Edit tool calls are always allowed."""
        code, _ = _call("Edit", tmp_file, log_path)
        assert code == 0


class TestDriftAlert:
    def test_drift_alert_triggers_at_threshold(self, log_path, tmp_file, tmp_path):
        """TC-6: drift_alert flips to True after DRIFT_ALERT_THRESHOLD blocks."""
        # Need 3 different files to get 3 independent blocked reads
        files = []
        for i in range(3):
            p = tmp_path / f"file_{i}.py"
            p.write_text(f"# file {i}\n")
            files.append(str(p))

        # For each file: read twice (to reach block threshold), then read a third time (block)
        for fp in files:
            _call("Read", fp, log_path)  # first read — allowed
            _call("Read", fp, log_path)  # second — warn
            _call("Read", fp, log_path)  # third — blocked, increments blocked_count

        log = _load(log_path)
        assert log["drift_alert"] is True

    def test_drift_alert_message_in_stderr(self, log_path, tmp_path):
        """TC-6: DRIFT-ALERT message appears in stderr when threshold is crossed."""
        files = []
        for i in range(3):
            p = tmp_path / f"da_{i}.py"
            p.write_text(f"# {i}\n")
            files.append(str(p))

        stderr_output = ""
        for fp in files:
            _call("Read", fp, log_path)
            _call("Read", fp, log_path)
            _, stderr = _call("Read", fp, log_path)
            stderr_output += stderr

        assert "READ-GUARD DRIFT-ALERT" in stderr_output

    def test_drift_alert_only_emitted_once(self, log_path, tmp_path):
        """TC-6: DRIFT-ALERT is not re-emitted on subsequent blocks after flag is set."""
        files = []
        for i in range(4):
            p = tmp_path / f"once_{i}.py"
            p.write_text(f"# {i}\n")
            files.append(str(p))

        # Trigger 3 blocks to set drift_alert
        for fp in files[:3]:
            for _ in range(3):
                _call("Read", fp, log_path)

        # 4th block — alert already set, should not re-emit
        for _ in range(3):
            _call("Read", files[3], log_path)
        _, stderr = _call("Read", files[3], log_path)

        assert "READ-GUARD DRIFT-ALERT" not in stderr


class TestEdgeCases:
    def test_missing_file_allowed(self, log_path):
        """TC-7: Non-existent file path exits 0 (guard never crashes)."""
        code, stderr = _call("Read", "/nonexistent/path/fake.py", log_path)
        assert code == 0
        assert "READ-GUARD BLOCK" not in stderr

    def test_missing_file_logged_as_untracked(self, log_path):
        """TC-7: Non-existent file is logged with hash 'UNTRACKED'."""
        _call("Read", "/nonexistent/path/fake.py", log_path)
        log = _load(log_path)
        entry = log["reads"].get("/nonexistent/path/fake.py")
        assert entry is not None
        assert entry["hash"] == "UNTRACKED"

    def test_malformed_json_input_allowed(self, log_path):
        """Guard exits 0 on unparseable stdin — never crashes Claude Code."""
        env = {**os.environ, "READ_GUARD_LOG": log_path}
        result = subprocess.run(
            [sys.executable, GUARD],
            input="not json at all", text=True, capture_output=True, env=env,
        )
        assert result.returncode == 0

    def test_empty_stdin_allowed(self, log_path):
        """Guard exits 0 on empty stdin."""
        env = {**os.environ, "READ_GUARD_LOG": log_path}
        result = subprocess.run(
            [sys.executable, GUARD],
            input="", text=True, capture_output=True, env=env,
        )
        assert result.returncode == 0


class TestIsolation:
    def test_real_log_untouched(self, log_path, tmp_file):
        """TC-8: Real session_reads.json is never modified when READ_GUARD_LOG is set."""
        real_log = os.path.join(
            os.path.dirname(GUARD), "session_reads.json"
        )
        existed_before = os.path.exists(real_log)
        mtime_before = os.path.getmtime(real_log) if existed_before else None

        # Run several calls using the isolated log
        for _ in range(5):
            _call("Read", tmp_file, log_path)

        if existed_before:
            assert os.path.getmtime(real_log) == mtime_before
        else:
            assert not os.path.exists(real_log)

    def test_each_test_gets_fresh_log(self, log_path, tmp_file):
        """TC-8: Each test's log_path fixture is unique — no cross-test contamination."""
        _call("Read", tmp_file, log_path)
        log = _load(log_path)
        # Only one entry, read_count exactly 1
        assert len(log["reads"]) == 1
        assert list(log["reads"].values())[0]["read_count"] == 1


class TestPerformance:
    def test_guard_completes_under_500ms(self, log_path, tmp_file):
        """Guard must complete in under 500ms per call — never adds noticeable latency."""
        start = time.perf_counter()
        _call("Read", tmp_file, log_path)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"read_guard took {elapsed:.3f}s — too slow"
