const std = @import("std");

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    // 512-bit vector of 16 32-bit floats
    const a: @Vector(16, f32) = @splat(2.5);
    const b: @Vector(16, f32) = @splat(4.0);
    const result = a * b;

    try stdout.print("AVX-512 Vectorized Tensor Output: {d}\n", .{result[0]});
}
