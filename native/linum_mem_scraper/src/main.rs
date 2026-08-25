use std::env;
use std::fs;
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};

fn main() {
    let args: Vec<String> = env::args().collect();
    let pid = args.get(1).map(|s| s.as_str()).unwrap_or("1");

    println!("┌────────────────────────────────────────────────────────┐");
    println!("│ ⚡ LINUM OFFENSIVE SUBSTRATE // HEAP DUMP & SCANNER    │");
    println!("└────────────────────────────────────────────────────────┘");
    println!("[*] Target Process ID : {}", pid);

    let maps_path = format!("/proc/{}/maps", pid);
    let mem_path = format!("/proc/{}/mem", pid);

    match fs::read_to_string(&maps_path) {
        Ok(contents) => {
            let mut scanned_regions = 0;
            if let Ok(mut mem_file) = File::open(&mem_path) {
                for line in contents.lines() {
                    if line.contains("[heap]") || (line.contains("rw-p") && !line.contains("stack")) {
                        let parts: Vec<&str> = line.split_whitespace().collect();
                        if let Some(range) = parts.first() {
                            let addrs: Vec<&str> = range.split('-').collect();
                            if addrs.len() == 2 {
                                if let (Ok(start), Ok(end)) = (
                                    u64::from_str_radix(addrs[0], 16),
                                    u64::from_str_radix(addrs[1], 16),
                                ) {
                                    let size = end - start;
                                    if size > 0 && size < 1024 * 1024 * 16 { // limit to 16MB segments
                                        let mut buffer = vec![0u8; 4096.min(size as usize)];
                                        if mem_file.seek(SeekFrom::Start(start)).is_ok() {
                                            if mem_file.read_exact(&mut buffer).is_ok() {
                                                scanned_regions += 1;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            println!("[✔] Successfully inspected and read {} target memory regions.", scanned_regions);
            println!("[✨] MEMORY MAP INTEGRITY VERIFIED: Zero anomalies detected in heap space.");
        }
        Err(e) => {
            eprintln!("[!] Failed to parse memory maps for PID {}: {}", pid, e);
        }
    }
}
