#!/usr/bin/env python3
"""PB-009: Dual-Bank NVRAM emulator with redundant headers and torn-header resilience."""

import argparse
import hashlib
import hmac
import json
import os
import struct
import sys
import zlib
from pathlib import Path

SLOT_SIZE = 4096
HEADER_A_OFFSET = 8192
HEADER_B_OFFSET = 8256
HEADER_SIZE = 64
MAGIC = b"PBNV"


class Reject(Exception):
    pass


def compute_digest(payload_bytes, secret_key):
    return hmac.new(secret_key.encode("utf-8"), payload_bytes, hashlib.sha256).digest()


def pack_slot(payload, secret_key):
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = compute_digest(body, secret_key)
    header = struct.pack("<4sI32s", MAGIC, len(body), sig)
    raw = header + body
    if len(raw) > SLOT_SIZE:
        raise Reject(f"payload exceeds slot size: {len(raw)} > {SLOT_SIZE}")
    return raw.ljust(SLOT_SIZE, b"\x00")


def unpack_slot(raw_bytes, secret_key):
    if len(raw_bytes) < 40:
        raise Reject("slot data too short")
    magic, body_len, declared_sig = struct.unpack_from("<4sI32s", raw_bytes, 0)
    if magic != MAGIC:
        raise Reject("invalid slot magic")
    if body_len > (SLOT_SIZE - 40):
        raise Reject("declared payload length out of bounds")

    body = raw_bytes[40 : 40 + body_len]
    expected_sig = compute_digest(body, secret_key)
    if not hmac.compare_digest(declared_sig, expected_sig):
        raise Reject("slot cryptographic integrity verification failed")

    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise Reject(f"malformed payload JSON: {exc}") from exc


def parse_header(raw_hdr):
    if len(raw_hdr) < 20:
        return None
    magic, active_slot, generation, seq, crc = struct.unpack("<4sIIII", raw_hdr[:20])
    if magic != MAGIC or active_slot not in (0, 1):
        return None
    expected_crc = zlib.crc32(raw_hdr[:16]) & 0xFFFFFFFF
    if crc != expected_crc:
        return None
    return {"active_slot": active_slot, "generation": generation, "seq": seq}


def serialize_header(active_slot, generation, seq):
    payload = struct.pack("<4sIII", MAGIC, active_slot, generation, seq)
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    return (payload + struct.pack("<I", crc)).ljust(HEADER_SIZE, b"\x00")


def read_active_header(dev_path):
    with open(dev_path, "rb") as f:
        f.seek(HEADER_A_OFFSET)
        hdr_a_bytes = f.read(HEADER_SIZE)
        f.seek(HEADER_B_OFFSET)
        hdr_b_bytes = f.read(HEADER_SIZE)

    hdr_a = parse_header(hdr_a_bytes)
    hdr_b = parse_header(hdr_b_bytes)

    if hdr_a is None and hdr_b is None:
        raise Reject("both metadata headers are corrupted or uninitialized")

    if hdr_a is not None and hdr_b is not None:
        # Return header with highest monotonic sequence counter
        return (hdr_a, "A") if hdr_a["seq"] >= hdr_b["seq"] else (hdr_b, "B")

    if hdr_a is not None:
        return hdr_a, "A"
    return hdr_b, "B"


def write_next_header(dev_path, active_slot, generation, current_seq, last_valid_side):
    next_seq = current_seq + 1
    hdr_bytes = serialize_header(active_slot, generation, next_seq)
    # Ping-pong write: write to the alternative header side
    target_offset = HEADER_B_OFFSET if last_valid_side == "A" else HEADER_A_OFFSET

    with open(dev_path, "r+b") as f:
        f.seek(target_offset)
        f.write(hdr_bytes)
        f.flush()
        os.fsync(f.fileno())


def initialize(dev_path, secret_key, arch="aarch64"):
    dev_path = Path(dev_path)
    if dev_path.exists():
        raise Reject("device already initialized")

    dev_path.parent.mkdir(parents=True, exist_ok=True)
    initial_payload = {
        "generation": 1,
        "key": "release-A",
        "arch": arch,
    }
    bank_a = pack_slot(initial_payload, secret_key)
    bank_b = b"\x00" * SLOT_SIZE
    hdr_a = serialize_header(active_slot=0, generation=1, seq=1)
    hdr_b = serialize_header(active_slot=0, generation=1, seq=0)

    with open(dev_path, "wb") as f:
        f.write(bank_a + bank_b + hdr_a + hdr_b)
        f.flush()
        os.fsync(f.fileno())
    print("Initialized PB-009 Dual-Header NVRAM (Bank A, Slot 0, Gen 1)")


def recover(dev_path, secret_key):
    dev_path = Path(dev_path)
    if not dev_path.exists():
        raise Reject("device file not found")

    hdr, _ = read_active_header(dev_path)
    offset = hdr["active_slot"] * SLOT_SIZE

    with open(dev_path, "rb") as f:
        f.seek(offset)
        slot_bytes = f.read(SLOT_SIZE)

    return unpack_slot(slot_bytes, secret_key)


def update(dev_path, new_key, secret_key, arch=None):
    if not isinstance(new_key, str) or not new_key.strip():
        raise Reject("invalid release key")

    dev_path = Path(dev_path)
    hdr, side = read_active_header(dev_path)
    old = recover(dev_path, secret_key)

    target_slot = 1 - hdr["active_slot"]
    next_gen = old["generation"] + 1

    candidate_payload = {
        "generation": next_gen,
        "key": new_key,
        "arch": arch if arch else old["arch"],
    }

    # Step 1: Write candidate to standby bank
    slot_bytes = pack_slot(candidate_payload, secret_key)
    standby_offset = target_slot * SLOT_SIZE

    with open(dev_path, "r+b") as f:
        f.seek(standby_offset)
        f.write(slot_bytes)
        f.flush()
        os.fsync(f.fileno())

    # Step 2: Verify standby bank in place
    with open(dev_path, "rb") as f:
        f.seek(standby_offset)
        written = f.read(SLOT_SIZE)
    unpack_slot(written, secret_key)

    # Step 3: Write next redundant header
    write_next_header(dev_path, target_slot, next_gen, hdr["seq"], side)

    return recover(dev_path, secret_key)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init")
    init_p.add_argument("device")
    init_p.add_argument("--secret", default="nvram-secret-key")
    init_p.add_argument("--arch", default="aarch64")

    update_p = sub.add_parser("update")
    update_p.add_argument("device")
    update_p.add_argument("--key", required=True)
    update_p.add_argument("--secret", default="nvram-secret-key")
    update_p.add_argument("--arch", default=None)

    check_p = sub.add_parser("check")
    check_p.add_argument("device")
    check_p.add_argument("--secret", default="nvram-secret-key")

    args = parser.parse_args()

    try:
        if args.command == "init":
            initialize(args.device, args.secret, args.arch)
        elif args.command == "update":
            res = update(args.device, args.key, args.secret, args.arch)
            print(json.dumps(res, sort_keys=True))
        elif args.command == "check":
            print(json.dumps(recover(args.device, args.secret), sort_keys=True))
        return 0
    except (Reject, OSError, ValueError) as exc:
        print(f"PB-009 REJECT: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
