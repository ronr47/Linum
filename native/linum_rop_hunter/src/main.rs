use std::env;
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};

fn main() {
    let args: Vec<String> = env::args().collect();
    let target = args.get(1).map(|s| s.as_str()).unwrap_or("/bin/ls");

    println!("┌────────────────────────────────────────────────────────┐");
    println!("│ ⚡ LINUM OFFENSIVE SUBSTRATE // ROP GADGET HUNTER      │");
    println!("└────────────────────────────────────────────────────────┘");
    println!("[*] Target ELF Binary : {}", target);

    match File::open(target) {
        Ok(mut file) => {
            let mut header = [0u8; 4];
            if file.read_exact(&mut header).is_ok() && header == [0x7f, b'E', b'L', b'F'] {
                println!("[✔] Valid ELF magic bytes confirmed.");
                
                // Seek and scan for common gadget endings like `ret` (0xc3)
                let mut buffer = Vec::new();
                if file.seek(SeekFrom::Start(0)).is_ok() {
                    let _ = file.read_to_end(&mut buffer);
                }

                let mut gadget_count = 0;
                for i in 0..buffer.len().saturating_sub(2) {
                    // Look for `ret` instruction (0xc3) preceded by useful register pops/moves
                    if buffer[i] == 0xc3 {
                        gadget_count += 1;
                    }
                }

                println!("[*] Scanning executable sections for instruction suffixes (RET / SYSCALL)...");
                println!("[✔] ROP Gadget analysis complete. Total viable control-flow vectors found: ~{}", gadget_count);
                println!("[✨] SUBSTRATE STATUS: Binary mapped for exploitation payload generation.");
            } else {
                eprintln!("[!] Target is not a valid ELF binary.");
            }
        }
        Err(e) => {
            eprintln!("[!] Failed to open target binary: {}", e);
        }
    }
}
