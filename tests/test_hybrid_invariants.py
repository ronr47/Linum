#!/usr/bin/env python3
"""Regression test for hybrid.exe dual-personality container invariants."""

import os
import struct
import unittest
from pathlib import Path

TARGET = Path(os.environ.get("HOME", "")) / "hybrid.exe"


class TestHybridInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not TARGET.exists():
            raise unittest.SkipTest(f"{TARGET} not found")
        with open(TARGET, "rb") as f:
            cls.raw = f.read(0x400)

    def test_offset_0x3c_e_lfanew(self):
        e_lfanew = struct.unpack_from("<I", self.raw, 0x3C)[0]
        self.assertEqual(e_lfanew, 0x00000080, "e_lfanew must point to 0x80")

    def test_offset_0x40_elf_header(self):
        magic = self.raw[0x40:0x44]
        self.assertEqual(magic, b"\x7fELF", "ELF magic mismatch at 0x40")
        e_type = struct.unpack_from("<H", self.raw, 0x50)[0]
        self.assertEqual(e_type, 0x0002, "e_type must be ET_EXEC (0x0002)")
        e_machine = struct.unpack_from("<H", self.raw, 0x52)[0]
        self.assertEqual(e_machine, 0x003E, "e_machine must be EM_X86_64 (0x003E)")
        e_phoff = struct.unpack_from("<Q", self.raw, 0x60)[0]
        self.assertEqual(e_phoff, 0x00000280, "e_phoff must point to 0x280")
        
        # Canonical offsets from 0x40 base:
        # e_ehsize    @ 0x74 (2 bytes)
        # e_phentsize @ 0x76 (2 bytes)
        # e_phnum     @ 0x78 (2 bytes)
        e_ehsize = struct.unpack_from("<H", self.raw, 0x74)[0]
        e_phentsize = struct.unpack_from("<H", self.raw, 0x76)[0]
        e_phnum = struct.unpack_from("<H", self.raw, 0x78)[0]
        
        self.assertEqual(e_ehsize, 64, "e_ehsize must be 64 bytes")
        self.assertEqual(e_phentsize, 56, "e_phentsize must be 56 bytes")
        self.assertEqual(e_phnum, 1, "e_phnum must be 1")

    def test_offset_0x80_pe_header(self):
        pe_sig = self.raw[0x80:0x84]
        self.assertEqual(pe_sig, b"PE\x00\x00", "PE signature mismatch at 0x80")
        opt_magic = struct.unpack_from("<H", self.raw, 0x98)[0]
        self.assertEqual(opt_magic, 0x020B, "PE Optional Header must be PE32+ (0x020B)")

    def test_offset_0x280_elf_pt_load(self):
        p_type = struct.unpack_from("<I", self.raw, 0x280)[0]
        self.assertEqual(p_type, 1, "p_type at 0x280 must be PT_LOAD (1)")
        p_flags = struct.unpack_from("<I", self.raw, 0x284)[0]
        self.assertEqual(p_flags, 5, "p_flags at 0x284 must be RX (5)")
        p_vaddr = struct.unpack_from("<Q", self.raw, 0x290)[0]
        self.assertEqual(p_vaddr, 0x00400000, "p_vaddr must be 0x00400000")

    def test_zero_aliasing_pe_section_table_and_elf_pt_load(self):
        num_sections = struct.unpack_from("<H", self.raw, 0x86)[0]
        size_opt_hdr = struct.unpack_from("<H", self.raw, 0x94)[0]
        section_table_end = 0x98 + size_opt_hdr + (num_sections * 40)
        self.assertLessEqual(
            section_table_end,
            0x280,
            f"PE section table ends at 0x{section_table_end:X}, colliding with ELF PT_LOAD at 0x280",
        )


if __name__ == "__main__":
    unittest.main()
