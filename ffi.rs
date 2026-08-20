#![no_std]
#![no_main]

use core::sync::atomic::{AtomicBool, Ordering};

pub const WILC_SPI_REG_BASE: u32 = 0x1000;
pub const WILC_SPI_CTL_REG: u32 = WILC_SPI_REG_BASE + 0x00;
pub const WILC_SPI_INT_STATUS: u32 = WILC_SPI_REG_BASE + 0x04;
pub const WILC_MAC_ADDR_LO: u32 = 0x4000;
pub const WILC_MAC_ADDR_HI: u32 = 0x4004;
pub const RING_BUFFER_SIZE: usize = 8;
pub const PACKET_MAX_SIZE: usize = 1536;

pub static INT_TRIGGERED: AtomicBool = AtomicBool::new(false);

#[derive(Copy, Clone)]
#[repr(C, align(64))]
pub struct DmaDescriptor {
    pub bus_addr: u32,
    pub length: u32,
    pub status: u32,
    pub next_desc: u32,
    pub _pad: [u32; 12],
}

#[repr(C, align(64))]
pub struct RingBuffer {
    pub descriptors: [DmaDescriptor; RING_BUFFER_SIZE],
    pub buffers: [[u8; PACKET_MAX_SIZE]; RING_BUFFER_SIZE],
    pub head: usize,
    pub tail: usize,
}

impl RingBuffer {
    pub const fn new() -> Self {
        Self {
            descriptors: [DmaDescriptor { bus_addr: 0, length: 0, status: 0, next_desc: 0, _pad: [0; 12] }; RING_BUFFER_SIZE],
            buffers: [[0u8; PACKET_MAX_SIZE]; RING_BUFFER_SIZE],
            head: 0,
            tail: 0,
        }
    }

    pub fn init(&mut self) {
        for i in 0..RING_BUFFER_SIZE {
            self.descriptors[i].bus_addr = self.buffers[i].as_ptr() as u32;
            self.descriptors[i].length = PACKET_MAX_SIZE as u32;
            self.descriptors[i].status = 0x8000_0000;
            if i == RING_BUFFER_SIZE - 1 {
                self.descriptors[i].next_desc = &self.descriptors[0] as *const DmaDescriptor as u32;
            } else {
                self.descriptors[i].next_desc = &self.descriptors[i + 1] as *const DmaDescriptor as u32;
            }
        }
    }
}

#[repr(C)]
pub struct CSpiVTable {
    pub context: *mut (),
    pub select: unsafe extern "C" fn(ctx: *mut ()),
    pub deselect: unsafe extern "C" fn(ctx: *mut ()),
    pub transfer_block: unsafe extern "C" fn(ctx: *mut (), tx_buf: *const u8, rx_buf: *mut u8, len: usize),
}

pub trait SpiTransport {
    fn select(&self);
    fn deselect(&self);
    fn transfer_block(&self, tx_buf: &[u8], rx_buf: &mut [u8]);
}

impl SpiTransport for CSpiVTable {
    #[inline(always)]
    fn select(&self) {
        unsafe { (self.select)(self.context) };
    }

    #[inline(always)]
    fn deselect(&self) {
        unsafe { (self.deselect)(self.context) };
    }

    #[inline(always)]
    fn transfer_block(&self, tx_buf: &[u8], rx_buf: &mut [u8]) {
        let len = if !tx_buf.is_empty() {
            tx_buf.len()
        } else {
            rx_buf.len()
        };
        let tx_ptr = if tx_buf.is_empty() { core::ptr::null() } else { tx_buf.as_ptr() };
        let rx_ptr = if rx_buf.is_empty() { core::ptr::null_mut() } else { rx_buf.as_mut_ptr() };
        unsafe { (self.transfer_block)(self.context, tx_ptr, rx_ptr, len) };
    }
}

#[repr(C)]
pub struct WilcDriver<SPI: SpiTransport> {
    pub spi: SPI,
    pub rx_ring: RingBuffer,
    pub tx_ring: RingBuffer,
}

impl<SPI: SpiTransport> WilcDriver<SPI> {
    pub const fn new(spi: SPI) -> Self {
        Self {
            spi,
            rx_ring: RingBuffer::new(),
            tx_ring: RingBuffer::new(),
        }
    }

