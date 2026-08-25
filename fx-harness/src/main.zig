const std = @import("std");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const stdout = std.io.getStdOut().writer();

    // 1. Bind POSIX TCP Socket Listener
    const listen_address = try std.net.Address.parseIp4("127.0.0.1", 8080);
    var server = try listen_address.listen(.{ .reuse_address = true });
    defer server.deinit();

    try stdout.print("[fx-core-clone] Hardened Network Daemon active on 127.0.0.1:8080\n", .{});

    var msg_buf = std.ArrayList(u8).init(allocator);
    defer msg_buf.deinit();

    // 2. Main Socket Connection Loop
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

        // Hardened Environment Isolation
        var env_map = std.process.EnvMap.init(allocator);
        defer env_map.deinit();

        try env_map.put("PATH", "/usr/local/bin:/usr/bin:/bin");
        try env_map.put("AGENT_WORKER_ID", "FX_DAEMON_CORE");
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
