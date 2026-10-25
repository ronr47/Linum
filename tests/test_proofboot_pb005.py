import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.proofboot_pb005_store import (
    Reject,
    initialize,
    recover,
)


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "proofboot_pb005_store.py"
)


class PB005Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Path(self.temp.name) / "store"
        initialize(self.store)

    def tearDown(self):
        self.temp.cleanup()

    def child_update(self, stage):
        return subprocess.run(
            [
                sys.executable, str(SCRIPT), "update",
                str(self.store), "--key", "release-B",
                "--crash-after", stage,
            ],
            capture_output=True,
            text=True,
        )

    def test_crash_before_commit_keeps_old_policy(self):
        for stage in ("pending", "validated"):
            with self.subTest(stage=stage):
                # Each subtest needs a fresh initial store to clear stale post-crash lock.
                self.temp.cleanup()
                self.temp = tempfile.TemporaryDirectory()
                self.store = Path(self.temp.name) / "store"
                initialize(self.store)

                result = self.child_update(stage)
                self.assertEqual(result.returncode, 77, result.stderr)
                self.assertEqual(
                    recover(self.store),
                    {"generation": 1, "key": "release-A"},
                )

    def test_crash_after_commit_keeps_new_policy(self):
        for stage in ("committed", "cleanup"):
            with self.subTest(stage=stage):
                # Each subtest needs a fresh initial store.
                self.temp.cleanup()
                self.temp = tempfile.TemporaryDirectory()
                self.store = Path(self.temp.name) / "store"
                initialize(self.store)

                result = self.child_update(stage)
                self.assertEqual(result.returncode, 77, result.stderr)
                self.assertEqual(
                    recover(self.store),
                    {"generation": 2, "key": "release-B"},
                )

    def test_completed_update(self):
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), "update",
                str(self.store), "--key", "release-B",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            recover(self.store),
            {"generation": 2, "key": "release-B"},
        )
        self.assertFalse((self.store / "pending.json").exists())

    def test_pending_record_is_not_authoritative(self):
        (self.store / "pending.json").write_text(
            json.dumps({"generation": 99, "key": "attacker"})
        )
        self.assertEqual(
            recover(self.store),
            {"generation": 1, "key": "release-A"},
        )

    def test_corrupt_committed_record_fails_closed(self):
        (self.store / "committed.json").write_text("{broken")
        with self.assertRaises(Reject):
            recover(self.store)

    def test_unknown_policy_fields_rejected(self):
        (self.store / "committed.json").write_text(
            json.dumps({
                "generation": 1,
                "key": "release-A",
                "authorized": True,
            })
        )
        with self.assertRaises(Reject):
            recover(self.store)


if __name__ == "__main__":
    unittest.main()
