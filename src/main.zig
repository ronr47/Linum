const std = @import("std");

pub fn main() !void {
    std.debug.print("Scanning sysfs for Oppo / Qualcomm EDL (05c6:9008)...\n", .{});

    const sysfs_path = "/sys/bus/usb/devices";
    var dir = std.fs.cwd().openDir(sysfs_path, .{ .iterate = true }) catch |err| {
        std.debug.print("Error: Failed to open {s}: {}\n", .{sysfs_path, err});
        return err;
    };
    defer dir.close();

    var it = dir.iterate();
    var found = false;

    while (it.next() catch null) |entry| {
        if (entry.kind == .directory) {
            // Check idVendor
            actor: {
                const vid_path = std.fmt.allocPrint(std.heap.page_allocator, "{s}/{s}/idVendor", .{ sysfs_path, entry.name }) catch break :actor;
                defer std.heap.page_allocator.free(vid_path);

                var vid_file = std.fs.cwd().openFile(vid_path, .{}) catch break :actor;
                defer vid_file.close();

                var vid_buf: [16]u8 = undefined;
                const vid_len = vid_file.read(&vid_buf) catch break :actor;
                const vid_str = std.mem.trim(u8, vid_buf[0..vid_len], "\n\r ");

                if (std.mem.eql(u8, vid_str, "05c6")) {
                    // Check idProduct
                    const pid_path = std.fmt.allocPrint(std.heap.page_allocator, "{s}/{s}/idProduct", .{ sysfs_path, entry.name }) catch break :actor;
                    defer std.heap.page_allocator.free(pid_path);

                    var pid_file = std.fs.cwd().openFile(pid_path, .{}) catch break :actor;
                    defer pid_file.close();

                    var pid_buf: [16]u8 = undefined;
                    const pid_len = pid_file.read(&pid_buf) catch break :actor;
                    const pid_str = std.mem.trim(u8, pid_buf[0..pid_len], "\n\r ");

                    if (std.mem.eql(u8, pid_str, "9008")) {
                        std.debug.print("🎯 [EDL CONNECTED] Found target device on port: {s}\n", .{entry.name});
                        found = true;
                    }
                }
            }
        }
    }

    if (!found) {
        std.debug.print("No EDL device (05c6:9008) currently detected on the bus.\n", .{});
    }
}
