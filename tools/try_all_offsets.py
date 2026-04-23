#!/usr/bin/env python3
"""
尝试从每个offset位置解码24x24图像
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def try_decode_at(data, offset, expected_w, expected_h):
    """尝试从指定偏移解码"""
    if offset + 4 > len(data):
        return None

    chunk = data[offset:]
    w = struct.unpack('<H', chunk[0:2])[0]
    h = struct.unpack('<H', chunk[2:4])[0]

    if w != expected_w or h != expected_h:
        return None

    # RLE解码
    src = chunk[4:]
    src_idx = 0
    dst = bytearray()
    screen_width = 320
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
        height -= 1

    return bytes(dst)

def main():
    with open(DAT_FILE, 'rb') as f:
        start, size = read_index(f, 1)
        f.seek(start)
        data = f.read(size)

        # offset表从字节6开始
        sub_count = struct.unpack('<H', data[4:6])[0]
        print(f"索引1: {size} 字节, 24x24, {sub_count}个子项")

        print("\n尝试从每个offset解码24x24图像:")
        for i in range(min(sub_count, 20)):
            off = struct.unpack('<I', data[6 + i*4:10 + i*4])[0]

            result = try_decode_at(data, off, 24, 24)
            if result:
                nonzero = sum(1 for p in result if p > 0)
                print(f"  offset[{i}]=0x{off:04x}: 解码成功, 非零像素={nonzero}")
            else:
                # 打印该位置的数据
                chunk = data[off:off+8] if off + 8 <= size else b''
                print(f"  offset[{i}]=0x{off:04x}: 失败, 数据={chunk.hex()}")

        # 也许字节6-85之间还有RLE数据？让我检查字节86之后
        print("\n分析最后一个offset之后的数据 (字节2211+):")
        last_off = struct.unpack('<I', data[6 + 19*4:10 + 19*4])[0]
        print(f"最后offset: 0x{last_off:x}")

        if last_off + 24 <= size:
            chunk = data[last_off:last_off+24]
            print(f"数据: {chunk.hex()}")

if __name__ == '__main__':
    main()