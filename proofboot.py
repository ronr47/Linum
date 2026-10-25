#!/usr/bin/env python3
"""ProofBoot PB-001: architecture evidence and image integrity."""

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

POLICY = "proofboot-pb001-v1"

# PE COFF Machine identifiers.
PE_MACHINES = {
    0x8664: "x86_64",
    0xAA64: "aarch64",
}

# ELF e_machine identifiers.
ELF_MACHINES = {
    62: "x86_64",    # EM_X86_64
    183: "aarch64",  # EM_AARCH64
}


class Reject(Exception):
    pass


def inspect(data):
    """Derive format and architecture from binary bytes."""

    if len(data) < 64:
        raise Reject("truncated header")

    # PE/COFF, including PE32+ EFI applications.
    if data[:2] == b"MZ":
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]

        if pe_offset + 24 > len(data):
            raise Reject("truncated PE header")
        if data[pe_offset:pe_offset + 4] != b"PE\0\0":
            raise Reject("invalid PE signature")

        machine, sections = struct.unpack_from(
            "<HH", data, pe_offset + 4
        )
        optional_size = struct.unpack_from(
            "<H", data, pe_offset + 20
        )[0]
        optional = pe_offset + 24

        if optional + optional_size > len(data):
            raise Reject("truncated PE optional header")
        if optional_size < 2:
            raise Reject("missing PE optional header")

        magic = struct.unpack_from("<H", data, optional)[0]
        if magic != 0x20B:
            raise Reject("not PE32+")

        if machine not in PE_MACHINES:
            raise Reject(f"unsupported PE machine: 0x{machine:04x}")

        subsystem = struct.unpack_from(
            "<H", data, optional + 68
        )[0] if optional_size >= 70 else None

        return {
            "format": "PE32+",
            "architecture": PE_MACHINES[machine],
            "machine": machine,
            "sections": sections,
            "subsystem": subsystem,
        }

    # ELF64, either little- or big-endian.
    if data[:4] == b"\x7fELF":
        if data[4] != 2:
            raise Reject("not ELF64")
        if data[5] not in (1, 2):
            raise Reject("invalid ELF byte order")

        endian = "<" if data[5] == 1 else ">"
        machine = struct.unpack_from(endian + "H", data, 18)[0]

        if machine not in ELF_MACHINES:
            raise Reject(f"unsupported ELF machine: {machine}")

        return {
            "format": "ELF64",
            "architecture": ELF_MACHINES[machine],
            "machine": machine,
        }

    raise Reject("unsupported executable format")


def measure(path):
    data = Path(path).read_bytes()
    evidence = inspect(data)
    return {
        "policy": POLICY,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        **evidence,
    }


def verify(path, manifest_path, expected_arch):
    actual = measure(path)
    manifest = json.loads(Path(manifest_path).read_text())

    checks = {
        "policy_version": manifest.get("policy") == POLICY,
        "architecture_claim": manifest.get("architecture") == expected_arch,
        "binary_architecture": actual["architecture"] == expected_arch,
        "format_matches": manifest.get("format") == actual["format"],
        "size_matches": manifest.get("size") == actual["size"],
        "sha256_matches": manifest.get("sha256") == actual["sha256"],
    }

    for name, passed in checks.items():
        print(f'{"PASS" if passed else "REJECT"}: {name}')

    if not all(checks.values()):
        raise Reject("verification policy rejected the image")

    print("PROOFBOOT DECISION: ACCEPT (PB-001 prototype)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    m = sub.add_parser("measure", help="create a reference manifest")
    m.add_argument("image")
    m.add_argument("--out", required=True)

    v = sub.add_parser("verify", help="verify image against manifest")
    v.add_argument("image")
    v.add_argument("--manifest", required=True)
    v.add_argument("--arch", required=True,
                   choices=("x86_64", "aarch64"))

    args = parser.parse_args()

    try:
        if args.command == "measure":
            evidence = measure(args.image)
            Path(args.out).write_text(
                json.dumps(evidence, indent=2) + "\n"
            )
            print(json.dumps(evidence, indent=2))
        else:
            verify(args.image, args.manifest, args.arch)
    except (Reject, OSError, ValueError, KeyError, struct.error) as exc:
        print(f"PROOFBOOT REJECT: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
