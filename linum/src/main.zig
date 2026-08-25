const std = @import("std");
const fs = std.fs;

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    
    // Open target block storage
    const file = fs.cwd().openFile("/dev/sdb3", .{ .mode = .read_only }) catch |err| {
        if (err == error.AccessDenied) {
            try stdout.print("Error: Root privileges required. Run with sudo.\n", .{});
        } else {
            try stdout.print("Error opening device: {s}\n", .{@errorName(err)});
        }
        return err;
    };
    defer file.close();

    // Setup working output folder for recovered files
    fs.cwd().makeDir("recovered_dumps") catch |err| {
        if (err != error.PathAlreadyExists) return err;
    };
    var recovered_dir = try fs.cwd().openDir("recovered_dumps", .{});
    defer recovered_dir.close();

    // 4KB sector-aligned scanning buffer
    var buffer: [4096]u8 = undefined;
    var bytes_read: usize = 0;
    
    // Pre-allocated extraction buffer for file recovery (512 KB chunk size)
    const CARVE_SIZE = 512 * 1024;
    var carve_buffer: [CARVE_SIZE]u8 = undefined;
    var file_counter: u32 = 0;

    try stdout.print("Initializing forensic carving array on /dev/sdb3...\n", .{});

    while (true) {
        const amt = file.read(&buffer) catch |err| {
            try stdout.print("\nRead error at byte offset {d}: {s}\n", .{ bytes_read, @errorName(err) });
            return err;
        };
        if (amt == 0) break; 
        bytes_read += amt;

        var found_sig: ?[]const u8 = null;
        var sig_offset: usize = 0;

        if (std.mem.indexOf(u8, buffer[0..amt], "VORTEX")) |idx| {
            found_sig = "VORTEX";
            sig_offset = (bytes_read - amt) + idx;
        } else if (std.mem.indexOf(u8, buffer[0..amt], "MONOLIGHT")) |idx| {
            found_sig = "MONOLIGHT";
            sig_offset = (bytes_read - amt) + idx;
        }

        // If signature is detected, perform extraction drop
        if (found_sig) |sig_name| {
            try stdout.print("\n[+] Extracting {s} cluster at global offset: {d}\n", .{sig_name, sig_offset});
            
            // Save current partition seek point
            const current_pos = try file.getPos();
            
            // Seek directly to signature head position and read the recovery chunk
            try file.seekTo(sig_offset);
            const read_amt = try file.readAll(&carve_buffer);
            
            // Generate distinct filename asset
            var name_buf: [64]u8 = undefined;
            const file_name = try std.fmt.bufPrint(&name_buf, "{s}_recovery_{d}.dat", .{sig_name, file_counter});
            
            // Write payload data out to host workspace disk
            const dump_file = try recovered_dir.createFile(file_name, .{});
            try dump_file.writeAll(carve_buffer[0..read_amt]);
            dump_file.close();
            
            file_counter += 1;
            
            // Restore file descriptor to loop progression coordinate
            try file.seekTo(current_pos);
        }

        // Display progress metrics
        if (bytes_read % (1024 * 1024 * 10) == 0) {
            try stdout.print("\rScanned volume depth: {d} MB...", .{bytes_read / (1024 * 1024)});
        }
    }

    try stdout.print("\n\nScan complete. Total dumped files: {d}\n", .{file_counter});
}
