"""Read-only PE32+/ELF64 inspector. Never modifies the input binary."""
from __future__ import annotations

import argparse
import json
import logging
import struct
import sys
from pathlib import Path

LOG = logging.getLogger("linum.pe_inspector")
U16 = struct.Struct("<H")
U32 = struct.Struct("<I")
U64 = struct.Struct("<Q")


class FormatError(ValueError):
    """Malformed or truncated executable image."""


def need(buf: bytes, offset: int, size: int, label: str) -> None:
    if offset < 0 or size < 0 or offset > len(buf) or size > len(buf) - offset:
        raise FormatError(
            f"{label} outside file bounds: offset=0x{offset:x}, "
            f"size=0x{size:x}, file_size=0x{len(buf):x}"
        )


def unpack(fmt: struct.Struct, buf: bytes, offset: int, label: str):
    need(buf, offset, fmt.size, label)
    return fmt.unpack_from(buf, offset)[0]


def inspect_pe(buf: bytes) -> dict:
    need(buf, 0, 0x40, "DOS header")
    if buf[:2] != b"MZ":
        raise FormatError("Missing MZ signature")

    pe_offset = unpack(U32, buf, 0x3C, "e_lfanew")
    need(buf, pe_offset, 24, "PE signature and COFF header")
    if buf[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise FormatError("Missing PE signature")

    coff = pe_offset + 4
    machine = unpack(U16, buf, coff, "Machine")
    section_count = unpack(U16, buf, coff + 2, "NumberOfSections")
    optional_size = unpack(U16, buf, coff + 16, "SizeOfOptionalHeader")
    optional = coff + 20
    need(buf, optional, optional_size, "Optional header")

    if optional_size < 2:
        raise FormatError("Optional header is too short")

    magic = unpack(U16, buf, optional, "OptionalHeader.Magic")
    if magic != 0x20B:
        raise FormatError(
            f"Expected PE32+ (0x20b), found 0x{magic:04x}; "
            "PE32 and other formats are not parsed by this template"
        )
    if optional_size < 112:
        raise FormatError("PE32+ optional header too short for required fields")

    entry_rva = unpack(U32, buf, optional + 16, "AddressOfEntryPoint")
    image_base = unpack(U64, buf, optional + 24, "ImageBase")
    section_alignment = unpack(U32, buf, optional + 32, "SectionAlignment")
    file_alignment = unpack(U32, buf, optional + 36, "FileAlignment")
    size_image = unpack(U32, buf, optional + 56, "SizeOfImage")
    size_headers = unpack(U32, buf, optional + 60, "SizeOfHeaders")
    subsystem = unpack(U16, buf, optional + 68, "Subsystem")

    section_table = optional + optional_size
    table_size = section_count * 40
    need(buf, section_table, table_size, "Section table")

    sections = []
    raw_ranges = []
    virtual_ranges = []

    for i in range(section_count):
        off = section_table + i * 40
        raw_name = buf[off:off + 8].split(b"\0", 1)[0]
        name = raw_name.decode("ascii", errors="replace")
        vsize, va, raw_size, raw_offset = struct.unpack_from(
            "<IIII", buf, off + 8
        )
        characteristics = unpack(U32, buf, off + 36, "Section.Characteristics")

        if raw_size:
            need(buf, raw_offset, raw_size, f"{name} raw data")
            raw_ranges.append((raw_offset, raw_offset + raw_size, name))

        if vsize or raw_size:
            span = max(vsize, raw_size)
            virtual_ranges.append((va, va + span, name))

        sections.append({
            "name": name,
            "virtual_size": vsize,
            "virtual_address": va,
            "raw_size": raw_size,
            "raw_offset": raw_offset,
            "characteristics": f"0x{characteristics:08x}",
        })

    def overlaps(ranges):
        ordered = sorted(ranges)
        found = []
        for left, right in zip(ordered, ordered[1:]):
            if right[0] < left[1]:
                found.append({
                    "first": left[2],
                    "second": right[2],
                    "first_end": f"0x{left[1]:x}",
                    "second_start": f"0x{right[0]:x}",
                })
        return found

    # These are diagnostics, not a complete PE conformance proof.
    raw_overlaps = overlaps(raw_ranges)
    virtual_overlaps = overlaps(virtual_ranges)

    return {
        "format": "PE32+",
        "machine": f"0x{machine:04x}",
        "machine_name": {
            0x8664: "AMD64",
            0xAA64: "ARM64",
            0x14C: "I386",
        }.get(machine, "unknown"),
        "pe_offset": f"0x{pe_offset:x}",
        "entry_rva": f"0x{entry_rva:x}",
        "image_base": f"0x{image_base:x}",
        "entry_va_preferred": f"0x{image_base + entry_rva:x}",
        "section_alignment": section_alignment,
        "file_alignment": file_alignment,
        "size_of_image": f"0x{size_image:x}",
        "size_of_headers": f"0x{size_headers:x}",
        "subsystem": subsystem,
        "sections": sections,
        "raw_section_overlaps": raw_overlaps,
        "virtual_section_overlaps": virtual_overlaps,
        "notes": [
            "Preferred entry VA is not proof of runtime mapping.",
            "Overlap checks are diagnostics, not full loader validation.",
            "Imports, relocations, checksums, and entry-point mapping "
            "require additional validation."
        ],
    }


def inspect_elf(buf: bytes) -> dict:
    need(buf, 0, 64, "ELF64 header")
    if buf[:4] != b"\x7fELF":
        raise FormatError("Missing ELF magic")
    if buf[4] != 2:
        raise FormatError("Only ELFCLASS64 is supported")
    if buf[5] != 1:
        raise FormatError("Only little-endian ELF is supported")
    if buf[6] != 1:
        raise FormatError("Unsupported ELF identification version")

    e_type, machine = struct.unpack_from("<HH", buf, 16)
    version = unpack(U32, buf, 20, "e_version")
    entry = unpack(U64, buf, 24, "e_entry")
    phoff = unpack(U64, buf, 32, "e_phoff")
    shoff = unpack(U64, buf, 40, "e_shoff")
    ehsize = unpack(U16, buf, 52, "e_ehsize")
    phentsize = unpack(U16, buf, 54, "e_phentsize")
    phnum = unpack(U16, buf, 56, "e_phnum")
    shentsize = unpack(U16, buf, 58, "e_shentsize")
    shnum = unpack(U16, buf, 60, "e_shnum")

    if ehsize < 64:
        raise FormatError("ELF64 header size is too small")
    if phnum:
        if phentsize < 56:
            raise FormatError("ELF64 program-header entries are too small")
        need(buf, phoff, phentsize * phnum, "Program header table")
    if shnum:
        if shentsize < 64:
            raise FormatError("ELF64 section-header entries are too small")
        need(buf, shoff, shentsize * shnum, "Section header table")

    segments = []
    for i in range(phnum):
        off = phoff + i * phentsize
        p_type, p_flags = struct.unpack_from("<II", buf, off)
        p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = (
            struct.unpack_from("<QQQQQQ", buf, off + 8)
        )
        if p_filesz:
            need(buf, p_offset, p_filesz, f"Program segment {i}")
        segments.append({
            "type": p_type,
            "flags": p_flags,
            "offset": f"0x{p_offset:x}",
            "virtual_address": f"0x{p_vaddr:x}",
            "file_size": p_filesz,
            "memory_size": p_memsz,
            "alignment": p_align,
        })

    return {
        "format": "ELF64",
        "type": e_type,
        "machine": machine,
        "machine_name": {
            3: "i386",
            62: "x86-64",
            183: "AArch64",
        }.get(machine, "unknown"),
        "version": version,
        "entry": f"0x{entry:x}",
        "program_header_offset": phoff,
        "section_header_offset": shoff,
        "program_headers": segments,
        "notes": [
            "Header bounds are checked; this is not a full ELF verifier.",
            "Extended ELF numbering and all ABI constraints are not yet handled."
        ],
    }


def inspect_file(path: Path) -> dict:
    try:
        buf = path.read_bytes()
    except OSError as exc:
        raise FormatError(f"Cannot read {path}: {exc}") from exc

    if not buf:
        raise FormatError("Input file is empty")

    if buf.startswith(b"MZ"):
        result = inspect_pe(buf)
    elif buf.startswith(b"\x7fELF"):
        result = inspect_elf(buf)
    else:
        raise FormatError("Unrecognized format: expected PE (MZ) or ELF magic")

    result["path"] = str(path.resolve())
    result["file_size"] = len(buf)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only PE32+/ELF64 header and section/segment inspection"
    )
    parser.add_argument("file", type=Path, help="Path to an existing binary")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--log", type=Path, help="Optional structured log file")
    args = parser.parse_args()

    handlers = [logging.StreamHandler(sys.stderr)]
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(args.log, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format='{"level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
        handlers=handlers,
    )

    if not args.file.is_file():
        LOG.error("Input is not an existing regular file: %s", args.file)
        return 2

    try:
        result = inspect_file(args.file)
    except (FormatError, struct.error, OverflowError) as exc:
        LOG.error("Inspection failed: %s", exc)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Format: {result['format']}")
        print(f"Path: {result['path']}")
        print(f"Size: {result['file_size']} bytes")
        print(f"Architecture: {result.get('machine_name', 'unknown')}")
        print(f"Entry: {result.get('entry_rva', result.get('entry', 'unknown'))}")
        for section in result.get("sections", []):
            print(
                f"  {section['name']!r}: "
                f"RVA={section['virtual_address']:#x} "
                f"file_offset={section['raw_offset']:#x} "
                f"raw_size={section['raw_size']:#x}"
            )
        for item in result.get("raw_section_overlaps", []):
            print(f"WARNING raw overlap: {item}")
        for item in result.get("virtual_section_overlaps", []):
            print(f"WARNING virtual overlap: {item}")
        for note in result.get("notes", []):
            print(f"NOTE: {note}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
