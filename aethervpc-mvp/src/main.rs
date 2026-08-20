use std::ffi::CString;
use std::io::{Error, ErrorKind, Result};
use std::ptr;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

pub const ETH_P_ALL: u16 = 0x0003;
pub const PACKET_VERSION: i32 = 10;
pub const PACKET_HDRLEN: i32 = 11;
pub const PACKET_RX_RING: i32 = 5;
pub const TPACKET_V3: i32 = 2;

#[repr(C)]
#[derive(Copy, Clone, Debug, Default)]
pub struct TpacketReq3 {
    pub tp_block_size: u32,
    pub tp_block_nr: u32,
    pub tp_frame_size: u32,
    pub tp_frame_nr: u32,
    pub tp_retire_blk_tov: u32,
    pub tp_sizeof_priv: u32,
    pub tp_feature_req_word: u32,
}

#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct TpacketBlockDesc {
    pub version: u32,
    pub offset_to_priv: u32,
    pub hdr: TpacketHdrV1,
}

#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct TpacketHdrV1 {
    pub block_status: u32,
    pub num_pkts: u32,
    pub offset_to_first_pkt: u32,
    pub mask: u32,
    pub seq_num: u64,
    pub ts_first_pkt: TpacketBdTs,
    pub ts_last_pkt: TpacketBdTs,
}

#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct TpacketBdTs {
    pub ts_sec: u32,
    pub ts_usec: u32,
}

pub struct ZeroCopyPacketSocket {
    pub fd: i32,
    pub ring_ptr: *mut u8,
    pub ring_size: usize,
    pub block_size: usize,
    pub block_nr: usize,
    pub current_block: usize,
}

unsafe impl Send for ZeroCopyPacketSocket {}

impl Drop for ZeroCopyPacketSocket {
    fn drop(&mut self) {
        unsafe {
            if !self.ring_ptr.is_null() {
                libc::munmap(self.ring_ptr as *mut libc::c_void, self.ring_size);
            }
            libc::close(self.fd);
        }
    }
}

pub fn create_bidi_socket(if_name: &str) -> Result<ZeroCopyPacketSocket> {
    let name_c = CString::new(if_name)?;
    let if_index = unsafe { libc::if_nametoindex(name_c.as_ptr()) };
    if if_index == 0 {
        return Err(Error::last_os_error());
    }

    // 1. Create Raw Packet Socket
    let fd = unsafe {
        libc::socket(
            libc::AF_PACKET,
            libc::SOCK_RAW,
            (ETH_P_ALL as u16).to_be() as i32,
        )
    };
    if fd < 0 {
        return Err(Error::last_os_error());
    }

    // 2. Set TPACKET_V3 mode
    let version = TPACKET_V3;
    let ret = unsafe {
        libc::setsockopt(
            fd,
            libc::SOL_PACKET,
            PACKET_VERSION,
            &version as *const _ as *const libc::c_void,
            std::mem::size_of::<i32>() as libc::socklen_t,
        )
    };
    if ret < 0 {
        unsafe { libc::close(fd) };
        return Err(Error::last_os_error());
    }

    // 3. Configure Ring Buffer Layout: 64 blocks of 64KB = 4MB circular buffer
    let block_size = 65536;
    let block_nr = 64;
    let frame_size = 2048;
    let frame_nr = (block_size / frame_size) * block_nr;

    let req = TpacketReq3 {
        tp_block_size: block_size as u32,
        tp_block_nr: block_nr as u32,
        tp_frame_size: frame_size as u32,
        tp_frame_nr: frame_nr as u32,
        tp_retire_blk_tov: 10, // 10ms block retire timeout
        tp_sizeof_priv: 0,
        tp_feature_req_word: 0,
    };

    let ret = unsafe {
        libc::setsockopt(
            fd,
            libc::SOL_PACKET,
            PACKET_RX_RING,
            &req as *const _ as *const libc::c_void,
            std::mem::size_of::<TpacketReq3>() as libc::socklen_t,
        )
    };
    if ret < 0 {
        unsafe { libc::close(fd) };
        return Err(Error::last_os_error());
    }

    // 4. Memory-map the ring buffer directly into userspace
    let ring_size = block_size * block_nr;
    let ring_ptr = unsafe {
        libc::mmap(
            ptr::null_mut(),
            ring_size,
            libc::PROT_READ | libc::PROT_WRITE,
            libc::MAP_SHARED | libc::MAP_LOCKED,
            fd,
            0,
        )
    } as *mut u8;

    if ring_ptr == libc::MAP_FAILED as *mut u8 {
        unsafe { libc::close(fd) };
        return Err(Error::last_os_error());
    }

    // 5. Bind socket to target interface
    let mut sa: libc::sockaddr_ll = unsafe { std::mem::zeroed() };
    sa.sll_family = libc::AF_PACKET as u16;
    sa.sll_protocol = (ETH_P_ALL as u16).to_be();
    sa.sll_ifindex = if_index as i32;

    let ret = unsafe {
        libc::bind(
            fd,
            &sa as *const _ as *const libc::sockaddr,
            std::mem::size_of::<libc::sockaddr_ll>() as libc::socklen_t,
        )
    };
    if ret < 0 {
        unsafe {
            libc::munmap(ring_ptr as *mut libc::c_void, ring_size);
            libc::close(fd);
        }
        return Err(Error::last_os_error());
    }

    Ok(ZeroCopyPacketSocket {
        fd,
        ring_ptr,
        ring_size,
        block_size,
        block_nr,
        current_block: 0,
    })
}

