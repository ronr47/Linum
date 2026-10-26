// ProofBoot PB-010: Bare-Metal Dual-Bank NVRAM Policy Engine
// Target: Native R2 Core

module proofboot.pb010;

const SLOT_SIZE: u32        = 4096;
const HEADER_A_OFFSET: u32  = 8192;
const HEADER_B_OFFSET: u32  = 8256;
const HEADER_SIZE: u32      = 64;
const PB_MAGIC: u32         = 0x564E4250; // "PBNV" Little-Endian

enum Status : u32 {
    Ok                  = 0,
    InvalidMagic        = 1,
    CrcMismatch         = 2,
    AuthFailed          = 3,
    BoundsViolation     = 4,
    MonotonicViolation  = 5,
    IoError             = 6,
}

#[packed, repr(C)]
struct Header {
    magic: u32,
    active_slot: u32,
    generation: u32,
    seq: u32,
    crc: u32,
    reserved: [u8; 44],
}

#[packed, repr(C)]
struct SlotEnvelope {
    magic: u32,
    body_len: u32,
    digest: [u8; 32],
}

struct StorageDevice {
    base: mmio<u8>,
    capacity: u32,
    secret_key: [u8; 32],
}

fn crc32(buffer: ram<u8>, len: u32) -> u32
    pre: len <= 4096
    post: true
{
    var crc: u32 = 0xFFFFFFFF;
    var i: u32 = 0;
    while i < len {
        let byte_val: u32 = (buffer[i] as u32);
        crc = crc ^ byte_val;
        var j: u32 = 0;
        while j < 8 {
            let mask: u32 = 0 - (crc & 1);
            crc = (crc >> 1) ^ (0xEDB88320 & mask);
            j = j + 1;
        }
        i = i + 1;
    }
    return ~crc;
}

fn constant_time_eq(a: ram<u8>, b: ram<u8>, len: u32) -> bool
    pre: len <= 64
    post: true
{
    var diff: u8 = 0;
    var i: u32 = 0;
    while i < len {
        diff = diff | (a[i] ^ b[i]);
        i = i + 1;
    }
    return diff == 0;
}

fn parse_header(slot_base: ram<u8>) -> (bool, Header) {
    let hdr = unsafe { *(slot_base as ram<Header>) };
    if hdr.magic != PB_MAGIC {
        return (false, hdr);
    }
    let computed_crc = crc32(slot_base, 12);
    if hdr.crc != computed_crc {
        return (false, hdr);
    }
    return (true, hdr);
}

fn arbitrate_active_header(dev: StorageDevice) -> (Status, Header, u8) {
    var raw_a: [u8; 64] = [0; 64];
    var raw_b: [u8; 64] = [0; 64];

    mmio_read_barrier();
    mmio_copy(raw_a.as_ram(), dev.base + HEADER_A_OFFSET, HEADER_SIZE);
    mmio_copy(raw_b.as_ram(), dev.base + HEADER_B_OFFSET, HEADER_SIZE);
    mmio_read_barrier();

    let (valid_a, hdr_a) = parse_header(raw_a.as_ram());
    let (valid_b, hdr_b) = parse_header(raw_b.as_ram());

    if !valid_a && !valid_b {
        return (Status::CrcMismatch, hdr_a, b'X');
    }
    if valid_a && valid_b {
        if hdr_a.seq >= hdr_b.seq {
            return (Status::Ok, hdr_a, b'A');
        } else {
            return (Status::Ok, hdr_b, b'B');
        }
    }
    if valid_a {
        return (Status::Ok, hdr_a, b'A');
    }
    return (Status::Ok, hdr_b, b'B');
}

fn commit_transition(
    dev: StorageDevice, 
    new_payload: ram<u8>, 
    payload_len: u32,
    new_generation: u32
) -> Status
    pre: payload_len <= (SLOT_SIZE - 40)
    post: ret == Status::Ok || ret == Status::MonotonicViolation
{
    let (status, active_hdr, side) = arbitrate_active_header(dev);
    if status != Status::Ok {
        return status;
    }

    if new_generation <= active_hdr.generation {
        return Status::MonotonicViolation;
    }

    let target_slot: u32 = 1 - active_hdr.active_slot;
    let target_offset: u32 = target_slot * SLOT_SIZE;

    var slot_buffer: [u8; 4096] = [0; 4096];
    let env = unsafe { (slot_buffer.as_ram() as ram<SlotEnvelope>) };
    env.magic = PB_MAGIC;
    env.body_len = payload_len;

    hmac_sha256(
        dev.secret_key.as_ram(), 32,
        new_payload, payload_len,
        env.digest.as_ram()
    );

    ram_copy(slot_buffer.as_ram() + 40, new_payload, payload_len);

    mmio_write_barrier();
    mmio_copy(dev.base + target_offset, slot_buffer.as_ram(), SLOT_SIZE);
    mmio_flush(dev.base + target_offset, SLOT_SIZE);

    var verify_buf: [u8; 4096] = [0; 4096];
    mmio_copy(verify_buf.as_ram(), dev.base + target_offset, SLOT_SIZE);
    if !constant_time_eq(slot_buffer.as_ram(), verify_buf.as_ram(), SLOT_SIZE) {
        return Status::AuthFailed;
    }

    var next_hdr: Header = Header {
        magic: PB_MAGIC,
        active_slot: target_slot,
        generation: new_generation,
        seq: active_hdr.seq + 1,
        crc: 0,
        reserved: [0; 44],
    };

    next_hdr.crc = crc32((&next_hdr as ram<u8>), 16);

    let next_header_offset: u32 = if side == b'A' {
        HEADER_B_OFFSET
    } else {
        HEADER_A_OFFSET
    };

    mmio_write_barrier();
    mmio_copy(dev.base + next_header_offset, (&next_hdr as ram<u8>), HEADER_SIZE);
    mmio_flush(dev.base + next_header_offset, HEADER_SIZE);

    return Status::Ok;
}
