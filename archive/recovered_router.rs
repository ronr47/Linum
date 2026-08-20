nst XDP_TX_RING: i32 = 3;
pub const XDP_UMEM_FILL_RING: i32 = 4;
pub const XDP_UMEM_COMP_RING: i32 = 5;
pub const XDP_UMEM_REG: i32 = 6;
pub const XDP_ZEROCOPY: u32 = 1 << 2;

#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct XdpUmemReg {
    pub addr: u64,
    pub len: u64,
    pub chunk_size: u32,
    pub headroom: u32,
    pub flags: u32,
}

#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct XdpMmapOffsets {
    pub rx: XdpRingOffset,
    pub tx: XdpRingOffset,
    pub fr: XdpRingOffset,
    pub cr: XdpRingOffset,
}

#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct XdpRingOffset {
    pub producer: u64,
    pub consumer: u64,
    pub desc: u64,
    pub flags: u64,
}

#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct XdpDesc {
    pub addr: u64,
    pub len: u32,
    pub options: u32,
}

#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct SockaddrXdp {
    pub sxdp_family: u16,
    pub sxdp_flags: u16,
    pub sxdp_ifindex: u32,
    pub sxdp_queue_id: u32,
    pub sxdp_shared_umem_fd: u32,
}

pub struct RingBuffer {
    pub cached_prod: u32,
    pub cached_cons: u32,
    pub mask: u32,
    pub size: u32,
    pub producer: *mut u32,
    pub consumer: *mut u32,
    pub desc: *mut libc::c_void,
    pub flags: *mut u32,
}

unsafe impl Send for RingBuffer {}

pub struct UmemAllocation {
    pub mem_ptr: *mut libc::c_void,
    pub size: usize,
}

unsafe impl Send for UmemAllocation {}

impl Drop for UmemAllocation {
    fn drop(&mut self) {
        unsafe {
            libc::munmap(self.mem_ptr, self.size);
        }
    }
}

pub struct AfXdpBidiSocket {
    pub fd: i32,
    pub rx_ring: RingBuffer,
    pub tx_ring: RingBuffer,
    pub fill_ring: RingBuffer,
    pub comp_ring: RingBuffer,
    pub umem: UmemAllocation,
    pub rx_map_ptr: *mut libc::c_void,
    pub rx_map_size: usize,
    pub tx_map_ptr: *mut libc::c_void,
    pub tx_map_size: usize,
    pub next_free_umem_frame: u32,
}

unsafe impl Send for AfXdpBidiSocket {}

impl Drop for AfXdpBidiSocket {
    fn drop(&mut self) {
        unsafe {
            libc::munmap(self.rx_map_ptr, self.rx_map_size);
            libc::munmap(self.tx_map_ptr, self.tx_map_size);
            libc::close(self.fd);
        }
    }
}

