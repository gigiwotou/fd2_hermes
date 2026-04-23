#!/usr/bin/env python3
"""
FDOTHER 资源数据转储 - 用于调试
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def main():
    with open(DAT_FILE, 'rb') as f:
        # 索引 18: 16x16 头像 (简单图案)
        start, size = read_index(f, 18)
        f.seek(start)
        data = f.read(min(size, 200))

        print(f"索引 18 (16x16 头像) 前 {len(data)} 字节:")
        print(f"  头4字节 (width, height): {struct.unpack('<HH', data[0:4])}")

        # 打印前64字节的hexdump
        print(f"  Hex dump:")
        for i in range(0, min(len(data), 64), 16):
            hex_str = ' '.join(f'{b:02x}' for b in data[i:i+16])
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
            print(f"    {i:04x}: {hex_str:<48} {ascii_str}")

        # 索引 1: 24x24 小图标
        print()
        start, size = read_index(f, 1)
        f.seek(start)
        data = f.read(min(size, 200))

        print(f"索引 1 (24x24 小图标) 前 {len(data)} 字节:")
        print(f"  头4字节 (width, height): {struct.unpack('<HH', data[0:4])}")

        # 打印前64字节的hexdump
        print(f"  Hex dump:")
        for i in range(0, min(len(data), 64), 16):
            hex_str = ' '.join(f'{b:02x}' for b in data[i:i+16])
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
            print(f"    {i:04x}: {hex_str:<48} {ascii_str}")

if __name__ == '__main__':
    main()