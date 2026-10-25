#!/usr/bin/env python3
"""PB-008: Dual-Bank NVRAM partition tests and torn-standby resilience."""

import tempfile
import unittest
from pathlib import Path

from scripts.proofboot_pb008_nvram import (
    Reject,
    SLOT_SIZE,
    initialize,
    read_header,
    recover,
    update,
)


class PB008Tests(unittest.TestCase):
    def setUp(self):
        self.secret = "nvram-hardware-secret-key"
        self.temp = tempfile.TemporaryDirectory()
        self.dev = Path(self.temp.name) / "nvram.bin"
        initialize(self.dev, secret_key=self.secret, arch="aarch64")

    def tearDown(self):
        self.temp.cleanup()

    def test_initial_state(self):
        slot, gen = read_header(self.dev)
        self.assertEqual(slot, 0)
        self.assertEqual(gen, 1)

        policy = recover(self.dev, secret_key=self.secret)
        self.assertEqual(policy["generation"], 1)
        self.assertEqual(policy["key"], "release-A")

    def test_dual_bank_flip_transition(self):
        # Update 1: Flips from Bank 0 to Bank 1
        res1 = update(self.dev, new_key="release-B", secret_key=self.secret)
        self.assertEqual(res1["generation"], 2)
        slot, gen = read_header(self.dev)
        self.assertEqual(slot, 1)
        self.assertEqual(gen, 2)

        # Update 2: Flips from Bank 1 back to Bank 0
        res2 = update(self.dev, new_key="release-C", secret_key=self.secret)
        self.assertEqual(res2["generation"], 3)
        slot, gen = read_header(self.dev)
        self.assertEqual(slot, 0)
        self.assertEqual(gen, 3)

        current = recover(self.dev, secret_key=self.secret)
        self.assertEqual(current["key"], "release-C")

    def test_torn_standby_write_leaves_active_bank_valid(self):
        """Simulate power-loss during standby write: active slot remains completely uncorrupted."""
        # Active is Bank 0. Standby is Bank 1 (offset 4096 to 8192)
        with open(self.dev, "r+b") as f:
            f.seek(SLOT_SIZE)
            # Write partial garbage into standby bank
            f.write(b"CORRUPT_TEARING_PARTIAL_WRITE" * 8)

        # System recovery must remain unaffected because active bank is Bank 0
        policy = recover(self.dev, secret_key=self.secret)
        self.assertEqual(policy["generation"], 1)
        self.assertEqual(policy["key"], "release-A")

    def test_active_bank_tamper_fails_closed(self):
        """Modifying the active bank causes cryptographic rejection."""
        with open(self.dev, "r+b") as f:
            f.seek(0)
            f.write(b"CORRUPT_ACTIVE_BANK")

        with self.assertRaises(Reject):
            recover(self.dev, secret_key=self.secret)

    def test_header_tamper_fails_closed(self):
        """Invalid slot indicator in header halts boot."""
        with open(self.dev, "r+b") as f:
            f.seek(8192 + 4)  # active_slot offset
            f.write(b"\x05\x00\x00\x00")  # Invalid slot 5

        with self.assertRaises(Reject):
            recover(self.dev, secret_key=self.secret)


if __name__ == "__main__":
    unittest.main()
