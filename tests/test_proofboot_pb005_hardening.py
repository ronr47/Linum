#!/usr/bin/env python3
"""PB-005 durability and concurrency regression tests."""

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.proofboot_pb005_store import (
    ConcurrencyError,
    Reject,
    initialize,
    recover,
    update,
)


class PB005HardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Path(self.tmp.name) / "store"
        initialize(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def assert_old_policy(self):
        self.assertEqual(
            recover(self.store),
            {"generation": 1, "key": "release-A"},
        )

    def assert_no_temp_files(self):
        self.assertEqual(list(self.store.glob(".pb005-*")), [])

    def test_invalid_keys_do_not_modify_store(self):
        for key in ("", " ", "\t", None, 123):
            with self.subTest(key=repr(key)):
                with self.assertRaises(Reject):
                    update(self.store, key)

                self.assertFalse(
                    (self.store / "pending.json").exists()
                )
                self.assert_old_policy()

        self.assertFalse((self.store / ".lock").exists())
        self.assert_no_temp_files()

    def test_file_fsync_failure_propagates_and_cleans_temp(self):
        with patch(
            "scripts.proofboot_pb005_store.os.fsync",
            side_effect=OSError("injected file fsync failure"),
        ):
            with self.assertRaisesRegex(OSError, "file fsync"):
                update(self.store, "release-B")

        self.assert_old_policy()
        self.assert_no_temp_files()
        self.assertFalse((self.store / ".lock").exists())

    def test_pending_directory_fsync_failure_propagates(self):
        real_fsync = os.fsync

        def fail_directory_sync(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise OSError("injected directory fsync failure")
            return real_fsync(fd)

        with patch(
            "scripts.proofboot_pb005_store.os.fsync",
            side_effect=fail_directory_sync,
        ):
            with self.assertRaisesRegex(OSError, "directory fsync"):
                update(self.store, "release-B")

        # The pending rename may have happened. The committed record
        # must remain authoritative and retain its original contents.
        self.assert_old_policy()
        self.assert_no_temp_files()
        self.assertFalse((self.store / ".lock").exists())

    def test_pending_replace_failure_preserves_committed(self):
        with patch(
            "scripts.proofboot_pb005_store.os.replace",
            side_effect=OSError("injected replace failure"),
        ):
            with self.assertRaisesRegex(OSError, "replace failure"):
                update(self.store, "release-B")

        self.assert_old_policy()
        self.assert_no_temp_files()
        self.assertFalse((self.store / ".lock").exists())

    def test_committed_replace_failure_preserves_old_policy(self):
        real_replace = os.replace

        def fail_committed(src, dst):
            if Path(dst) == self.store / "committed.json":
                raise OSError("injected committed replacement failure")
            return real_replace(src, dst)

        with patch(
            "scripts.proofboot_pb005_store.os.replace",
            side_effect=fail_committed,
        ):
            with self.assertRaisesRegex(OSError, "committed replacement"):
                update(self.store, "release-B")

        self.assert_old_policy()
        self.assert_no_temp_files()
        self.assertFalse((self.store / ".lock").exists())

    def test_existing_lock_rejects_update(self):
        (self.store / ".lock").write_text("held", encoding="utf-8")

        with self.assertRaises(ConcurrencyError):
            update(self.store, "release-B")

        self.assert_old_policy()

    def test_existing_lock_rejects_initialization(self):
        (self.store / ".lock").write_text("held", encoding="utf-8")

        with self.assertRaises(ConcurrencyError):
            initialize(self.store)

        self.assert_old_policy()

    def test_successful_update_cleans_lock_and_pending(self):
        result = update(self.store, "release-B")

        self.assertEqual(
            result, {"generation": 2, "key": "release-B"}
        )
        self.assertFalse((self.store / ".lock").exists())
        self.assertFalse((self.store / "pending.json").exists())
        self.assert_no_temp_files()


if __name__ == "__main__":
    unittest.main()
