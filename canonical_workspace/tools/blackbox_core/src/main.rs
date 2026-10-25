#![no_std]
#![no_main]

use core::panic::PanicInfo;

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    sys_exit(1);
}

#[inline(always)]
fn sys_exit(code: i32) -> ! {
    unsafe {
        core::arch::asm!(
            "svc #0",
            in("x8") 93,
            in("x0") code,
            options(noreturn)
        );
    }
}

#[inline(always)]
fn sys_write(fd: i32, buf: *const u8, count: usize) -> isize {
    let ret: isize;
    unsafe {
        core::arch::asm!(
            "svc #0",
            in("x8") 64,
            in("x0") fd,
            in("x1") buf,
            in("x2") count,
            lateout("x0") ret,
            clobber_abi("system")
        );
    }
    ret
}

#[inline(always)]
fn sys_openat(dfd: i32, path: *const u8, flags: i32, mode: i32) -> i32 {
    let ret: i32;
    unsafe {
        core::arch::asm!(
            "svc #0",
            in("x8") 56,
            in("x0") dfd,
            in("x1") path,
            in("x2") flags,
            in("x3") mode,
            lateout("x0") ret,
            clobber_abi("system")
        );
    }
    ret
}

#[inline(always)]
fn sys_close(fd: i32) -> i32 {
    let ret: i32;
    unsafe {
        core::arch::asm!(
            "svc #0",
            in("x8") 57,
            in("x0") fd,
            lateout("x0") ret,
            clobber_abi("system")
        );
    }
    ret
}

#[inline(always)]
fn sys_fstat(fd: i32, stat_buf: *mut u8) -> i32 {
    let ret: i32;
    unsafe {
        core::arch::asm!(
            "svc #0",
            in("x8") 80,
            in("x0") fd,
            in("x1") stat_buf,
            lateout("x0") ret,
            clobber_abi("system")
        );
    }
    ret
}

#[inline(always)]
fn sys_mmap(addr: *mut u8, length: usize, prot: i32, flags: i32, fd: i32, offset: i64) -> *mut u8 {
    let ret: *mut u8;
    unsafe {
        core::arch::asm!(
            "svc #0",
            in("x8") 222,
            in("x0") addr,
            in("x1") length,
            in("x2") prot,
            in("x3") flags,
            in("x4") fd,
            in("x5") offset,
            lateout("x0") ret,
            clobber_abi("system")
        );
    }
    ret
}

#[inline(always)]
fn sys_munmap(addr: *mut u8, length: usize) -> i32 {
    let ret: i32;
    unsafe {
        core::arch::asm!(
            "svc #0",
            in("x8") 215,
            in("x0") addr,
            in("x1") length,
            lateout("x0") ret,
            clobber_abi("system")
        );
    }
    ret
}

#[inline(always)]
fn sys_mprotect(addr: *mut u8, length: usize, prot: i32) -> i32 {
    let ret: i32;
    unsafe {
        core::arch::asm!(
            "svc #0",
            in("x8") 226,
            in("x0") addr,
            in("x1") length,
            in("x2") prot,
            lateout("x0") ret,
            clobber_abi("system")
        );
    }
    ret
}

fn write_str(s: &str) {
    sys_write(1, s.as_ptr(), s.len());
}

fn write_hex64(mut val: u64) {
    let hex_chars = b"0123456789abcdef";
    let mut buf = [b'0'; 18];
    buf[0] = b'0';
    buf[1] = b'x';
    for i in (0..16).rev() {
        buf[2 + i] = hex_chars[(val & 0xf) as usize];
        val >>= 4;
    }
    sys_write(1, buf.as_ptr(), 18);
}

