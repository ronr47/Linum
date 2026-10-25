#!/usr/bin/env python3
"""LINUM ProofBoot v0.1: conservative PE/UEFI evidence verifier."""

import argparse
import hashlib
import json
import pathlib
import struct
import sys

MACHINES = {
    0x8664: "x86_64",
    0xAA64: "aarch64",
}
EFI_APPLICATION = 10
EXECUTE = 0x20000000
WRITE = 0x80000000


class Reject(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Reject(message)


def inspect(path, expected_arch=None):
    data = pathlib.Path(path).read_bytes()
    size = len(data)

    def unpack(fmt, offset):
        length = struct.calcsize(fmt)
        require(offset >= 0 and offset + length <= size,
                f"Truncated structure at file offset 0x{offset:X}")
        return struct.unpack_from(fmt, data, offset)

    require(size >= 64, "File is too short for a DOS header")
    require(data[:2] == b"MZ", "Missing MZ signature")

    peoff, = unpack("<I", 0x3C)
    require(peoff + 24 <= size, "Truncated PE header")
    require(data[peoff:peoff + 4] == b"PE\0\0",
            "Missing PE signature")

    machine, nsects, _, _, _, optsize, _ = unpack(
        "<HHIIIHH", peoff + 4
    )
    require(0 < nsects <= 96, "Invalid section count")

    arch = MACHINES.get(machine, f"unknown:0x{machine:04X}")
    require(machine in MACHINES, f"Unsupported architecture: {arch}")
    if expected_arch:
        require(arch == expected_arch,
                f"Expected {expected_arch}, found {arch}")

    opt = peoff + 24
    require(optsize >= 70, "Optional header is too short")
    magic, = unpack("<H", opt)
    require(magic == 0x20B, "Not a PE32+ image")

    entry, = unpack("<I", opt + 16)
    section_align, file_align = unpack("<II", opt + 32)
    size_image, size_headers = unpack("<II", opt + 56)
    subsystem, = unpack("<H", opt + 68)

    require(subsystem == EFI_APPLICATION,
            f"Not a UEFI application: subsystem={subsystem}")
    require(section_align > 0 and file_align > 0,
            "Invalid section/file alignment")
    require(size_headers <= size, "Headers exceed file size")

    table = opt + optsize
    require(table + nsects * 40 <= size,
            "Truncated section table")

    sections = []
    raw_ranges = []
    entry_sections = []

    for i in range(nsects):
        off = table + i * 40
        name_b = data[off:off + 8].split(b"\0", 1)[0]
        name = name_b.decode("ascii", errors="replace")
        vsize, va, rawsize, rawoff = unpack("<IIII", off + 8)
        characteristics, = unpack("<I", off + 36)

        require(rawoff + rawsize <= size,
                f"{name}: raw section exceeds file bounds")

        if rawsize:
            raw_ranges.append((rawoff, rawoff + rawsize, name))

        span = max(vsize, rawsize)
        if span and va <= entry < va + span:
            if characteristics & EXECUTE:
                entry_sections.append(name)

        sections.append({
            "name": name,
            "virtual_address": f"0x{va:X}",
            "virtual_size": vsize,
            "raw_offset": f"0x{rawoff:X}",
            "raw_size": rawsize,
            "executable": bool(characteristics & EXECUTE),
            "writable": bool(characteristics & WRITE),
        })

    raw_ranges.sort()
    for previous, current in zip(raw_ranges, raw_ranges[1:]):
        require(previous[1] <= current[0],
                f"Overlapping raw sections: {previous[2]} / {current[2]}")

    require(bool(entry_sections),
            "Entry point is not in an executable section")

    return {
        "protocol": "LINUM-ProofBoot",
        "protocol_version": "0.1",
        "artifact": pathlib.Path(path).name,
        "file_size": size,
        "sha256": hashlib.sha256(data).hexdigest(),
        "architecture": arch,
        "machine": f"0x{machine:04X}",
        "format": "PE32+",
        "subsystem": "UEFI_APPLICATION",
        "entry_rva": f"0x{entry:X}",
        "section_alignment": section_align,
        "file_alignment": file_align,
        "size_of_image": size_image,
        "size_of_headers": size_headers,
        "sections": sections,
        "entry_sections": entry_sections,
        "checks": {
            "pe_structure": "PASS",
            "architecture": "PASS",
            "uefi_subsystem": "PASS",
            "section_bounds": "PASS",
            "raw_section_overlap": "PASS",
            "executable_entry_point": "PASS",
        },
        "limitations": [
            "Static inspection only; no firmware execution performed.",
            "No signature or trust-policy validation performed.",
            "No hardware shadow-stack state verified.",
            "No measured-boot or TPM attestation performed.",
        ],
        "verdict": "STRUCTURAL_CHECKS_PASS",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--expect-arch",
                        choices=("x86_64", "aarch64"))
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        result = inspect(args.image, args.expect_arch)
        code = 0
    except (Reject, OSError, ValueError, struct.error) as exc:
        result = {
            "protocol": "LINUM-ProofBoot",
            "protocol_version": "0.1",
            "verdict": "REJECTED",
            "reason": str(exc),
        }
        code = 1

    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        pathlib.Path(args.output).write_text(output)
    print(output, end="")
    return code


if __name__ == "__main__":
    sys.exit(main())
