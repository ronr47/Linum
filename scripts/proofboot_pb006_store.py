#!/usr/bin/env python3
"""PB-006: Multi-process durable state store with granular crash injection."""

import argparse
import contextlib
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
    """Enforce mutual exclusion across process boundaries."""
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


def trigger_crash(point, target):
    """Abrupt process termination via unbuffered os._exit without cleanup."""
    if point and point == target:
        os._exit(77)


def sync_directory(directory):
    """Request persistence of directory-entry changes to storage substrate."""
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(str(directory), flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write(path, data, crash_point=None, prefix=""):
    """Write bytes with low-level barrier synchronization and crash triggers."""
    path = Path(path)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(prefix=f".pb006-{prefix}-", dir=str(parent))
    temp = Path(temp_name)

    trigger_crash(f"{prefix}_pre_write", crash_point)

    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            trigger_crash(f"{prefix}_pre_file_sync", crash_point)
            os.fsync(stream.fileno())

        trigger_crash(f"{prefix}_pre_replace", crash_point)
        os.replace(temp, path)
        trigger_crash(f"{prefix}_post_replace", crash_point)

        sync_directory(parent)
        trigger_crash(f"{prefix}_post_dir_sync", crash_point)
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass


def encode(policy):
    return (
        json.dumps(policy, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def validate(policy):
    if not isinstance(policy, dict):
        raise Reject("policy is not an object")
    if set(policy) != {"generation", "key"}:
        raise Reject("unexpected policy fields")
    if type(policy["generation"]) is not int:
        raise Reject("invalid generation type")
    if policy["generation"] < 1:
        raise Reject("invalid generation")
    if not isinstance(policy["key"], str) or not policy["key"].strip():
        raise Reject("invalid release key")
    return policy


def read_policy(path):
    path = Path(path)
    if not path.exists():
        raise Reject(f"file not found: {path.name}")
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise Reject(f"cannot read policy: {exc}") from exc
    return validate(policy)


def initialize(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with acquire_lock(root):
        committed = root / "committed.json"
        if committed.exists():
            raise Reject("store already initialized")

        initial = {"generation": 1, "key": "release-A"}
        validate(initial)
        atomic_write(committed, encode(initial), prefix="init")
    print("Initialized generation 1")


def recover(root):
    """Authority resolver: committed.json is the single anchor of truth."""
    return read_policy(Path(root) / "committed.json")


def update(root, new_key, crash_point=None):
    if not isinstance(new_key, str) or not new_key.strip():
        raise Reject("invalid release key")

    root = Path(root)
    committed_path = root / "committed.json"
    pending_path = root / "pending.json"

    with acquire_lock(root):
        old = recover(root)
        candidate = {
            "generation": old["generation"] + 1,
            "key": new_key,
        }
        validate(candidate)

        # Stage 1: Candidate persistence
        atomic_write(
            pending_path,
            encode(candidate),
            crash_point=crash_point,
            prefix="pending",
        )

        # Stage 2: Verification of persisted candidate
        persisted = read_policy(pending_path)
        if persisted["generation"] != old["generation"] + 1:
            raise Reject("generation transition invalid")
        trigger_crash("post_candidate_validation", crash_point)

        # Stage 3: Atomic authority transfer
        atomic_write(
            committed_path,
            encode(persisted),
            crash_point=crash_point,
            prefix="commit",
        )

        # Stage 4: Cleanup
        pending_path.unlink(missing_ok=True)
        sync_directory(root)
        trigger_crash("post_cleanup", crash_point)

    return recover(root)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init")
    init_p.add_argument("store")

    update_p = sub.add_parser("update")
    update_p.add_argument("store")
    update_p.add_argument("--key", required=True)
    update_p.add_argument("--crash-point", default=None)

    check_p = sub.add_parser("check")
    check_p.add_argument("store")

    args = parser.parse_args()

    try:
        if args.command == "init":
            initialize(args.store)
        elif args.command == "update":
            result = update(args.store, args.key, crash_point=args.crash_point)
            print(json.dumps(result, sort_keys=True))
        elif args.command == "check":
            print(json.dumps(recover(args.store), sort_keys=True))
        return 0
    except (Reject, OSError, ValueError) as exc:
        print(f"PB-006 REJECT: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
