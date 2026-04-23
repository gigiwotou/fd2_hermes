#!/usr/bin/env python3
"""
暴力测试 RLE 解码参数
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def decode_rle_brute(data, start_offset, width, height, screen_width=320):
    """尝试解码，返回非零像素数和像素值分布"""
    if start_offset + 4 > len(data):
        return None

    src = data[start_offset + 4:]  # 跳过width,height头
    src_idx = 0
    dst = bytearray()
    row_remain = width
    v8 = screen_width - width

    h = height
    while h > 0:
        c = row_remain
        while c > 0:
            if src_idx >= len(src):
                return None

            value = src[src_idx]
            src_idx += 1

            # 解析命令
            count_1 = ((value * 4) & 0xFF) >> 2
            if count_1 == 0:
                count_1 = 1
            count_1 += 1

            bit7 = (value >> 7) & 1
            bit6 = (value >> 6) & 1

            if not bit7:
                # 直接数据
                if not bit6:
                    if src_idx + count_1 > len(src):
                        return None
                    dst.extend(src[src_idx:src_idx + count_1])
                    src_idx += count_1
                else:
                    if src_idx >= len(src):
                        return None
                    byte = src[src_idx]
                    src_idx += 1
                    dst.extend([byte] * count_1)
                c -= count_1
            else:
                # RLE
                if not bit6:
                    dst.extend([0] * count_1)
                else:
                    if src_idx >= len(src):
                        return None
                    byte = src[src_idx]
                    src_idx += 1
                    dst.extend([byte] * count_1)
                c -= count_1

        dst.extend([0] * v8)
        h -= 1

    return bytes(dst)

def analyze_pixels(data):
    """分析像素值分布"""
    if not data:
        return 0, []

    nonzero = sum(1 for p in data if p > 0)
    # 统计不同像素值的数量
    unique = len(set(data))
    return nonzero, unique

def main():
    with open(DAT_FILE, 'rb') as f:
        # 测试索引18
        start, size = read_index(f, 18)
        f.seek(start)
        data = f.read(size)

        print("=== 索引 18 (16x16) 暴力测试 ===\n")

        # 测试不同的RLE数据起始位置
        for rle_start in [4, 8, 10, 12, 72, 76]:
            for w in [16, 24, 32]:
                for h in [16, 24, 32]:
                    if rle_start + 4 > size:
                        continue

                    result = decode_rle_brute(data, rle_start, w, h, 320)
                    if result:
                        nonzero, unique = analyze_pixels(result)
                        if 50 < nonzero < 500 and unique > 5:
                            print(f"start={rle_start}, size={w}x{h}: nonzero={nonzero}, unique={unique}")

        # 尝试不用width/height头，直接用给定尺寸
        print("\n直接用给定尺寸解码:")
        for rle_start in [4, 72, 76, 86]:
            result = decode_rle_brute(data, rle_start - 4, 16, 16, 320)
            if result:
                nonzero, unique = analyze_pixels(result)
                print(f"  从{rle_start}开始: nonzero={nonzero}, unique={unique}")

        # 关键发现：字节72处数据
        print(f"\n字节72处原始数据前30字节:")
        print(f"  {data[72:102].hex()}")

        # 也许需要从字节72+4开始（跳过某个头）？
        for header_skip in [0, 4, 6, 8]:
            off = 72 + header_skip
            w = struct.unpack('<H', data[off:off+2])[0] if off + 2 <= size else 0
            h = struct.unpack('<H', data[off+2:off+4])[0] if off + 4 <= size else 0
            print(f"  字节{off}: width={w}, height={h}")

if __name__ == '__main__':
    main()