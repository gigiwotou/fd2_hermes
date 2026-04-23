#!/usr/bin/env python3
"""
在索引18中寻找真正的RLE数据起始位置
RLE数据应该包含: width/height头 + 压缩像素数据
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def check_rle_at(data, offset, min_w=8, max_w=64, min_h=8, max_h=64):
    """检查offset处是否有有效的RLE头"""
    if offset + 4 > len(data):
        return None

    w = struct.unpack('<H', data[offset:offset+2])[0]
    h = struct.unpack('<H', data[offset+2:offset+4])[0]

    if min_w <= w <= max_w and min_h <= h <= max_h:
        # 检查RLE数据部分是否有合理的命令分布
        rle_data = data[offset+4:offset+4+100]
        nonzero = sum(1 for b in rle_data if b != 0)
        if nonzero > 10:  # 有足够多的非零字节
            return (w, h)
    return None

def main():
    with open(DAT_FILE, 'rb') as f:
        start, size = read_index(f, 18)
        f.seek(start)
        data = f.read(size)

        print(f"索引18: {size} 字节")
        print(f"预期尺寸: 16x16\n")

        # 搜索所有可能的位置
        print("搜索有效的 RLE 头 (width 8-32, height 8-32):")
        candidates = []
        for off in range(0, min(size - 4, 500), 2):
            result = check_rle_at(data, off, 8, 64, 8, 64)
            if result:
                candidates.append((off, result))

        if candidates:
            for off, (w, h) in candidates[:20]:
                print(f"  偏移{off}: {w}x{h}")
        else:
            print("  未找到有效RLE头")

        # 也检查字节76-86范围
        print(f"\n字节72-86的原始数据:")
        for off in [72, 74, 76, 78, 80, 82, 84, 86]:
            w = struct.unpack('<H', data[off:off+2])[0]
            h = struct.unpack('<H', data[off+2:off+4])[0]
            print(f"  {off}: width={w}, height={h}")

        # 关键问题：索引18的字节0-3是width=16, height=16
        # 字节4-?是什么？也许字节4-?就是RLE数据？
        print(f"\n=== 假设：从字节0开始就是RLE数据 ===")
        w0 = struct.unpack('<H', data[0:2])[0]
        h0 = struct.unpack('<H', data[2:4])[0]
        print(f"头: {w0}x{h0}")

        # 但字节4-11全是0，不是RLE数据...
        print(f"字节4-11: {data[4:12].hex()}")

        # 也许RLE数据从字节76开始？
        print(f"\n=== 检查字节76处的RLE数据 ===")
        print(f"字节76-83: {data[76:84].hex()}")
        w76 = struct.unpack('<H', data[76:78])[0]
        h76 = struct.unpack('<H', data[78:80])[0]
        print(f"作为width/height: {w76}x{h76}")

if __name__ == '__main__':
    main()