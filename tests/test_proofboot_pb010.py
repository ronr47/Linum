#!/usr/bin/env python3
"""PB-010: Structural and behavioral verification for R2 dual-bank storage engine."""

import hashlib
import hmac
import struct
import unittest
import zlib
from pathlib import Path

SLOT_SIZE = 4096
HEADER_A_OFFSET = 8192
HEADER_B_OFFSET = 8256
HEADER_SIZE = 64
PB_MAGIC = 0x564E4250  # b"PBNV"


class StorageDeviceMock:
    def __init__(self, key: bytes):
        self.buffer = bytearray(16384)
        self.key = key

    def mmio_read(self, offset: int, length: int) -> bytes:
        return bytes(self.buffer[offset : offset + length])

    def mmio_write(self, offset: int, data: bytes):
        self.buffer[offset : offset + len(data)] = data


def compute_crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def compute_hmac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


class PB010ReferenceEngine:
    def __init__(self, dev: StorageDeviceMock):
        self.dev = dev

    def parse_header(self, raw: bytes):
        if len(raw) < 20:
            return False, None
        magic, active_slot, gen, seq, crc = struct.unpack("<IIIII", raw[:20])
        if magic != PB_MAGIC or active_slot > 1:
            return False, None
        if crc != compute_crc32(raw[:16]):
            return False, None
        return True, {
            "magic": magic,
            "active_slot": active_slot,
            "generation": gen,
            "seq": seq,
            "crc": crc,
        }

    def arbitrate_active_header(self):
        raw_a = self.dev.mmio_read(HEADER_A_OFFSET, HEADER_SIZE)
        raw_b = self.dev.mmio_read(HEADER_B_OFFSET, HEADER_SIZE)

        valid_a, hdr_a = self.parse_header(raw_a)
        valid_b, hdr_b = self.parse_header(raw_b)

        if not valid_a and not valid_b:
            return False, None, "X"
        if valid_a and valid_b:
            if hdr_a["seq"] >= hdr_b["seq"]:
                return True, hdr_a, "A"
            return True, hdr_b, "B"
        if valid_a:
            return True, hdr_a, "A"
        return True, hdr_b, "B"

    def commit_transition(self, new_payload: bytes, new_generation: int):
        ok, active_hdr, side = self.arbitrate_active_header()
        if not ok:
            return "CrcMismatch"

        if new_generation <= active_hdr["generation"]:
            return "MonotonicViolation"

        target_slot = 1 - active_hdr["active_slot"]
        target_offset = target_slot * SLOT_SIZE

        # Assemble Slot Frame: [Magic(4) | BodyLen(4) | HMAC(32) | Payload]
        digest = compute_hmac(self.dev.key, new_payload)
        slot_frame = bytearray(SLOT_SIZE)
        slot_frame[0:4] = struct.pack("<I", PB_MAGIC)
        slot_frame[4:8] = struct.pack("<I", len(new_payload))
        slot_frame[8:40] = digest
        slot_frame[40 : 40 + len(new_payload)] = new_payload

        # Write standby slot
        self.dev.mmio_write(target_offset, slot_frame)

        # Build next ping-pong header
        next_seq = active_hdr["seq"] + 1
        meta = struct.pack("<IIII", PB_MAGIC, target_slot, new_generation, next_seq)
        crc = compute_crc32(meta)
        next_hdr = bytearray(HEADER_SIZE)
        next_hdr[:16] = meta
        next_hdr[16:20] = struct.pack("<I", crc)

        target_header_offset = HEADER_B_OFFSET if side == "A" else HEADER_A_OFFSET
        self.dev.mmio_write(target_header_offset, next_hdr)
        return "Ok"


class TestProofBootPB010(unittest.TestCase):
    def setUp(self):
        self.key = b"sovereign_silicon_root_key_2026"
        self.dev = StorageDeviceMock(self.key)
        self.engine = PB010ReferenceEngine(self.dev)

        # Initialize Slot 0 / Generation 1 / Seq 1 in Header A
        meta = struct.pack("<IIII", PB_MAGIC, 0, 1, 1)
        crc = compute_crc32(meta)
        hdr = bytearray(HEADER_SIZE)
        hdr[:16] = meta
        hdr[16:20] = struct.pack("<I", crc)
        self.dev.mmio_write(HEADER_A_OFFSET, hdr)

    def test_arbitration_initial(self):
        ok, hdr, side = self.engine.arbitrate_active_header()
        self.assertTrue(ok)
        self.assertEqual(side, "A")
        self.assertEqual(hdr["generation"], 1)
        self.assertEqual(hdr["active_slot"], 0)

    def test_transition_success(self):
        payload = b'{"state": "SECURE_BOOT_GEN2"}'
        res = self.engine.commit_transition(payload, new_generation=2)
        self.assertEqual(res, "Ok")

        ok, hdr, side = self.engine.arbitrate_active_header()
        self.assertTrue(ok)
        self.assertEqual(side, "B")
        self.assertEqual(hdr["active_slot"], 1)
        self.assertEqual(hdr["generation"], 2)
        self.assertEqual(hdr["seq"], 2)

    def test_monotonic_violation_rejected(self):
        payload = b'{"state": "ROLLBACK_ATTEMPT"}'
        # Generation 1 <= Current Generation 1 must fail
        res = self.engine.commit_transition(payload, new_generation=1)
        self.assertEqual(res, "MonotonicViolation")

        # Prior active state preserved
        ok, hdr, side = self.engine.arbitrate_active_header()
        self.assertEqual(hdr["generation"], 1)
        self.assertEqual(side, "A")


if __name__ == "__main__":
    unittest.main()
