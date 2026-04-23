#!/usr/bin/env python3
"""
分析索引18的字节结构
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
        data = f.read(min(size, 200))

        print(f"索引18: {size} 字节")
        print("\n字节0-31:")
        for i in range(0, 32, 16):
            hex_str = ' '.join(f'{b:02x}' for b in data[i:i+16])
            print(f"  {i:04x}: {hex_str}")

        # 作为不同格式解释
        print("\n作为 uint16little-endian:")
        print(f"  字节0-1: width = {struct.unpack('<H', data[0:2])[0]}")
        print(f"  字节2-3: height = {struct.unpack('<H', data[2:4])[0]}")

        print("\n作为 uint32 little-endian (从字节4开始):")
        for i in range(4, 28, 4):
            val = struct.unpack('<I', data[i:i+4])[0]
            print(f"  字节{i}-{i+3}: 0x{val:x} ({val})")

        # 尝试从不同偏移开始作为RLE数据解码
        print("\n尝试从不同偏移作为RLE数据:")
        for offset in [4, 6, 8, 10, 12]:
            if offset + 4 <= len(data):
                w = struct.unpack('<H', data[offset:offset+2])[0]
                h = struct.unpack('<H', data[offset+2:offset+4])[0]
                print(f"  偏移{offset}: width={w}, height={h}")

        # 也许字节4-7是RLE数据，从字节4开始就是RLE头？
        print("\n如果RLE数据从字节4开始:")
        w = struct.unpack('<H', data[4:6])[0]
        h = struct.unpack('<H', data[6:8])[0]
        print(f"  width={w}, height={h}")
        if w == 16 and h == 16:
            print("  -> 匹配! RLE数据确实从字节4开始")

        # 验证：检查索引18的数据是否从字节4开始就是有效的16x16 RLE数据
        print("\n完整分析索引18:")
        print(f"  字节0-1: {data[0:2].hex()} = width=16")
        print(f"  字节2-3: {data[2:4].hex()} = height=16")
        print(f"  字节4-5: {data[4:6].hex()} = (可能子项数或RLE数据)")
        print(f"  字节6-7: {data[6:8].hex()} = (可能RLE数据)")

        # 如果字节4是RLE数据开始，验证
        rle_offset = 4
        if rle_offset + 4 <= size:
            rle_w = struct.unpack('<H', data[rle_offset:rle_offset+2])[0]
            rle_h = struct.unpack('<H', data[rle_offset+2:rle_offset+4])[0]
            print(f"\n从偏移{rle_offset}的RLE头: {rle_w}x{rle_h}")
            if rle_w == 16 and rle_h == 16:
                print("  -> 正确!")

        # 检查是否有offset表
        sub_count_possible = struct.unpack('<H', data[4:6])[0]
        if sub_count_possible > 0 and sub_count_possible < 100:
            print(f"\n字节4-5可能是子项数量: {sub_count_possible}")
            # 检查offset表
            for i in range(min(sub_count_possible, 10)):
                off = 6 + i * 4
                if off + 4 <= size:
                    val = struct.unpack('<I', data[off:off+4])[0]
                    print(f"  offset[{i}] = 0x{val:x}")

if __name__ == '__main__':
    main()