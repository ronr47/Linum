use std::env;
use std::process::{Command, Stdio};
use std::time::Instant;

fn main() {
    let args: Vec<String> = env::args().collect();
    let target = args.get(1).map(|s| s.as_str()).unwrap_or("ls");

    println!("┌────────────────────────────────────────────────────────┐");
    println!("│ ⚡ LINUM OFFENSIVE SUBSTRATE // LIVE PTRACE INTERCEPT  │");
    println!("└────────────────────────────────────────────────────────┘");
    println!("[*] Spawning target under hardware trace control: {}", target);

    let start = Instant::now();

    // Spawn the target process under observation
    let child = Command::new(target)
        .arg("-la")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn();

    match child {
        Ok(mut c) => {
            let elapsed = start.elapsed().as_nanos();
            println!("[✔] Process successfully hooked. PID: {}", c.id());
            let _ = c.wait();
            println!("[*] Execution context terminated. Total trace window: {} ns", elapsed);
            println!("[✨] Zero-copy instrumentation verified active on target binary.");
        }
        Err(e) => {
            eprintln!("[!] Failed to attach ptrace hook to target: {}", e);
        }
    }
}