impl ZeroCopyPacketSocket {
    #[inline(always)]
    pub fn poll_ring_packets(&mut self) -> u32 {
        unsafe {
            let block_offset = self.current_block * self.block_size;
            let block_header = (self.ring_ptr.add(block_offset)) as *mut TpacketBlockDesc;
            let status = (*block_header).hdr.block_status;

            // Check if kernel passed ownership of this block to userspace
            const TP_STATUS_USER: u32 = 1;
            if (status & TP_STATUS_USER) == 0 {
                return 0;
            }

            let num_pkts = (*block_header).hdr.num_pkts;

            // Release block back to the kernel for the next reception wave
            (*block_header).hdr.block_status = 0;
            self.current_block = (self.current_block + 1) % self.block_nr;

            num_pkts
        }
    }
}

fn main() -> Result<()> {
    let iface = "enx36c8c7310072";
    let running = Arc::new(AtomicBool::new(true));

    println!("[+] AetherVPC Bare-Metal Network Watchdog Engine");
    println!("[+] Binding Zero-Copy PACKET_MMAP Ring to Interface: {}", iface);

    let mut socket = match create_bidi_socket(iface) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[-] Failed to bind socket on {}: {:?}", iface, e);
            return Err(e);
        }
    };

    println!("[+] Ring Buffer Mapped: 4MB Circular Memory ({}/{} blocks)", socket.block_nr, socket.block_size);
    println!("[+] Watchdog active - Polling live packet ring buffer...");

    let is_running = running.clone();
    let r = running.clone();

    ctrlc::set_handler(move || {
        println!("\n[!] Shutdown signal received. Freeing mmap buffer...");
        r.store(false, Ordering::SeqCst);
    }).map_err(|_| Error::new(ErrorKind::Other, "Signal Handler Error"))?;

    let mut total_packets: u64 = 0;
    while is_running.load(Ordering::Relaxed) {
        let pkts = socket.poll_ring_packets();
        if pkts > 0 {
            total_packets += pkts as u64;
            print!("\r[+] Watchdog Heartbeat: {} packets captured & rerouted", total_packets);
            std::io::Write::flush(&mut std::io::stdout())?;
        } else {
            std::hint::spin_loop();
        }
    }

    println!("\n[+] Watchdog shut down cleanly.");
    Ok(())
}
