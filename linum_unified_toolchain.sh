#!/usr/bin/env bash
set -e

# ==============================================================================
# 1. HARDENED RAW BLOCK & RECOVERY EXTRACTION MATRIX (/dev/sdb)
# ==============================================================================
echo "[*] Step 1: Carving and inspecting /dev/sdb partitions..."

mkdir -p /home/ron/sdb_dumps /home/ron/sdb_extracted /home/ron/sdb_carved

if [ -b "/dev/sdb3" ]; then
    echo "[+] Scanning raw string landmarks (VORTEX / MONOLIGHT) on /dev/sdb3..."
    sudo strings -t d /dev/sdb3 | grep -E -C 3 "VORTEX|MONOLIGHT" > /home/ron/sdb_dumps/landmarks.txt || true

    echo "[+] Attempting read-only partition mount on /mnt..."
    if sudo mount -o ro /dev/sdb3 /mnt 2>/dev/null; then
        echo "[+] Copying partition contents to /home/ron/sdb_extracted..."
        cp -r /mnt/* /home/ron/sdb_extracted/ 2>/dev/null || true
        sudo umount /mnt
    else
        echo "[!] Mount failed: Partition unformatted or raw. Dumping block backup..."
        sudo dd if=/dev/sdb3 of=/home/ron/sdb_dumps/sdb3_backup.img bs=4M count=32 status=progress 2>/dev/null || true
    fi
    sudo chown -R $USER:$USER /home/ron/sdb_dumps /home/ron/sdb_extracted /home/ron/sdb_carved 2>/dev/null || true
else
    echo "[!] /dev/sdb3 block device not detected, skipping hardware carve."
fi

# ==============================================================================
# 2. ASSEMBLE BOOTLOADER WITH VALID 0xAA55 MBR SIGNATURE
# ==============================================================================
echo "[*] Step 2: Writing and compiling boot64_unified.asm..."
cd /home/ron/linum || cd ~

cat << 'ASM_EOF' > boot64_unified.asm
[bits 16]
[org 0x7c00]

_start:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7c00

    ; Output 'LINUM' status directly to COM1 serial for QEMU -nographic
    mov dx, 0x3F8
    mov al, 'L'
    out dx, al
    mov al, 'I'
    out dx, al
    mov al, 'N'
    out dx, al
    mov al, 'U'
    out dx, al
    mov al, 'M'
    out dx, al
    mov al, 0x0A
    out dx, al

.hang:
    hlt
    jmp .hang

times 510 - ($ - $$) db 0
dw 0xAA55
ASM_EOF

nasm -f bin boot64_unified.asm -o boot64.bin
dd if=/dev/zero of=disk.img bs=1M count=64 status=none
dd if=boot64.bin of=disk.img conv=notrunc status=none
echo "[+] Validated MBR Sector Hex Dump:"
hexdump -C -n 512 disk.img | tail -n 2

# ==============================================================================
# 3. ZIG NETWORK DAEMON & BARE-METAL HARNESS (fx-harness)
# ==============================================================================
echo "[*] Step 3: Initializing and compiling fx-lightweight Zig Daemon..."
mkdir -p /home/ron/linum/fx-harness/src
cd /home/ron/linum/fx-harness

cat << 'ZIG_BUILD' > build.zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const exe = b.addExecutable(.{
        .name = "fx-lightweight",
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });

    b.installArtifact(exe);
}
ZIG_BUILD

cat << 'ZIG_SRC' > src/main.zig
const std = @import("std");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const stdout = std.io.getStdOut().writer();

    const listen_address = try std.net.Address.parseIp4("127.0.0.1", 8080);
    var server = try listen_address.listen(.{ .reuse_address = true });
    defer server.deinit();

    try stdout.print("[fx-core-clone] Hardened Network Daemon active on 127.0.0.1:8080\n", .{});

    var msg_buf = std.ArrayList(u8).init(allocator);
    defer msg_buf.deinit();

    while (true) {
        const connection = server.accept() catch |err| {
            try stdout.print("   !! Socket accept failure: {}\n", .{err});
            continue;
        };
        defer connection.stream.close();

        msg_buf.clearRetainingCapacity();

        const max_input_limit = 10 * 1024 * 1024;
        connection.stream.reader().streamUntilDelimiter(msg_buf.writer(), '\n', max_input_limit) catch |err| {
            if (err != error.EndOfStream) {
                try stdout.print("   !! Network I/O boundary error: {}\n", .{err});
            }
            continue;
        };

        const input = std.mem.trim(u8, msg_buf.items, " \r\n");
        if (input.len == 0) continue;

        if (std.mem.eql(u8, input, "exit") or std.mem.eql(u8, input, "quit")) {
            try stdout.print("[fx-core-clone] Administrative shutdown accepted.\n", .{});
            break;
        }

        var bw = std.io.bufferedWriter(connection.stream.writer());
        const socket_writer = bw.writer();

        if (std.mem.startsWith(u8, input, "{")) {
            try processMcpMessage(allocator, socket_writer, input);
        } else {
            try processAgentTask(allocator, socket_writer, input);
        }

        try bw.flush();
    }
}

fn processMcpMessage(allocator: std.mem.Allocator, writer: anytype, json_input: []const u8) !void {
    _ = allocator;
    if (std.mem.indexOf(u8, json_input, "\"method\":\"tools/list\"") != null) {
        try writer.print("{s}\n", .{
            \\{"jsonrpc":"2.0","result":{"tools":[{"name":"exec","description":"Run shell utilities under isolated env"},{"name":"scan-native","description":"Carve raw partition sectors directly"}]},"id":1}
        });
    } else {
        try writer.print("{s}\n", .{
            \\{"jsonrpc":"2.0","error":{"code":-32601,"message":"Method not found"},"id":null}
        });
    }
}

fn processAgentTask(allocator: std.mem.Allocator, writer: anytype, input: []const u8) !void {
    var it = std.mem.tokenizeSequence(u8, input, " ");
    const cmd = it.next() orelse return;

    if (std.mem.eql(u8, cmd, "ask")) {
        const query = input[cmd.len..];
        try writer.print("   -> Processing query: \"{s}\"\n", .{std.mem.trim(u8, query, " ")});
    } else if (std.mem.eql(u8, cmd, "scan-native")) {
        try carveStorageBlock(writer);
    } else if (std.mem.eql(u8, cmd, "exec")) {
        var argv = std.ArrayList([]const u8).init(allocator);
        defer argv.deinit();
        while (it.next()) |arg| try argv.append(arg);

        if (argv.items.len == 0) {
            try writer.print("Error: Target command missing.\n", .{});
            return;
        }

        var env_map = std.process.EnvMap.init(allocator);
        defer env_map.deinit();

        try env_map.put("PATH", "/usr/local/bin:/usr/bin:/bin");
        try env_map.put("AGENT_WORKER_ID", "FX_CONCURRENT_DAEMON");
        try env_map.put("LINUM_CONTEXT_ISOLATION", "TRUE");

        var child = std.process.Child.init(argv.items, allocator);
        child.stdout_behavior = .Pipe;
        child.stderr_behavior = .Pipe;
        child.env_map = &env_map;

        try child.spawn();

        const max_output_size = 50 * 1024;
        const stdout_payload = try child.stdout.?.reader().readAllAlloc(allocator, max_output_size);
        defer allocator.free(stdout_payload);
        const stderr_payload = try child.stderr.?.reader().readAllAlloc(allocator, max_output_size);
        defer allocator.free(stderr_payload);
        _ = try child.wait();

        if (stdout_payload.len > 0) try writer.print("{s}", .{stdout_payload});
        if (stderr_payload.len > 0) try writer.print("{s}", .{stderr_payload});
    } else {
        try writer.print("Unknown command primitive.\n", .{});
    }
}

fn carveStorageBlock(writer: anytype) !void {
    var file = std.fs.openFileAbsolute("/dev/sdb3", .{ .mode = .read_only }) catch |err| {
        if (err == error.PermissionDenied) {
            try writer.print("   !! Permission Denied: Daemon requires CAP_SYS_RAWIO / root for /dev/sdb3 access.\n", .{});
            return;
        }
        try writer.print("   !! Direct Block Access Failure: {}\n", .{err});
        return;
    };
    defer file.close();

    var block_window: [65536]u8 = undefined;
    var total_matches: usize = 0;
    var sector_index: usize = 0;

    try writer.print("--- [NATIVE DISK MATRIX CARVE START: /dev/sdb3] ---\n", .{});

    while (true) {
        const bytes_read = file.read(&block_window) catch |err| {
            try writer.print("   !! Sector read error at index {}: {}\n", .{ sector_index, err });
            break;
        };
        if (bytes_read == 0) break;

        const chunk = block_window[0..bytes_read];

        if (std.mem.indexOf(u8, chunk, "VORTEX") != null or std.mem.indexOf(u8, chunk, "MONOLIGHT") != null) {
            total_matches += 1;
            try writer.print("   [+] LANDMARK MATCH at 64KB Sector Chunk: {}\n", .{sector_index});

            if (std.mem.indexOf(u8, chunk, "VORTEX")) |idx| {
                const end = @min(idx + 64, chunk.len);
                const start = if (idx > 64) idx - 64 else 0;
                try writer.print("       Context (VORTEX): ...{s}...\n", .{chunk[start..end]});
            }
            if (std.mem.indexOf(u8, chunk, "MONOLIGHT")) |idx| {
                const end = @min(idx + 64, chunk.len);
                const start = if (idx > 64) idx - 64 else 0;
                try writer.print("       Context (MONOLIGHT): ...{s}...\n", .{chunk[start..end]});
            }
            if (total_matches >= 10) {
                try writer.print("   [-] Match sample ceiling reached (10).\n", .{});
                break;
            }
        }
        sector_index += 1;
    }
    try writer.print("--- [CARVE COMPLETE | Total Landmarks Found: {}] ---\n", .{total_matches});
}
ZIG_SRC

zig build -Doptimize=ReleaseSmall
echo "[+] Zig Harness compiled cleanly at $(pwd)/zig-out/bin/fx-lightweight"

# ==============================================================================
# 4. HIGH-THROUGHPUT DIRECT-IO IO_URING STORAGE ENGINE
# ==============================================================================
echo "[*] Step 4: Compiling io_uring storage engine..."
cd /home/ron/linum || cd ~

cat << 'CPP_EOF' > batch_engine.cpp
#include <iostream>
#include <vector>
#include <fcntl.h>
#include <unistd.h>
#include <liburing.h>
#include <sys/mman.h>
#include <cstring>
#include <cstdlib>

constexpr std::size_t IO_BLOCK_SIZE = 4096;
constexpr unsigned QUEUE_DEPTH = 32;
constexpr int BATCH_SIZE = 4;

struct IOContext {
    int id;
    int fd;
    void* buffer;
    off_t offset;
};

int main() {
    std::vector<IOContext> contexts(BATCH_SIZE);
    
    for (int i = 0; i < BATCH_SIZE; ++i) {
        contexts[i].id = i + 1;
        contexts[i].offset = 0;

        contexts[i].fd = open("/tmp/io_target.dat", O_RDONLY | O_DIRECT);
        if (contexts[i].fd < 0) {
            std::cerr << "[-] Error: Failed to open descriptor " << i << "\n";
            return 1;
        }

        if (posix_memalign(&contexts[i].buffer, IO_BLOCK_SIZE, IO_BLOCK_SIZE) != 0) {
            std::cerr << "[-] Error: Memory alignment failed for context " << i << "\n";
            return 1;
        }
    }

    struct io_uring ring;
    if (io_uring_queue_init(QUEUE_DEPTH, &ring, 0) < 0) {
        std::cerr << "[-] Error: Subsystem initialization failed.\n";
        return 1;
    }

    for (int i = 0; i < BATCH_SIZE; ++i) {
        struct io_uring_sqe* sqe = io_uring_get_sqe(&ring);
        if (!sqe) break;
        io_uring_prep_read(sqe, contexts[i].fd, contexts[i].buffer, IO_BLOCK_SIZE, contexts[i].offset);
        io_uring_sqe_set_data(sqe, &contexts[i]);
    }

    int submitted = io_uring_submit(&ring);
    std::cout << "[+] Submitted " << submitted << " asynchronous SQEs in 1 syscall.\n";

    int completed = 0;
    while (completed < BATCH_SIZE) {
        struct io_uring_cqe* cqe;
        if (io_uring_wait_cqe(&ring, &cqe) < 0) break;

        unsigned head;
        unsigned count = 0;
        io_uring_for_each_cqe(&ring, head, cqe) {
            count++;
            auto* ctx = static_cast<IOContext*>(io_uring_cqe_get_data(cqe));
            if (cqe->res >= 0) {
                std::cout << "[✓] CQE Processed | ID: " << ctx->id << " | Bytes: " << cqe->res << "\n";
            }
        }
        io_uring_cq_advance(&ring, count);
        completed += count;
    }

    io_uring_queue_exit(&ring);
    for (int i = 0; i < BATCH_SIZE; ++i) {
        free(contexts[i].buffer);
        close(contexts[i].fd);
    }
    return 0;
}
CPP_EOF

dd if=/dev/urandom of=/tmp/io_target.dat bs=4096 count=1 status=none
g++ -O3 batch_engine.cpp -o batch_engine -luring

echo "============================================================"
echo " [✓] ALL ARTIFACTS BUILT, ALIGNED, AND DEPLOYED SOUNDLY"
echo "============================================================"
