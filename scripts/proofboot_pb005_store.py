#!/usr/bin/env python3
"""PB-005: Durable file-backed policy transitions."""

import argparse
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path


class Reject(Exception):
    """A policy or store operation was rejected."""


class ConcurrencyError(Reject):
    """Another operation holds the store lock."""


@contextlib.contextmanager
def acquire_lock(root):
    """Acquire a non-blocking, exclusive store lock."""
    lock_path = Path(root) / ".lock"

    try:
        fd = os.open(
            str(lock_path),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
    except FileExistsError as exc:
        raise ConcurrencyError(
            "store is locked by another operation"
        ) from exc

    try:
        yield
    finally:
        try:
            os.close(fd)
        finally:
            # Surface cleanup errors instead of silently claiming
            # that the lock was released.
            lock_path.unlink()


def sync_directory(directory):
    """Request persistence of directory-entry changes."""
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(str(directory), flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write(path, data):
    """Write, sync, atomically replace, and sync the parent directory."""
    path = Path(path)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        prefix=".pb005-", dir=str(parent)
    )
    temp = Path(temp_name)

    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temp, path)
        sync_directory(parent)
    finally:
        # Do not mask the original I/O error if cleanup also fails.
        try:
            temp.unlink(missing_ok=True)
        except OSError as exc:
            print(
                f"PB-005 WARNING: cannot remove {temp}: {exc}",
                file=sys.stderr,
            )


def encode(policy):
    return (
        json.dumps(
            policy, sort_keys=True, separators=(",", ":")
        ) + "\n"
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
        atomic_write(committed, encode(initial))

    print("Initialized generation 1")


def recover(root):
    """Only committed.json is authoritative; pending is never promoted."""
    return read_policy(Path(root) / "committed.json")


def update(root, new_key, crash_after=None):
    # Reject invalid keys before touching the store or acquiring a lock.
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

        # Stage 1: write the inactive candidate.
        atomic_write(pending_path, encode(candidate))
        crash(crash_after, "pending")

        # Stage 2: validate the persisted candidate.
        persisted = read_policy(pending_path)
        if persisted["generation"] != old["generation"] + 1:
            raise Reject("generation transition invalid")
        crash(crash_after, "validated")

        # Stage 3: replace the authoritative policy.
        atomic_write(committed_path, encode(persisted))
        crash(crash_after, "committed")

        # Stage 4: remove the candidate.
        pending_path.unlink(missing_ok=True)
        sync_directory(root)
        crash(crash_after, "cleanup")

    return recover(root)


def crash(requested, stage):
    """Simulate abrupt termination without Python cleanup."""
    if requested == stage:
        os._exit(77)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init")
    init_parser.add_argument("store")

    update_parser = sub.add_parser("update")
    update_parser.add_argument("store")
    update_parser.add_argument("--key", required=True)
    update_parser.add_argument(
        "--crash-after",
        choices=("pending", "validated", "committed", "cleanup"),
    )

    check_parser = sub.add_parser("check")
    check_parser.add_argument("store")

    args = parser.parse_args()

    try:
        if args.command == "init":
            initialize(args.store)
        elif args.command == "update":
            result = update(
                args.store, args.key, args.crash_after
            )
            print(json.dumps(result, sort_keys=True))
        else:
            print(json.dumps(recover(args.store), sort_keys=True))
        return 0
    except (Reject, OSError, ValueError) as exc:
        print(f"PB-005 REJECT: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
