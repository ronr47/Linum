#!/usr/bin/env python3
"""PB-009: Redundant dual-header tests and torn-header recovery."""

import tempfile
import unittest
from pathlib import Path

from scripts.proofboot_pb009_nvram import (
    HEADER_A_OFFSET,
    HEADER_B_OFFSET,
    HEADER_SIZE,
    Reject,
    initialize,
    read_active_header,
    recover,
    update,
)


class PB009Tests(unittest.TestCase):
    def setUp(self):
        self.secret = "nvram-pb009-key"
        self.temp = tempfile.TemporaryDirectory()
        self.dev = Path(self.temp.name) / "nvram.bin"
        initialize(self.dev, secret_key=self.secret, arch="aarch64")

    def tearDown(self):
        self.temp.cleanup()

    def test_initial_header_arbitration(self):
        hdr, side = read_active_header(self.dev)
        self.assertEqual(side, "A")
        self.assertEqual(hdr["seq"], 1)
        self.assertEqual(hdr["active_slot"], 0)

    def test_monotonic_sequence_progression(self):
        # Update 1 -> writes Header B
        update(self.dev, new_key="release-B", secret_key=self.secret)
        hdr, side = read_active_header(self.dev)
        self.assertEqual(side, "B")
        self.assertEqual(hdr["seq"], 2)
        self.assertEqual(hdr["active_slot"], 1)

        # Update 2 -> writes Header A
        update(self.dev, new_key="release-C", secret_key=self.secret)
        hdr, side = read_active_header(self.dev)
        self.assertEqual(side, "A")
        self.assertEqual(hdr["seq"], 3)
        self.assertEqual(hdr["active_slot"], 0)

    def test_torn_header_fallback(self):
        """If the latest header is torn mid-write, the previous valid header is selected."""
        # Progress to Header B (seq=2, active_slot=1)
        update(self.dev, new_key="release-B", secret_key=self.secret)

        # Corrupt Header B with a partial write / bad CRC
        with open(self.dev, "r+b") as f:
            f.seek(HEADER_B_OFFSET)
            f.write(b"\x00" * HEADER_SIZE)

        # Must fall back cleanly to Header A (seq=1, active_slot=0, release-A)
        hdr, side = read_active_header(self.dev)
        self.assertEqual(side, "A")
        self.assertEqual(hdr["seq"], 1)

        recovered = recover(self.dev, secret_key=self.secret)
        self.assertEqual(recovered["generation"], 1)
        self.assertEqual(recovered["key"], "release-A")

    def test_both_headers_corrupt_fails_closed(self):
        """If both redundant headers are invalid, the system halts without guessing."""
        with open(self.dev, "r+b") as f:
            f.seek(HEADER_A_OFFSET)
            f.write(b"\xFF" * (HEADER_SIZE * 2))

        with self.assertRaisesRegex(Reject, "both metadata headers are corrupted"):
            recover(self.dev, secret_key=self.secret)


if __name__ == "__main__":
    unittest.main()