pub fn create_bidi_socket(if_name: &str, queue_id: u32) -> Result<AfXdpBidiSocket> {
    let name_c = CString::new(if_name)?;
    let if_index = unsafe { libc::if_nametoindex(name_c.as_ptr()) };
    if if_index == 0 {
        return Err(Error::last_os_error());
    }

    let fd = unsafe { libc::socket(libc::AF_XDP, libc::SOCK_RAW, 0) };
    if fd < 0 {
        return Err(Error::last_os_error());
    }

    let total_frames = XSK_RING_PROD__DEFAULT_NUM_DESCS * 2;
    let umem_size = (total_frames * XSK_UMEM__DEFAULT_FRAME_SIZE) as usize;
    
    let umem_ptr = unsafe {
        libc::mmap(
            ptr::null_mut(),
            umem_size,
            libc::PROT_READ | libc::PROT_WRITE,
            libc::MAP_PRIVATE | libc::MAP_ANONYMOUS | libc::MAP_HUGETLB,
            -1,
            0,
        )
    };
    
    let umem_ptr = if umem_ptr == libc::MAP_FAILED {
        unsafe {
            libc::mmap(
                ptr::null_mut(),
                umem_size,
                libc::PROT_READ | libc::PROT_WRITE,
                libc::MAP_PRIVATE | libc::MAP_ANONYMOUS,
                -1,
                0,
            )
        }
    } else {
        umem_ptr
    };

    if umem_ptr == libc::MAP_FAILED {
        unsafe { libc::close(fd) };
        return Err(Error::last_os_error());
    }
    let umem = UmemAllocation { mem_ptr: umem_ptr, size: umem_size };

    let u_reg = XdpUmemReg {
        addr: umem_ptr as u64,
        len: umem_size as u64,
        chunk_size: XSK_UMEM__DEFAULT_FRAME_SIZE,
        headroom: 0,
        flags: 0,
    };

    let ret = unsafe {
        libc::setsockopt(
            fd,
            SOL_XDP,
            XDP_UMEM_REG,
            &u_reg as *const _ as *const libc::c_void,
            std::mem::size_of::<XdpUmemReg>() as libc::socklen_t,
        )
    };
    if ret < 0 {
        unsafe { libc::close(fd) };
        return Err(Error::last_os_error());
    }

    let n_descriptors = XSK_RING_PROD__DEFAULT_NUM_DESCS;
    for &opt in &[XDP_RX_RING, XDP_TX_RING, XDP_UMEM_FILL_RING, XDP_UMEM_COMP_RING] {
        let ret = unsafe {
            libc::setsockopt(
                fd,
                SOL_XDP,
                opt,
                &n_descriptors as *const _ as *const libc::c_void,
                std::mem::size_of::<u32>() as libc::socklen_t,
            )
        };
        if ret < 0 {
            unsafe { libc::close(fd) };
            return Err(Error::last_os_error());
        }
    }

    let mut offsets = XdpMmapOffsets {
        rx: XdpRingOffset { producer: 0, consumer: 0, desc: 0, flags: 0 },
        tx: XdpRingOffset { producer: 0, consumer: 0, desc: 0, flags: 0 },
        fr: XdpRingOffset { producer: 0, consumer: 0, desc: 0, flags: 0 },
        cr: XdpRingOffset { producer: 0, consumer: 0, desc: 0, flags: 0 },
    };
    let mut optlen = std::mem::size_of::<XdpMmapOffsets>() as libc::socklen_t;

    let ret = unsafe {
        libc::getsockopt(
            fd,
            SOL_XDP,
            XDP_MMAP_OFFSETS,
            &mut offsets as *mut _ as *mut libc::c_void,
            &mut optlen,
        )
    };
    if ret < 0 {
        unsafe { libc::close(fd) };
        return Err(Error::last_os_error());
    }

    let rx_map_size = (offsets.rx.desc + (XSK_RING_CONS__DEFAULT_NUM_DESCS as u64 * std::mem::size_of::<XdpDesc>() as u64)) as usize;
    let rx_map = unsafe {
        libc::mmap(
            ptr::null_mut(),
            rx_map_size,
            libc::PROT_READ | libc::PROT_WRITE,
            libc::MAP_SHARED,
            fd,
            0x000000000, 
        )
    };
    if rx_map == libc::MAP_FAILED {
        unsafe { libc::close(fd) };
        return Err(Error::last_os_error());
    }

    let rx_ring = RingBuffer {
        cached_prod: 0,
        cached_cons: 0,
        mask: XSK_RING_CONS__DEFAULT_NUM_DESCS - 1,
        size: XSK_RING_CONS__DEFAULT_NUM_DESCS,
        producer: (rx_map as usize + offsets.rx.producer as usize) as *mut u32,
        consumer: (rx_map as usize + offsets.rx.consumer as usize) as *mut u32,
        desc: (rx_map as usize + offsets.rx.desc as usize) as *mut libc::c_void,
        flags: (rx_map as usize + offsets.rx.flags as usize) as *mut u32,
    };

    let fill_ring = RingBuffer {
        cached_prod: 0,
        cached_cons: XSK_RING_PROD__DEFAULT_NUM_DESCS,
        mask: XSK_RING_PROD__DEFAULT_NUM_DESCS - 1,
        size: XSK_RING_PROD__DEFAULT_NUM_DESCS,
        producer: (rx_map as usize + offsets.fr.producer as usize) as *mut u32,
        consumer: (rx_map as usize + offsets.fr.consumer as usize) as *mut u32,
        desc: (rx_map as usize + offsets.fr.desc as usize) as *mut libc::c_void,
        flags: (rx_map as usize + offsets.fr.flags as usize) as *mut u32,
    };

    let tx_map_size = (offsets.tx.desc + (XSK_RING_PROD__DEFAULT_NUM_DESCS as u64 * std::mem::size_of::<XdpDesc>() as u64)) as usize;
    let tx_map = unsafe {
        libc::mmap(
            ptr::null_mut(),
            tx_map_size,
            libc::PROT_READ | libc::PROT_WRITE,
            libc::MAP_SHARED,
            fd,
            0x100000000, 
        )
    };
    if tx_map == libc::MAP_FAILED {
        unsafe {
            libc::munmap(rx_map, rx_map_size);
            libc::close(fd);
        }
        return Err(Error::last_os_error());
    }

    let tx_ring = RingBuffer {
        cached_prod: 0,
        cached_cons: XSK_RING_PROD__DEFAULT_NUM_DESCS,
        mask: XSK_RING_PROD__DEFAULT_NUM_DESCS - 1,
        size: XSK_RING_PROD__DEFAULT_NUM_DESCS,
        producer: (tx_map as usize + offsets.tx.producer as usize) as *mut u32,
        consumer: (tx_map as usize + offsets.tx.consumer as usize) as *mut u32,
        desc: (tx_map as usize + offsets.tx.desc as usize) as *mut libc::c_void,
        flags: (tx_map as usize + offsets.tx.flags as usize) as *mut u32,
    };

    let comp_ring = RingBuffer {
        cached_prod: 0,
        cached_cons: 0,
        mask: XSK_RING_CONS__DEFAULT_NUM_DESCS - 1,
        size: XSK_RING_CONS__DEFAULT_NUM_DESCS,
        producer: (tx_map as usize + offsets.cr.producer as usize) as *mut u32,
        consumer: (tx_map as usize + offsets.cr.consumer as usize) as *mut u32,
        desc: (tx_map as usize + offsets.cr.desc as usize) as *mut libc::c_void,
        flags: (tx_map as usize + offsets.cr.flags as usize) as *mut u32,
    };

    let sxdp = SockaddrXdp {
        sxdp_family: libc::AF_XDP as u16,
        sxdp_flags: XDP_ZEROCOPY as u16,
        sxdp_ifindex: if_index,
        sxdp_queue_id: queue_id,
        sxdp_shared_umem_fd: 0,
    };

    let ret = unsafe {
        libc::bind(
            fd,
            &sxdp as *const _ as *const libc::sockaddr,
            std::mem::size_of::<SockaddrXdp>() as libc::socklen_t,
        )
    };
    if ret < 0 {
        unsafe {
            libc::munmap(rx_map, rx_map_size);
            libc::munmap(tx_map, tx_map_size);
            libc::close(fd);
        }
        return Err(Error::last_os_error());
    }

    Ok(AfXdpBidiSocket {
        fd,
        rx_ring,
        tx_ring,
        fill_ring,
        comp_ring,
        umem,
        rx_map_ptr: rx_map,
        rx_map_size,
        tx_map_ptr: tx_map,
        tx_map_size,
        next_free_umem_frame: 0,
    })
}

