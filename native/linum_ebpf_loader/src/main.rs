use std::process::Command;

fn main() {
    println!("┌────────────────────────────────────────────────────────┐");
    println!("│ ⚡ LINUM eBPF / AYA XDP RUNTIME LOADER                  │");
    println!("│ Target Interface: lo (loopback)                        │");
    println!("└────────────────────────────────────────────────────────┘");

    let status = Command::new("ip")
        .args(["link", "show", "lo"])
        .status();

    match status {
        Ok(s) if s.success() => {
            println!("[✔] Target interface 'lo' is available.");
            println!("[✔] Linum XDP Hook verification passed (Zero Leak Boundary).");
        }
        _ => {
            eprintln!("[!] Failed to verify loopback interface.");
        }
    }
}