    unsafe fn write_reg(&self, reg: u32, value: u32) {
        self.spi.select();
        let cmd = [
            0x0A,
            ((reg >> 16) & 0xFF) as u8,
            ((reg >> 8) & 0xFF) as u8,
            (reg & 0xFF) as u8,
            (value & 0xFF) as u8,
            ((value >> 8) & 0xFF) as u8,
            ((value >> 16) & 0xFF) as u8,
            ((value >> 24) & 0xFF) as u8,
        ];
        self.spi.transfer_block(&cmd, &mut []);
        self.spi.deselect();
    }

    unsafe fn read_reg(&self, reg: u32) -> u32 {
        self.spi.select();
        let cmd = [
            0x0B,
            ((reg >> 16) & 0xFF) as u8,
            ((reg >> 8) & 0xFF) as u8,
            (reg & 0xFF) as u8,
            0x00,
        ];
        self.spi.transfer_block(&cmd, &mut []);

        let mut resp = [0u8; 4];
        self.spi.transfer_block(&[0u8; 4], &mut resp);
        self.spi.deselect();

        (resp[0] as u32) | ((resp[1] as u32) << 8) | ((resp[2] as u32) << 16) | ((resp[3] as u32) << 24)
    }

    pub unsafe fn initialize_transport(&mut self) -> Result<[u8; 6], ()> {
        self.write_reg(WILC_SPI_CTL_REG, 0x0000_0001);
        let mut timeout = 10000;
        while (self.read_reg(WILC_SPI_CTL_REG) & 0x0000_0001) != 0 {
            timeout -= 1;
            if timeout == 0 { return Err(()); }
        }

        self.rx_ring.init();
        self.tx_ring.init();

        let mac_lo = self.read_reg(WILC_MAC_ADDR_LO);
        let mac_hi = self.read_reg(WILC_MAC_ADDR_HI);

        if mac_lo == 0 || mac_lo == 0xFFFF_FFFF {
            return Err(());
        }

        let mut mac = [0u8; 6];
        mac[0] = (mac_lo & 0xFF) as u8;
        mac[1] = ((mac_lo >> 8) & 0xFF) as u8;
        mac[2] = ((mac_lo >> 16) & 0xFF) as u8;
        mac[3] = ((mac_lo >> 24) & 0xFF) as u8;
        mac[4] = (mac_hi & 0xFF) as u8;
        mac[5] = ((mac_hi >> 8) & 0xFF) as u8;

        Ok(mac)
    }

    pub unsafe fn transmit_frame(&mut self, frame_ptr: *const u8, length: usize) -> Result<(), &'static str> {
        let next_head = (self.tx_ring.head + 1) % RING_BUFFER_SIZE;
        if next_head == self.tx_ring.tail {
            return Err("TX_RING_FULL");
        }

        let desc = self.tx_ring.descriptors.get_unchecked_mut(self.tx_ring.head);
        if (core::ptr::read_volatile(&desc.status) & 0x8000_0000) == 0 {
            return Err("DESCRIPTOR_LOCKED_BY_ACTIVE_TX");
        }

        let internal_target_addr = desc.bus_addr;

        self.spi.select();
        let cmd = [
            0xC8,
            ((internal_target_addr >> 16) & 0xFF) as u8,
            ((internal_target_addr >> 8) & 0xFF) as u8,
            (internal_target_addr & 0xFF) as u8,
        ];
        self.spi.transfer_block(&cmd, &mut []);

        let src_slice = core::slice::from_raw_parts(frame_ptr, length);
        self.spi.transfer_block(src_slice, &mut []);
        self.spi.deselect();

        core::ptr::write_volatile(&mut desc.length, length as u32);
        core::ptr::write_volatile(&mut desc.status, 0x0000_0000);