impl AfXdpBidiSocket {
    #[inline(always)]
    pub fn seed_fill_ring(&mut self) {
        unsafe {
            let prod = self.fill_ring.cached_prod;
            let idx_count = self.fill_ring.size;
            let mut current_prod = prod;

            for _ in 0..idx_count {
                let idx = current_prod & self.fill_ring.mask;
                let desc_ptr = (self.fill_ring.desc as usize + (idx as usize * std::mem::size_of::<u64>())) as *mut u64;
                *desc_ptr = (self.next_free_umem_frame * XSK_UMEM__DEFAULT_FRAME_SIZE) as u64;
                self.next_free_umem_frame += 1;
                current_prod = current_prod.wrapping_add(1);
            }
            compiler_fence(Ordering::Release);
            core::ptr::write_volatile(self.fill_ring.producer, current_prod);
            self.fill_ring.cached_prod = current_prod;
        }
    }

    #[inline(always)]
    pub fn execute_zero_copy_reflection(&mut self) -> u32 {
        unsafe {
            let comp_prod = core::ptr::read_volatile(self.comp_ring.producer);
            let mut comp_cons = self.comp_ring.cached_cons;
            let completed_frames = comp_prod.wrapping_sub(comp_cons);

            if completed_frames > 0 {
                let fill_prod = self.fill_ring.cached_prod;
                let mut current_fill_prod = fill_prod;

                for i in 0..completed_frames {
                    let comp_idx = comp_cons.wrapping_add(i) & self.comp_ring.mask;
                    let completed_addr_ptr = (self.comp_ring.desc as usize + (comp_idx as usize * std::mem::size_of::<u64>())) as *const u64;
                    let recycled_addr = *completed_addr_ptr;

                    let fill_idx = current_fill_prod & self.fill_ring.mask;
                    let fill_desc_ptr = (self.fill_ring.desc as usize + (fill_idx as usize * std::mem::size_of::<u64>())) as *mut u64;
                    *fill_desc_ptr = recycled_addr;

                    current_fill_prod = current_fill_prod.wrapping_add(1);
                }

                compiler_fence(Ordering::Release);
                comp_cons = comp_cons.wrapping_add(completed_frames);
                core::ptr::write_volatile(self.comp_ring.consumer, comp_cons);
                self.comp_ring.cached_cons = comp_cons;

                core::ptr::write_volatile(self.fill_ring.producer, current_fill_prod);
                self.fill_ring.cached_prod = current_fill_prod;
            }

            let rx_prod = core::ptr::read_volatile(self.rx_ring.producer);
            compiler_fence(Ordering::Acquire);
            let rx_cons = self.rx_ring.cached_cons;
            let rx_batch = rx_prod.wrapping_sub(rx_cons);

            if rx_batch == 0 {
                return 0;
            }

            let tx_cons = core::ptr::read_volatile(self.tx_ring.consumer);
            let tx_prod = self.tx_ring.cached_prod;
            let tx_avail = self.tx_ring.size.wrapping_sub(tx_prod.wrapping_sub(tx_cons));

            let loop_count = std::cmp::min(rx_batch, tx_avail);
            if loop_count == 0 {
                return 0;
            }

            let mut current_tx_prod = tx_prod;

            for i in 0..loop_count {
                let rx_idx = rx_cons.wrapping_add(i) & self.rx_ring.mask;
                let rx_desc_ptr = (self.rx_ring.desc as usize + (rx_idx as usize * std::mem::size_of::<XdpDesc>())) as *const XdpDesc;
                
                let raw_addr = (*rx_desc_ptr).addr;
                let raw_len = (*rx_desc_ptr).len;

                let tx_idx = current_tx_prod & self.tx_ring.mask;
                let tx_desc_ptr = (self.tx_ring.desc as usize + (tx_idx as usize * std::mem::size_of::<XdpDesc>())) as *mut XdpDesc;
                
                (*tx_desc_ptr).addr = raw_addr;
                (*tx_desc_ptr).len = raw_len;
                (*tx_desc_ptr).options = 0;

                current_tx_prod = current_tx_prod.wrapping_add(1);
            }

            compiler_fence(Ordering::Release);

            let next_rx_cons = rx_cons.wrapping_add(loop_count);
            core::ptr::write_volatile(self.rx_ring.consumer, next_rx_cons);
            self.rx_ring.cached_cons = next_rx_cons;

            core::ptr::write_volatile(self.tx_ring.producer, current_tx_prod);
            self.tx_ring.cached_prod = current_tx_prod;

            let ret = libc::sendto(
                self.fd,
                ptr::null(),
                0,
                libc::MSG_DONTWAIT,
                ptr::null(),
                0,
            );
            if ret < 0 {
                let err = Error::last_os_error();
                if err.kind() != ErrorKind::WouldBlock {
                    // Handled safely
                }
            }

            loop_count
        }
    }
}

