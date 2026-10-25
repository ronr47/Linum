#!/usr/bin/env python3
"""Read-only structural checks for PE32+ EFI images."""

import json
import struct
import sys
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inspect(path):
    data = Path(path).read_bytes()
    require(len(data) >= 64, "File is shorter than the DOS header")
    require(data[:2] == b"MZ", "Missing DOS MZ signature")

    pe = struct.unpack_from("<I", data, 0x3C)[0]
    require(pe + 24 <= len(data), "Truncated PE/COFF header")
    require(data[pe:pe + 4] == b"PE\0\0", "Invalid PE signature")

    machine, count = struct.unpack_from("<HH", data, pe + 4)
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24

    require(machine == 0x8664, f"Unexpected machine: {machine:#x}")
    require(opt + opt_size <= len(data), "Truncated optional header")
    require(opt_size >= 112, "Optional header too short for PE32+")

    magic = struct.unpack_from("<H", data, opt)[0]
    require(magic == 0x20B, f"Expected PE32+, got {magic:#x}")

    entry = struct.unpack_from("<I", data, opt + 16)[0]
    image_base = struct.unpack_from("<Q", data, opt + 24)[0]
    section_align, file_align = struct.unpack_from(
        "<II", data, opt + 32
    )
    size_image, size_headers = struct.unpack_from(
        "<II", data, opt + 56
    )
    subsystem = struct.unpack_from("<H", data, opt + 68)[0]
    directory_count = struct.unpack_from("<I", data, opt + 108)[0]

    require(section_align > 0 and file_align > 0, "Zero alignment")
    require(size_headers <= len(data), "Headers exceed file size")
    require(size_image > 0, "SizeOfImage is zero")
    require(subsystem == 10, f"Not an EFI application: subsystem={subsystem}")

    section_table = opt + opt_size
    table_end = section_table + count * 40
    require(table_end <= len(data), "Truncated section table")
    require(table_end <= size_headers, "Section table exceeds SizeOfHeaders")

    sections = []
    raw_ranges = []
    virtual_ranges = []

    for i in range(count):
        off = section_table + i * 40
        name_raw = data[off:off + 8].split(b"\0", 1)[0]
        name = name_raw.decode("ascii", errors="replace")
        vsize, rva, raw_size, raw_off = struct.unpack_from(
            "<IIII", data, off + 8
        )
        characteristics = struct.unpack_from("<I", data, off + 36)[0]

        require(raw_off + raw_size <= len(data),
                f"{name}: raw data extends beyond file")

        extent = max(vsize, raw_size)
        require(rva + extent <= 0x100000000,
                f"{name}: virtual range overflows 32-bit RVA space")

        if raw_size:
            require(raw_off >= size_headers,
                    f"{name}: raw data overlaps declared headers")
            raw_ranges.append((raw_off, raw_off + raw_size, name))

        if extent:
            virtual_ranges.append((rva, rva + extent, name))

        sections.append({
            "name": name,
            "virtual_address": hex(rva),
            "virtual_size": vsize,
            "raw_offset": hex(raw_off),
            "raw_size": raw_size,
            "characteristics": hex(characteristics),
        })

    def overlaps(ranges):
        ordered = sorted(ranges)
        found = []
        for previous, current in zip(ordered, ordered[1:]):
            if current[0] < previous[1]:
                found.append({
                    "first": previous[2],
                    "second": current[2],
                    "boundary": hex(current[0]),
                })
        return found

    mapped = []
    for s in sections:
        start = int(s["virtual_address"], 16)
        end = start + max(s["virtual_size"], s["raw_size"])
        if start <= entry < end:
            mapped.append(s["name"])

    report = {
        "path": str(Path(path).resolve()),
        "file_size": len(data),
        "machine": hex(machine),
        "optional_magic": hex(magic),
        "pe_offset": hex(pe),
        "entry_rva": hex(entry),
        "preferred_image_base": hex(image_base),
        "section_alignment": section_align,
        "file_alignment": file_align,
        "size_of_image": hex(size_image),
        "size_of_headers": hex(size_headers),
        "subsystem": subsystem,
        "data_directory_count": directory_count,
        "sections": sections,
        "raw_overlaps": overlaps(raw_ranges),
        "virtual_overlaps": overlaps(virtual_ranges),
        "entry_sections": mapped,
    }

    require(not report["raw_overlaps"], "Raw section overlap detected")
    require(not report["virtual_overlaps"], "Virtual section overlap detected")
    require(len(mapped) == 1,
            f"Entry point must map to exactly one section; found {mapped}")

    # Confirm the entry RVA resolves to bytes present in the file.
    entry_section = next(s for s in sections if s["name"] == mapped[0])
    rva = int(entry_section["virtual_address"], 16)
    raw_off = int(entry_section["raw_offset"], 16)
    raw_size = entry_section["raw_size"]
    require(entry - rva < raw_size,
            "Entry point lies in zero-filled data, not file-backed bytes")

    report["entry_file_offset"] = hex(raw_off + entry - rva)
    report["structural_validation"] = "PASS"
    return report


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError(
                f"Usage: {sys.argv[0]} /path/to/BOOTX64.EFI"
            )
        print(json.dumps(inspect(sys.argv[1]), indent=2))
    except (OSError, ValueError, struct.error) as exc:
        print(json.dumps({
            "structural_validation": "FAIL",
            "error": str(exc),
        }), file=sys.stderr)
        sys.exit(1)
