use std::io::{self, Read, Write};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

pub struct SolidPipeline {
    buffer_size: usize,
    active: Arc<AtomicBool>,
}

impl SolidPipeline {
    pub fn new(buffer_size: usize) -> Self {
        Self {
            buffer_size,
            active: Arc::new(AtomicBool::new(true)),
        }
    }

    pub fn run_pipe<R: Read, W: Write>(&self, mut reader: R, mut writer: W) -> io::Result<()> {
        let mut buf = vec![0u8; self.buffer_size];
        
        while self.active.load(Ordering::Relaxed) {
            let n = match reader.read(&mut buf) {
                Ok(0) => break,
                Ok(n) => n,
                Err(ref e) if e.kind() == io::ErrorKind::Interrupted => continue,
                Err(e) => return Err(e),
            };

            let chunk = &buf[..n];
            writer.write_all(chunk)?;
            writer.flush()?;
        }

        Ok(())
    }

    pub fn halt(&self) {
        self.active.store(false, Ordering::Relaxed);
    }
}