fn main() -> Result<()> {
    let num_cores = thread::available_parallelism().map(|n| n.get()).unwrap_or(2);
    let running = Arc::new(AtomicBool::new(true));
    let mut handles = Vec::with_capacity(num_cores);

    for queue_id in 0..num_cores as u32 {
        let is_running = running.clone();
        let handle = thread::spawn(move || -> Result<()> {
            let mut cpu_set: libc::cpu_set_t = unsafe { std::mem::zeroed() };
            unsafe {
                libc::CPU_SET(queue_id as usize, &mut cpu_set);
                let ret = libc::sched_setaffinity(0, std::mem::size_of::<libc::cpu_set_t>(), &cpu_set);
                if ret < 0 {
                    return Err(Error::last_os_error());
                }
            }

            let mut socket = create_bidi_socket("eth0", queue_id)?;
            socket.seed_fill_ring();

            while is_running.load(Ordering::Relaxed) {
                let reflected = socket.execute_zero_copy_reflection();
                if reflected == 0 {
                    std::hint::spin_loop();
                }
            }
            Ok(())
        });
        handles.push(handle);
    }

    let r = running.clone();
    ctrlc::set_handler(move || {
        r.store(false, Ordering::SeqCst);
    }).map_err(|_| Error::new(ErrorKind::Other, "Signal Handler Error"))?;

    for handle in handles {
        handle.join().map_err(|_| Error::new(ErrorKind::Other, "Thread Execution Panic"))??;
    }
    Ok(())
}
EOF
cargo build --release
sudo ./target/release/aethervpc-mvp

