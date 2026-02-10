const std = @import("std");

pub fn add(a: i32, b: i32) i32 {
    return a + b;
}

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    try stdout.print("{}", .{add(2, 3)});
}
