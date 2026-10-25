#!/usr/bin/env python3
"""PB-007: Cryptographically bound durable policy transitions with tamper detection."""

import argparse
import contextlib
import hashlib
import hmac
import json
import os
import sys
import tempfile
from pathlib import Path


class Reject(Exception):
    pass


class ConcurrencyError(Reject):
    pass


@contextlib.contextmanager
def acquire_lock(root):
    lock_path = Path(root) / ".lock"
    try:
        fd = os.open(
            str(lock_path),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
    except FileExistsError as exc:
        raise ConcurrencyError("store is locked by another operation") from exc

    try:
        yield
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            lock_path.unlink()
        except OSError:
            pass


def sync_directory(directory):
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(str(directory), flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write(path, data):
    path = Path(path)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(prefix=".pb007-", dir=str(parent))
    temp = Path(temp_name)

    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temp, path)
        sync_directory(parent)
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass


def compute_digest(payload_bytes, secret_key):
    return hmac.new(secret_key.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


def encode_envelope(payload, secret_key):
    canonical_body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = compute_digest(canonical_body, secret_key)
    envelope = {
        "payload": payload,
        "digest": signature,
    }
    return (json.dumps(envelope, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def validate_envelope(data_bytes, secret_key):
    try:
        envelope = json.loads(data_bytes.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise Reject(f"invalid JSON envelope: {exc}") from exc

    if not isinstance(envelope, dict) or set(envelope) != {"payload", "digest"}:
        raise Reject("malformed envelope structure")

    payload = envelope["payload"]
    declared_digest = envelope["digest"]

    if not isinstance(payload, dict):
        raise Reject("payload is not an object")

    if set(payload) != {"generation", "key", "arch"}:
        raise Reject("invalid payload schema")

    if type(payload["generation"]) is not int or payload["generation"] < 1:
        raise Reject("invalid generation")

    if not isinstance(payload["key"], str) or not payload["key"].strip():
        raise Reject("invalid release key")

    if payload["arch"] not in ("x86_64", "aarch64"):
        raise Reject("unsupported architecture")

    canonical_body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected_digest = compute_digest(canonical_body, secret_key)

    if not hmac.compare_digest(declared_digest, expected_digest):
        raise Reject("cryptographic signature mismatch (tampered policy)")

    return payload


def initialize(root, secret_key, arch="aarch64"):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with acquire_lock(root):
        committed = root / "committed.json"
        if committed.exists():
            raise Reject("store already initialized")

        initial_payload = {
            "generation": 1,
            "key": "release-A",
            "arch": arch,
        }
        raw_envelope = encode_envelope(initial_payload, secret_key)
        atomic_write(committed, raw_envelope)
    print("Initialized generation 1")


def recover(root, secret_key):
    committed_path = Path(root) / "committed.json"
    if not committed_path.exists():
        raise Reject("committed.json not found")
    try:
        data = committed_path.read_bytes()
    except OSError as exc:
        raise Reject(f"cannot read store: {exc}") from exc

    return validate_envelope(data, secret_key)


def update(root, new_key, secret_key, arch=None):
    if not isinstance(new_key, str) or not new_key.strip():
        raise Reject("invalid release key")

    root = Path(root)
    committed_path = root / "committed.json"
    pending_path = root / "pending.json"

    with acquire_lock(root):
        old = recover(root, secret_key)
        target_arch = arch if arch else old["arch"]

        candidate_payload = {
            "generation": old["generation"] + 1,
            "key": new_key,
            "arch": target_arch,
        }

        # Stage 1: write pending envelope
        raw_pending = encode_envelope(candidate_payload, secret_key)
        atomic_write(pending_path, raw_pending)

        # Stage 2: validate pending envelope on disk
        persisted = validate_envelope(pending_path.read_bytes(), secret_key)
        if persisted["generation"] != old["generation"] + 1:
            raise Reject("monotonic generation violation")

        # Stage 3: commit replacement
        atomic_write(committed_path, raw_pending)

        # Stage 4: cleanup
        pending_path.unlink(missing_ok=True)
        sync_directory(root)

    return recover(root, secret_key)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init")
    init_p.add_argument("store")
    init_p.add_argument("--secret", default="test-secret-key")
    init_p.add_argument("--arch", default="aarch64")

    update_p = sub.add_parser("update")
    update_p.add_argument("store")
    update_p.add_argument("--key", required=True)
    update_p.add_argument("--secret", default="test-secret-key")
    update_p.add_argument("--arch", default=None)

    check_p = sub.add_parser("check")
    check_p.add_argument("store")
    check_p.add_argument("--secret", default="test-secret-key")

    args = parser.parse_args()

    try:
        if args.command == "init":
            initialize(args.store, args.secret, args.arch)
        elif args.command == "update":
            res = update(args.store, args.key, args.secret, args.arch)
            print(json.dumps(res, sort_keys=True))
        elif args.command == "check":
            print(json.dumps(recover(args.store, args.secret), sort_keys=True))
        return 0
    except (Reject, OSError, ValueError) as exc:
        print(f"PB-007 REJECT: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