fn parse_pe(data: *const u8, len: usize) -> bool {
    if len < 0x40 {
        return false;
    }
    unsafe {
        if *data != b'M' || *data.add(1) != b'Z' {
            return false;
        }
        let e_lfanew = *(data.add(0x3C) as *const u32) as usize;
        if e_lfanew + 24 > len {
            return false;
        }
        let nt_ptr = data.add(e_lfanew);
        if *nt_ptr != b'P' || *nt_ptr.add(1) != b'E' || *nt_ptr.add(2) != 0 || *nt_ptr.add(3) != 0 {
            return false;
        }

        let machine = *(nt_ptr.add(4) as *const u16);
        let num_sections = *(nt_ptr.add(6) as *const u16) as usize;
        let opt_hdr_size = *(nt_ptr.add(20) as *const u16) as usize;

        if machine != 0x8664 && machine != 0xAA64 {
            return false;
        }

        let opt_ptr = nt_ptr.add(24);
        let magic = *(opt_ptr as *const u16);
        if magic != 0x020B {
            return false;
        }

        let entry_point_rva = *(opt_ptr.add(16) as *const u32) as usize;
        let image_base = *(opt_ptr.add(24) as *const u64);
        let section_tbl_offset = e_lfanew + 24 + opt_hdr_size;

        if section_tbl_offset + (num_sections * 40) > len {
            return false;
        }

        write_str("[+] Valid PE32+ Image Verified\n");
        write_str("    ImageBase:        ");
        write_hex64(image_base);
        write_str("\n    EntryPoint RVA:   ");
        write_hex64(entry_point_rva as u64);
        write_str("\n    Section Count:    ");
        write_hex64(num_sections as u64);
        write_str("\n");

        for i in 0..num_sections {
            let sec = data.add(section_tbl_offset + (i * 40));
            let virt_size = *(sec.add(8) as *const u32) as usize;
            let virt_addr = *(sec.add(12) as *const u32) as usize;
            let raw_size = *(sec.add(16) as *const u32) as usize;
            let raw_ptr = *(sec.add(20) as *const u32) as usize;

            if raw_ptr.saturating_add(raw_size) > len {
                write_str("[!] Section raw data bounds violated\n");
                return false;
            }

            if entry_point_rva >= virt_addr && entry_point_rva < virt_addr.saturating_add(virt_size) {
                let ep_offset = entry_point_rva - virt_addr + raw_ptr;
                if ep_offset < len {
                    write_str("    EntryPoint Offset:");
                    write_hex64(ep_offset as u64);
                    write_str("\n");
                }
            }
        }
    }
    true
}

#[no_mangle]
pub extern "C" fn blackbox_main(argc: isize, argv: *const *const u8) -> i32 {
    write_str("[*] BlackBox Core Standalone Binary Forensic Substrate (AArch64)\n");
    if argc < 2 {
        write_str("[-] Usage: blackbox_engine <pe_binary_path>\n");
        return 1;
    }

    let file_path = unsafe { *argv.add(1) };
    let fd = sys_openat(-100, file_path, 0, 0);
    if fd < 0 {
        write_str("[-] Failed to open target PE payload\n");
        return 2;
    }

    let mut stat = [0u8; 144];
    if sys_fstat(fd, stat.as_mut_ptr()) < 0 {
        sys_close(fd);
        write_str("[-] Failed to stat binary payload\n");
        return 3;
    }

    let file_size = unsafe { *(stat.as_ptr().add(48) as *const usize) };
    if file_size == 0 {
        sys_close(fd);
        write_str("[-] Target payload size is zero\n");
        return 4;
    }

    let map_addr = sys_mmap(core::ptr::null_mut(), file_size, 1 | 2, 0x02, fd, 0);
    sys_close(fd);

    if (map_addr as isize) < 0 {
        write_str("[-] Memory mapping failed\n");
        return 5;
    }

    let mprotect_res = sys_mprotect(map_addr, file_size, 1);
    if mprotect_res < 0 {
        sys_munmap(map_addr, file_size);
        write_str("[-] Memory sealing (W^X transition) failed\n");
        return 6;
    }

    let success = parse_pe(map_addr, file_size);
    sys_munmap(map_addr, file_size);

    if success {
        write_str("[+] Canonical Truth Code Target Achieved.\n");
        0x42
    } else {
        write_str("[-] Payload parsing fault.\n");
        7
    }
}
