#!/usr/bin/env python3
"""
FDOTHER 索引1详细分析 - 24x24小图标
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def main():
    with open(DAT_FILE, 'rb') as f:
        start, size = read_index(f, 1)
        f.seek(start)
        data = f.read(size)

        print(f"索引1: {size} 字节")
        print(f"头8字节: {data[:8].hex()}")
        print(f"width={struct.unpack('<H', data[0:2])[0]}, height={struct.unpack('<H', data[2:4])[0]}")

        # 偏移表
        offsets = [86, 307, 558, 794]
        for i, off in enumerate(offsets):
            if off < size:
                # 读取偏移处的前10字节
                chunk = data[off:off+10]
                w = struct.unpack('<H', chunk[0:2])[0] if off + 2 <= size else 0
                h = struct.unpack('<H', chunk[2:4])[0] if off + 4 <= size else 0
                print(f"  偏移{i} (0x{off:x}): 前10字节={chunk.hex()}, w={w}, h={h}")
            else:
                print(f"  偏移{i} (0x{off:x}): 越界")

        # 也检查偏移0x56=86处是否是另一个子图像
        print()
        print("如果索引1的偏移0x56(86)处是另一个RLE图像头:")
        off = 86
        if off + 4 <= size:
            sub_w = struct.unpack('<H', data[off:off+2])[0]
            sub_h = struct.unpack('<H', data[off+2:off+4])[0]
            print(f"  子图像: width={sub_w}, height={sub_h}")

if __name__ == '__main__':
    main()