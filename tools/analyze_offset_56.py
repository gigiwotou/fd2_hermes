#!/usr/bin/env python3
"""
详细分析索引1偏移0x56处的数据
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

        # 偏移0x56处的数据
        off = 0x56
        chunk = data[off:off+50]

        print(f"索引1偏移0x56处数据:")
        print(f"  十六进制: {chunk.hex()}")
        print(f"  作为uint16 (小端):")
        for i in range(0, 20, 2):
            val = struct.unpack('<H', chunk[i:i+2])[0]
            print(f"    字节{i}-{i+1}: 0x{val:04x} ({val})")

        # 尝试不同的width/height解释
        # 如果字节0-1是count而不是width呢?
        w0 = struct.unpack('<H', chunk[0:2])[0]
        h0 = struct.unpack('<H', chunk[2:4])[0]
        print(f"\n标准解释: w={w0}, h={h0}")

        # 如果字节2-3是width, 字节0-1是其他?
        w1 = struct.unpack('<H', chunk[2:4])[0]
        h1 = struct.unpack('<H', chunk[0:2])[0]
        print(f"交换: w={w1}, h={h1}")

        # 让我尝试用不同的offset
        print(f"\n尝试从不同偏移作为RLE头:")
        for test_off in range(0x56, 0x56+20, 2):
            if test_off + 4 <= len(data):
                w = struct.unpack('<H', data[off + test_off - 0x56:off + test_off - 0x56 + 2])[0]
                h = struct.unpack('<H', data[off + test_off - 0x56 + 2:off + test_off - 0x56 + 4])[0]
                if 8 <= w <= 64 and 8 <= h <= 64:
                    print(f"  偏移{test_off}: w={w}, h={h}")

        # 也许offset表不是偏移，而是子图像的索引？
        # 让我查看字节6-9作为uint32的值
        print(f"\n字节6-9作为uint32: {struct.unpack('<I', data[6:10])[0]}")
        print(f"字节10-13作为uint32: {struct.unpack('<I', data[10:14])[0]}")

        # 如果这些是相对偏移（从资源开始处），那么实际位置 = start + offset
        # 但我们已经在start处，所以直接用offset
        print(f"\n如果offset是相对于文件开头:")
        off0 = struct.unpack('<I', data[6:10])[0]
        print(f"  offset 0x56 -> 绝对位置: {start + off0}")
        print(f"  索引1数据本身从0开始，offset {off0} 应该相对于索引1数据的开始")

if __name__ == '__main__':
    main()