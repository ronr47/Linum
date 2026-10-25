#!/usr/bin/env python3
"""PB-006: Subprocess crash-injection and authority isolation tests."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.proofboot_pb006_store import (
    Reject,
    initialize,
    recover,
)

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "proofboot_pb006_store.py"
)


class PB006Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Path(self.temp.name) / "store"
        initialize(self.store)

    def tearDown(self):
        self.temp.cleanup()

    def run_child_update(self, crash_point=None, key="release-B"):
        cmd = [
            sys.executable, str(SCRIPT), "update",
            str(self.store), "--key", key,
        ]
        if crash_point:
            cmd.extend(["--crash-point", crash_point])
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_clean_transition_lifecycle(self):
        result = self.run_child_update()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            recover(self.store),
            {"generation": 2, "key": "release-B"},
        )
        self.assertFalse((self.store / "pending.json").exists())
        self.assertFalse((self.store / ".lock").exists())

    def test_crashes_before_commit_preserve_gen1(self):
        crash_points = [
            "pending_pre_write",
            "pending_pre_file_sync",
            "pending_pre_replace",
            "pending_post_replace",
            "pending_post_dir_sync",
            "post_candidate_validation",
            "commit_pre_write",
            "commit_pre_file_sync",
            "commit_pre_replace",
        ]
        for point in crash_points:
            with self.subTest(crash_point=point):
                # Fresh store instance for each crash test to prevent lock contention
                self.temp.cleanup()
                self.temp = tempfile.TemporaryDirectory()
                self.store = Path(self.temp.name) / "store"
                initialize(self.store)

                res = self.run_child_update(crash_point=point)
                self.assertEqual(res.returncode, 77, f"Did not crash as expected at {point}")

                # Authoritative state must remain Generation 1
                self.assertEqual(
                    recover(self.store),
                    {"generation": 1, "key": "release-A"},
                    f"State changed unexpectedly at {point}",
                )

    def test_crashes_after_commit_preserve_gen2(self):
        crash_points = [
            "commit_post_replace",
            "commit_post_dir_sync",
            "post_cleanup",
        ]
        for point in crash_points:
            with self.subTest(crash_point=point):
                self.temp.cleanup()
                self.temp = tempfile.TemporaryDirectory()
                self.store = Path(self.temp.name) / "store"
                initialize(self.store)

                res = self.run_child_update(crash_point=point)
                self.assertEqual(res.returncode, 77, f"Did not crash as expected at {point}")

                # Once replacement occurs, Gen 2 is the new baseline truth
                self.assertEqual(
                    recover(self.store),
                    {"generation": 2, "key": "release-B"},
                    f"Failed to adopt new generation after {point}",
                )

    def test_orphan_pending_never_promoted(self):
        rogue_policy = {"generation": 999, "key": "adversary"}
        (self.store / "pending.json").write_text(json.dumps(rogue_policy), encoding="utf-8")

        self.assertEqual(
            recover(self.store),
            {"generation": 1, "key": "release-A"},
        )

    def test_corrupted_committed_fails_closed(self):
        (self.store / "committed.json").write_text("{corrupt-json", encoding="utf-8")
        with self.assertRaises(Reject):
            recover(self.store)


if __name__ == "__main__":
    unittest.main()
