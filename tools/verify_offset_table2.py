#!/usr/bin/env python3
"""
FDOTHER 索引1偏移表分析 - 验证偏移表位置
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
        print(f"前48字节:")
        for i in range(0, 48, 16):
            hex_str = ' '.join(f'{b:02x}' for b in data[i:i+16])
            print(f"  {i:04x}: {hex_str}")

        # 偏移表从字节4开始 (0x56 = 86)
        print("\n偏移表 (从字节4开始):")
        offset_table = []
        for i in range(10):
            off = 4 + i * 4
            if off + 4 <= size:
                val = struct.unpack('<I', data[off:off+4])[0]
                offset_table.append(val)
                print(f"  项{i}: 偏移=0x{val:x} ({val})")

        # 偏移表最后一个有效值之后应该是RLE数据
        # 但实际上这些偏移值可能指向子图像数据
        print("\n检查偏移处的数据:")
        for i, off in enumerate(offset_table[:5]):
            if off < size and off > 0:
                chunk = data[off:off+6]
                print(f"  偏移0x{off:x}: {chunk.hex()}")

        # 等等，让我再看看字节4-5作为小端序uint16
        w_h_at_4 = struct.unpack('<H', data[4:6])[0]
        print(f"\n字节4-5作为uint16: {w_h_at_4} (0x{w_h_at_4:x})")

        # 如果字节4-5是偏移表项0，那么RLE数据可能从字节20开始
        # (假设有5个偏移表项 * 4字节 = 20字节)
        print(f"\n假设偏移表5项结束于字节24，检查字节24-30:")
        print(f"  {[hex(b) for b in data[24:30]]}")

        # 让我尝试从字节24开始作为RLE数据解码
        print("\n尝试从字节24开始解码:")
        rle_data = bytes([24, 0, 24, 0]) + data[24:100]
        print(f"  前20字节: {rle_data[:20].hex()}")

if __name__ == '__main__':
    main()