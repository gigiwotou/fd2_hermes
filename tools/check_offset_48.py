#!/usr/bin/env python3
"""
检查索引18中0x48偏移处的数据
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

        print(f"索引18: {size} 字节")

        # 如果字节8-11的0x48 (72) 是偏移，RLE数据从72开始
        rle_offset = 72
        print(f"\n从偏移{rle_offset} (0x48) 的数据:")
        if rle_offset + 20 <= size:
            chunk = data[rle_offset:rle_offset+20]
            print(f"  前20字节: {chunk.hex()}")
            w = struct.unpack('<H', chunk[0:2])[0]
            h = struct.unpack('<H', chunk[2:4])[0]
            print(f"  width={w}, height={h}")

        # 也检查偏移84 (0x54) - 字节8的下一个4字节边界
        print(f"\n从偏移84 (0x54) 的数据:")
        if 84 + 20 <= size:
            chunk = data[84:84+20]
            print(f"  前20字节: {chunk.hex()}")
            w = struct.unpack('<H', chunk[0:2])[0]
            h = struct.unpack('<H', chunk[2:4])[0]
            print(f"  width={w}, height={h}")

        # 尝试所有可能的偏移
        print("\n尝试所有偏移 (0-100):")
        for off in range(0, 100, 2):
            if off + 4 <= size:
                w = struct.unpack('<H', data[off:off+2])[0]
                h = struct.unpack('<H', data[off+2:off+4])[0]
                if 8 <= w <= 64 and 8 <= h <= 64:
                    print(f"  偏移{off}: width={w}, height={h}")

if __name__ == '__main__':
    main()