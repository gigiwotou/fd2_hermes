#!/usr/bin/env python3
"""
调试索引18的RLE解码
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def decode_rle_debug(data, w, h, screen_width=320):
    """带调试输出的RLE解码"""
    if len(data) < 4:
        return None

    src = data[4:]
    src_idx = 0
    dst = bytearray()

    print(f"RLE解码: width={w}, height={h}, screen_width={screen_width}")
    print(f"源数据长度: {len(src)} 字节")

    row_remain = w
    v8 = screen_width - w
    print(f"每行填充: {v8} 字节")

    height = h
    src_used_total = 0

    while height > 0:
        c = row_remain
        row_bytes = 0
        while c > 0:
            if src_idx >= len(src):
                print(f"  错误: src_idx={src_idx} >= len(src)={len(src)}")
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
                if not bit6:
                    # 复制
                    if src_idx + count_1 > len(src):
                        print(f"  错误: src越界复制")
                        return None
                    dst.extend(src[src_idx:src_idx + count_1])
                    src_idx += count_1
                    row_bytes += count_1
                else:
                    # 填充
                    if src_idx >= len(src):
                        print(f"  错误: src越界填充")
                        return None
                    byte = src[src_idx]
                    src_idx += 1
                    dst.extend([byte] * count_1)
                    row_bytes += count_1
                c -= count_1
            else:
                if not bit6:
                    # 跳过
                    dst.extend([0] * count_1)
                    row_bytes += count_1
                else:
                    # 隔点
                    if src_idx >= len(src):
                        print(f"  错误: src越界隔点")
                        return None
                    byte = src[src_idx]
                    src_idx += 1
                    for i in range(count_1):
                        dst.append(byte)
                        dst.append(0)
                    row_bytes += count_1 * 2
                c -= count_1

        # 行填充
        dst.extend([0] * v8)
        height -= 1

        if height % 5 == 0:
            print(f"  完成 {h - height}/{h} 行, src_idx={src_idx}, dst={len(dst)}")

    print(f"\n最终: dst={len(dst)} 字节, 预期={screen_width * h}")
    return bytes(dst), w, screen_width

def main():
    with open(DAT_FILE, 'rb') as f:
        start, size = read_index(f, 18)
        f.seek(start)
        data = f.read(size)

        w = struct.unpack('<H', data[0:2])[0]
        h = struct.unpack('<H', data[2:4])[0]

        print(f"=== 索引18 (16x16) ===")
        print(f"数据长度: {size}")
        print(f"头: width={w}, height={h}")
        print()

        decode_rle_debug(data, w, h, 320)

if __name__ == '__main__':
    main()