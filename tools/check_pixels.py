#!/usr/bin/env python3
"""
检查解码后的像素值
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def decode_rle_simple(data, w, h, screen_width=320):
    """简单RLE解码 - 不处理隔点模式"""
    if len(data) < 4:
        return None

    src = data[4:]
    src_idx = 0
    dst = bytearray()
    row_remain = w
    v8 = screen_width - w

    height = h
    while height > 0:
        c = row_remain
        while c > 0:
            if src_idx >= len(src):
                return None

            value = src[src_idx]
            src_idx += 1

            count_1 = ((value * 4) & 0xFF) >> 2
            if count_1 == 0:
                count_1 = 1
            count_1 += 1

            bit7 = (value >> 7) & 1
            bit6 = (value >> 6) & 1

            if not bit7:
                # 00-7F: 直接复制
                if src_idx + count_1 > len(src):
                    return None
                dst.extend(src[src_idx:src_idx + count_1])
                src_idx += count_1
            else:
                # 80-FF: RLE
                if not bit6:
                    # 80-BF: 跳过
                    dst.extend([0] * count_1)
                else:
                    # C0-FF: 需要字节
                    if src_idx >= len(src):
                        return None
                    byte = src[src_idx]
                    src_idx += 1
                    dst.extend([byte] * count_1)
            c -= count_1

        dst.extend([0] * v8)
        height -= 1

    return bytes(dst)

def main():
    with open(DAT_FILE, 'rb') as f:
        start, size = read_index(f, 18)
        f.seek(start)
        data = f.read(size)

        w = struct.unpack('<H', data[0:2])[0]
        h = struct.unpack('<H', data[2:4])[0]

        print(f"索引18: {w}x{h}")

        # 解码
        result = decode_rle_simple(data, w, h, 320)
        if result:
            print(f"解码: {len(result)} 字节")

            # 检查前16x16区域的像素值
            print("\n前16行每行的前16个像素 (16进制):")
            for row in range(min(16, len(result)//320)):
                pixels = result[row*320:row*320+16]
                nonzero = [f"{p:02x}" if p > 0 else ".." for p in pixels]
                print(f"  Row {row}: {' '.join(nonzero)}")

            # 统计
            nonzero = sum(1 for p in result if p > 0)
            print(f"\n非零像素: {nonzero}")

if __name__ == '__main__':
    main()