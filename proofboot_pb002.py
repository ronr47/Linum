#!/usr/bin/env python3
"""LINUM ProofBoot PB-002: signed firmware authorization."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from proofboot import inspect, Reject

POLICY = "proofboot-pb002-v1"
ARCHES = ("x86_64", "aarch64")


def canonical(obj):
    """Stable bytes for signing and signature verification."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def measure(image):
    data = Path(image).read_bytes()
    info = inspect(data)

    if info.get("format") != "PE32+":
        raise Reject("firmware must be PE32+")

    if info.get("subsystem") != 10:
        raise Reject("image is not a UEFI application")

    return {
        "architecture": info["architecture"],
        "format": info["format"],
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def openssl_sign(private_key, payload, signature):
    subprocess.run([
        "openssl", "pkeyutl", "-sign", "-rawin",
        "-inkey", str(private_key),
        "-in", str(payload),
        "-out", str(signature),
    ], check=True, capture_output=True)


def openssl_verify(public_key, payload, signature):
    result = subprocess.run([
        "openssl", "pkeyutl", "-verify", "-rawin", "-pubin",
        "-inkey", str(public_key),
        "-in", str(payload),
        "-sigfile", str(signature),
    ], capture_output=True, text=True)

    return result.returncode == 0


def sign_image(args):
    evidence = measure(args.image)

    if evidence["architecture"] != args.arch:
        raise Reject("requested architecture does not match image")

    if args.generation < 1:
        raise Reject("generation must be positive")

    manifest = {
        "policy": POLICY,
        "generation": args.generation,
        **evidence,
    }
    payload = canonical(manifest)

    out = Path(args.manifest)
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=out.parent) as temp:
        temp = Path(temp)
        data_file = temp / "canonical.json"
        sig_file = temp / "manifest.sig"
        data_file.write_bytes(payload)

        openssl_sign(args.private_key, data_file, sig_file)

        # Publish the manifest and signature after signing succeeds.
        out.write_text(json.dumps(manifest, indent=2) + "\n")
        Path(args.signature).write_bytes(sig_file.read_bytes())

    print("PASS: image measured")
    print("PASS: manifest signed")
    print(f"Architecture: {evidence['architecture']}")
    print(f"Generation: {args.generation}")
    print(f"SHA-256: {evidence['sha256']}")
    print("PB-002: SIGNED MANIFEST CREATED")


def verify_image(args):
    image = Path(args.image).read_bytes()
    actual = measure(args.image)
    manifest = json.loads(Path(args.manifest).read_text())

    if not isinstance(manifest, dict):
        raise Reject("manifest must be a JSON object")

    required = {
        "policy", "generation", "architecture",
        "format", "size", "sha256",
    }
    if set(manifest) != required:
        raise Reject("manifest fields are missing or unexpected")

    generation = manifest["generation"]
    if type(generation) is not int or generation < 1:
        raise Reject("invalid generation")

    # Verify the signature over the canonical manifest representation.
    with tempfile.TemporaryDirectory(
        dir=Path(args.manifest).parent
    ) as temp:
        payload = Path(temp) / "canonical.json"
        payload.write_bytes(canonical(manifest))

        if not openssl_verify(
            args.public_key, payload, args.signature
        ):
            raise Reject("manifest signature invalid")

    print("PASS: manifest signature")

    checks = {
        "policy_version": manifest["policy"] == POLICY,
        "architecture_policy": args.arch in ARCHES
            and manifest["architecture"] == args.arch,
        "binary_architecture": actual["architecture"] == args.arch,
        "format_matches": manifest["format"] == actual["format"],
        "size_matches": manifest["size"] == actual["size"],
        "sha256_matches": manifest["sha256"] == actual["sha256"],
        "minimum_generation": generation >= args.min_generation,
    }

    failed = []
    for name, passed in checks.items():
        print(f'{"PASS" if passed else "REJECT"}: {name}')
        if not passed:
            failed.append(name)

    if failed:
        raise Reject("policy rejected: " + ", ".join(failed))

    print("PROOFBOOT DECISION: ACCEPT (PB-002 prototype)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("sign")
    s.add_argument("image")
    s.add_argument("--arch", required=True, choices=ARCHES)
    s.add_argument("--generation", type=int, required=True)
    s.add_argument("--private-key", required=True)
    s.add_argument("--manifest", required=True)
    s.add_argument("--signature", required=True)

    v = sub.add_parser("verify")
    v.add_argument("image")
    v.add_argument("--arch", required=True, choices=ARCHES)
    v.add_argument("--min-generation", type=int, default=1)
    v.add_argument("--public-key", required=True)
    v.add_argument("--manifest", required=True)
    v.add_argument("--signature", required=True)

    args = parser.parse_args()

    try:
        if args.command == "sign":
            sign_image(args)
        else:
            if args.min_generation < 1:
                raise Reject("minimum generation must be positive")
            verify_image(args)
    except (
        Reject, OSError, ValueError, KeyError,
        TypeError, json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"PROOFBOOT REJECT: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
