#!/usr/bin/env python3
"""
索引1的offset表分析
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

        w = struct.unpack('<H', data[0:2])[0]
        h = struct.unpack('<H', data[2:4])[0]
        sub_count = struct.unpack('<H', data[4:6])[0]

        print(f"width={w}, height={h}, sub_count={sub_count}")

        # offset表从字节6开始
        print("\nOffset表 (从字节6开始):")
        offsets = []
        for i in range(min(sub_count, 24)):
            off = 6 + i * 4
            val = struct.unpack('<I', data[off:off+4])[0]
            offsets.append(val)
            print(f"  [{i}]: 0x{val:04x} ({val})")

            # 检查该偏移处的数据
            if val < size and val > 0:
                chunk = data[val:val+4]
                if len(chunk) == 4:
                    w2 = struct.unpack('<H', chunk[0:2])[0]
                    h2 = struct.unpack('<H', chunk[2:4])[0]
                    # 检查是否是有效的RLE头
                    if 8 <= w2 <= 64 and 1 <= h2 <= 64:
                        print(f"       -> RLE头: {w2}x{h2}")
                    elif w2 > 300 or h2 > 300:
                        print(f"       -> 可能是其他格式")
                    else:
                        print(f"       -> width={w2}, height={h2}")

        # 第一个子图像的位置
        print(f"\n第一个子图像偏移: 0x{offsets[0]:x}")
        off = offsets[0]
        print(f"该位置数据: {data[off:off+20].hex()}")

        # 尝试作为LMI1检查
        if data[off:off+4] == b'LMI1':
            frames = struct.unpack('<H', data[off+4:off+6])[0]
            print(f"这是LMI1动画: {frames}帧")

if __name__ == '__main__':
    main()