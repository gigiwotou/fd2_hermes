#!/usr/bin/env python3
"""
检查索引18的实际RLE数据位置
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

        # 字节8-11是0x48 (72)，可能是第一个RLE数据的偏移
        first_rle_offset = 0x48  # 72
        print(f"\n从偏移{first_rle_offset} (0x{first_rle_offset:x}) 开始:")
        print(f"  前32字节: {data[first_rle_offset:first_rle_offset+32].hex()}")

        w = struct.unpack('<H', data[first_rle_offset:first_rle_offset+2])[0]
        h = struct.unpack('<H', data[first_rle_offset+2:first_rle_offset+4])[0]
        print(f"  width={w}, height={h}")

        # 如果这是RLE数据，那么解码它
        if 8 <= w <= 64 and 8 <= h <= 64:
            print(f"\n这可能是RLE数据! 尝试解码...")

            # RLE解码
            src = data[first_rle_offset+4:]
            src_idx = 0
            dst = bytearray()
            row_remain = w
            v8 = 320 - w

            height = h
            while height > 0:
                c = row_remain
                while c > 0:
                    if src_idx >= len(src):
                        print(f"  错误: src越界")
                        break

                    value = src[src_idx]
                    src_idx += 1

                    count_1 = ((value * 4) & 0xFF) >> 2
                    if count_1 == 0:
                        count_1 = 1
                    count_1 += 1

                    bit7 = (value >> 7) & 1
                    bit6 = (value >> 6) & 1

                    if not bit7:
                        # 直接复制
                        if src_idx + count_1 > len(src):
                            print(f"  错误: src越界2")
                            break
                        dst.extend(src[src_idx:src_idx + count_1])
                        src_idx += count_1
                    else:
                        if not bit6:
                            # 跳过
                            dst.extend([0] * count_1)
                        else:
                            # 需要字节
                            if src_idx >= len(src):
                                break
                            byte = src[src_idx]
                            src_idx += 1
                            dst.extend([byte] * count_1)
                    c -= count_1

                dst.extend([0] * v8)
                height -= 1

            print(f"  解码结果: {len(dst)} 字节")

            # 检查前16x16
            print(f"\n  前16行每行的前16个像素:")
            for row in range(min(h, 16)):
                pixels = dst[row*320:row*320+16]
                nonzero = [f"{p:02x}" if p > 0 else ".." for p in pixels]
                print(f"    Row {row}: {' '.join(nonzero)}")

if __name__ == '__main__':
    main()