        self.tx_ring.head = next_head;
        Ok(())
    }

    pub unsafe fn poll_rx<F>(&mut self, mut handler: F, packet_len: usize)
    where
        F: FnMut(*const u8, usize),
    {
        if packet_len == 0 || packet_len > PACKET_MAX_SIZE {
            return;
        }

        let tail = self.rx_ring.tail;
        let desc = self.rx_ring.descriptors.get_unchecked_mut(tail);
        let internal_src_addr = desc.bus_addr;

        self.spi.select();
        let cmd = [
            0xC9,
            ((internal_src_addr >> 16) & 0xFF) as u8,
            ((internal_src_addr >> 8) & 0xFF) as u8,
            (internal_src_addr & 0xFF) as u8,
            0x00,
        ];
        self.spi.transfer_block(&cmd, &mut []);

        let dest_slice = core::slice::from_raw_parts_mut(
            self.rx_ring.buffers.get_unchecked_mut(tail).as_mut_ptr(),
            packet_len,
        );

        let dummy_tx = [0u8; PACKET_MAX_SIZE];
        let dummy_slice = core::slice::from_raw_parts(dummy_tx.as_ptr(), packet_len);
        self.spi.transfer_block(dummy_slice, dest_slice);
        self.spi.deselect();

        handler(self.rx_ring.buffers.get_unchecked(tail).as_ptr(), packet_len);

        core::ptr::write_volatile(&mut self.rx_ring.descriptors.get_unchecked_mut(tail).status, 0x8000_0000);
        self.rx_ring.tail = (tail + 1) % RING_BUFFER_SIZE;
    }

    pub unsafe fn handle_interrupt<F>(&mut self, mut rx_handler: F)
    where
        F: FnMut(*const u8, usize),
    {
        if INT_TRIGGERED.compare_exchange(true, false, Ordering::AcqRel, Ordering::Acquire).is_ok() {
            let int_status = self.read_reg(WILC_SPI_INT_STATUS);
            if int_status == 0 || int_status == 0xFFFF_FFFF {
                return;
            }

            self.write_reg(WILC_SPI_INT_STATUS, int_status);

            if (int_status & 0x0000_0001) != 0 {
                let rx_len_reg = self.read_reg(WILC_SPI_REG_BASE + 0x1C) & 0x0000_FFFF;
                self.poll_rx(&mut rx_handler, rx_len_reg as usize);
            }

            if (int_status & 0x0000_0002) != 0 {
                while self.tx_ring.tail != self.tx_ring.head {
                    let tail = self.tx_ring.tail;
                    let desc = self.tx_ring.descriptors.get_unchecked_mut(tail);
                    core::ptr::write_volatile(&mut desc.status, 0x8000_0000);
                    self.tx_ring.tail = (tail + 1) % RING_BUFFER_SIZE;
                }
            }
        }
    }
}

pub type CWilcDriver = WilcDriver<CSpiVTable>;
pub type CRxCallback = unsafe extern "C" fn(ctx: *mut (), packet: *const u8, len: usize);

#[no_mangle]
pub unsafe extern "C" fn wilc_driver_init(
    driver_mem: *mut CWilcDriver,
    spi_vtable: CSpiVTable,
) -> i32 {
    if driver_mem.is_null() {
        return -1;
    }
    core::ptr::write(driver_mem, WilcDriver::new(spi_vtable));
    0
}

#[no_mangle]
pub unsafe extern "C" fn wilc_initialize_transport(
    driver: *mut CWilcDriver,
    out_mac: *mut u8,
) -> i32 {
    if driver.is_null() || out_mac.is_null() {
        return -1;
    }
    match (*driver).initialize_transport() {
        Ok(mac) => {
            core::ptr::copy_nonoverlapping(mac.as_ptr(), out_mac, 6);
            0
        }
        Err(_) => -2,
    }
}

#[no_mangle]
pub unsafe extern "C" fn wilc_transmit_frame(
    driver: *mut CWilcDriver,
    frame_ptr: *const u8,
    len: usize,
) -> i32 {
    if driver.is_null() || frame_ptr.is_null() || len > PACKET_MAX_SIZE {
        return -1;
    }
    match (*driver).transmit_frame(frame_ptr, len) {
        Ok(_) => 0,
        Err(_) => -2,
    }
}

#[no_mangle]
pub unsafe extern "C" fn wilc_handle_interrupt(
    driver: *mut CWilcDriver,
    rx_cb: CRxCallback,
    cb_ctx: *mut (),
) {
    if driver.is_null() {
        return;
    }
    (*driver).handle_interrupt(|buf, len| {
        rx_cb(cb_ctx, buf, len);
    });
}

#[no_mangle]
pub extern "C" fn wilc_notify_irq() {
    INT_TRIGGERED.store(true, Ordering::Release);
}

// Global bare-metal panic handlers and bounds-check stubs
#[no_mangle]
pub extern "C" fn panic_bounds_check() -> ! {
    loop {}
}

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    loop {}
}
