#!/usr/bin/env python3
"""PB-008: Dual-Bank A/B NVRAM partition emulator with atomic slot toggle."""

import argparse
import hashlib
import hmac
import json
import os
import struct
import sys
from pathlib import Path

SLOT_SIZE = 4096
HEADER_OFFSET = 8192
MAGIC = b"PBNV"  # ProofBoot NVRAM


class Reject(Exception):
    pass


def compute_digest(payload_bytes, secret_key):
    return hmac.new(secret_key.encode("utf-8"), payload_bytes, hashlib.sha256).digest()


def pack_slot(payload, secret_key):
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = compute_digest(body, secret_key)
    # Slot format: [4B Magic][4B Payload Length][32B HMAC-SHA256][Payload Body][Padding]
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
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise Reject(f"malformed payload JSON: {exc}") from exc

    return payload


def read_header(dev_path):
    with open(dev_path, "rb") as f:
        f.seek(HEADER_OFFSET)
        hdr = f.read(64)
    if len(hdr) < 16:
        raise Reject("corrupt device header")
    magic, active_slot, generation, _ = struct.unpack("<4sII4s", hdr[:16])
    if magic != MAGIC:
        raise Reject("invalid header magic")
    if active_slot not in (0, 1):
        raise Reject("active slot must be 0 (Bank A) or 1 (Bank B)")
    return active_slot, generation


def write_header(dev_path, active_slot, generation):
    hdr = struct.pack("<4sII4s", MAGIC, active_slot, generation, b"\x00" * 4).ljust(64, b"\x00")
    with open(dev_path, "r+b") as f:
        f.seek(HEADER_OFFSET)
        f.write(hdr)
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
    header = struct.pack("<4sII4s", MAGIC, 0, 1, b"\x00" * 4).ljust(64, b"\x00")

    with open(dev_path, "wb") as f:
        f.write(bank_a + bank_b + header)
        f.flush()
        os.fsync(f.fileno())
    print("Initialized NVRAM Bank A (Slot 0, Generation 1)")


def recover(dev_path, secret_key):
    dev_path = Path(dev_path)
    if not dev_path.exists():
        raise Reject("device file not found")

    active_slot, _ = read_header(dev_path)
    offset = active_slot * SLOT_SIZE

    with open(dev_path, "rb") as f:
        f.seek(offset)
        slot_bytes = f.read(SLOT_SIZE)

    return unpack_slot(slot_bytes, secret_key)


def update(dev_path, new_key, secret_key, arch=None):
    if not isinstance(new_key, str) or not new_key.strip():
        raise Reject("invalid release key")

    dev_path = Path(dev_path)
    active_slot, current_gen = read_header(dev_path)
    old = recover(dev_path, secret_key)

    target_slot = 1 - active_slot  # 0 -> 1, 1 -> 0
    next_gen = old["generation"] + 1

    candidate_payload = {
        "generation": next_gen,
        "key": new_key,
        "arch": arch if arch else old["arch"],
    }

    # Step 1: Write candidate payload to standby bank
    slot_bytes = pack_slot(candidate_payload, secret_key)
    standby_offset = target_slot * SLOT_SIZE

    with open(dev_path, "r+b") as f:
        f.seek(standby_offset)
        f.write(slot_bytes)
        f.flush()
        os.fsync(f.fileno())

    # Step 2: Verify standby bank readability and cryptographic digest in place
    with open(dev_path, "rb") as f:
        f.seek(standby_offset)
        written_bytes = f.read(SLOT_SIZE)
    unpack_slot(written_bytes, secret_key)

    # Step 3: Atomic pointer toggle in header
    write_header(dev_path, target_slot, next_gen)

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
        print(f"PB-008 REJECT: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
