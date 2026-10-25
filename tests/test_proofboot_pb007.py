#!/usr/bin/env python3
"""PB-007: Cryptographic envelope binding and bit-rot tamper injection tests."""

import json
import tempfile
import unittest
from pathlib import Path

from scripts.proofboot_pb007_store import (
    Reject,
    initialize,
    recover,
    update,
)


class PB007Tests(unittest.TestCase):
    def setUp(self):
        self.secret = "production-boot-authority-secret"
        self.temp = tempfile.TemporaryDirectory()
        self.store = Path(self.temp.name) / "store"
        initialize(self.store, secret_key=self.secret, arch="aarch64")

    def tearDown(self):
        self.temp.cleanup()

    def test_clean_authorized_lifecycle(self):
        res = update(self.store, new_key="release-B", secret_key=self.secret)
        self.assertEqual(res["generation"], 2)
        self.assertEqual(res["key"], "release-B")
        self.assertEqual(res["arch"], "aarch64")

        active = recover(self.store, secret_key=self.secret)
        self.assertEqual(active, res)

    def test_bit_flip_tampering_fails_closed(self):
        """Simulate bit-rot / sector corruption: modifying 1 byte invalidates authority."""
        committed = self.store / "committed.json"
        raw = bytearray(committed.read_bytes())
        # Flip bit inside the JSON structure
        raw[20] ^= 0x01
        committed.write_bytes(raw)

        with self.assertRaises(Reject):
            recover(self.store, secret_key=self.secret)

    def test_payload_tamper_signature_mismatch(self):
        """Altering the generation directly without re-signing fails HMAC check."""
        committed = self.store / "committed.json"
        envelope = json.loads(committed.read_text(encoding="utf-8"))
        envelope["payload"]["generation"] = 999
        committed.write_text(json.dumps(envelope), encoding="utf-8")

        with self.assertRaisesRegex(Reject, "cryptographic signature mismatch"):
            recover(self.store, secret_key=self.secret)

    def test_wrong_secret_key_rejected(self):
        with self.assertRaisesRegex(Reject, "cryptographic signature mismatch"):
            recover(self.store, secret_key="wrong-unauthorized-key")

    def test_architecture_validation(self):
        with self.assertRaisesRegex(Reject, "unsupported architecture"):
            update(
                self.store,
                new_key="release-B",
                secret_key=self.secret,
                arch="mips64",
            )


if __name__ == "__main__":
    unittest.main()
