#!/usr/bin/env python3
"""
打印索引18的RLE命令流
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def main():
    with open(DAT_FILE, 'rb') as f:
        start, size = read_index(f, 18)
        f.seek(start)
        data = f.read(size)

        print(f"索引18: {size} 字节, width=16, height=16")

        # RLE数据从字节4开始
        src = list(data[4:])
        print(f"\nRLE数据 (字节4-100): {data[4:100].hex()}")
        print(f"\n前50个RLE命令:")

        src_idx = 0
        x = 0
        for i in range(50):
            if src_idx >= len(src):
                print(f"  命令{i}: src越界")
                break

            value = src[src_idx]

            count_1 = ((value * 4) & 0xFF) >> 2
            if count_1 == 0:
                count_1 = 1
            count_1 += 1

            bit7 = (value >> 7) & 1
            bit6 = (value >> 6) & 1

            if bit7 == 0 and bit6 == 0:
                desc = f"COPY {count_1} bytes: {[hex(src[src_idx+j]) if src_idx+j < len(src) else '?' for j in range(1, count_1+1)]}"
                src_idx += count_1 + 1
            elif bit7 == 0 and bit6 == 1:
                desc = f"FILL {count_1} with 0x{src[src_idx+1]:02x}" if src_idx+1 < len(src) else "FILL (no byte)"
                src_idx += 2
            elif bit7 == 1 and bit6 == 0:
                desc = f"SKIP {count_1}"
                src_idx += 1
            else:
                desc = f"INTERLEAVE {count_1} with 0x{src[src_idx+1]:02x}" if src_idx+1 < len(src) else "INTERLEAVE (no byte)"
                src_idx += 2

            x += count_1 if bit7 == 1 and bit6 == 0 else count_1 if bit7 == 0 else count_1

            cmd_byte = value & 0xFF
            print(f"  命令{i}: byte=0x{cmd_byte:02x} bit7={bit7} bit6={bit6} {desc} (x={x})")

            if x >= 16:
                break

if __name__ == '__main__':
    main()