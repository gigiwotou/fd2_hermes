#!/usr/bin/env python3
"""
检查索引1的offset表后的RLE数据
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def decode_rle(data, w, h, screen_width=320):
    """RLE解码"""
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

        w = struct.unpack('<H', data[0:2])[0]
        h = struct.unpack('<H', data[2:4])[0]
        sub_count = struct.unpack('<H', data[4:6])[0]

        print(f"索引1: {size} 字节, {w}x{h}, {sub_count}个子项")

        # offset表从字节6开始，占用 sub_count * 4 字节
        offset_table_end = 6 + sub_count * 4
        print(f"Offset表结束于字节: {offset_table_end}")

        # 检查offset表后的数据
        print(f"\noffset表后 (字节{offset_table_end}-{offset_table_end+30}):")
        print(f"  {data[offset_table_end:offset_table_end+30].hex()}")

        # 尝试从offset表后作为RLE数据解码
        rle_data = data[offset_table_end:]
        rw = struct.unpack('<H', rle_data[0:2])[0]
        rh = struct.unpack('<H', rle_data[2:4])[0]
        print(f"\n从字节{offset_table_end}的RLE头: {rw}x{rh}")

        # 也许是24x24?
        result = decode_rle(rle_data, 24, 24, 320)
        if result:
            nonzero = sum(1 for p in result if p > 0)
            print(f"解码24x24: 成功, 非零像素={nonzero}")
        else:
            print(f"解码24x24: 失败")

        # 尝试直接解码offset值处的数据，但用24x24作为尺寸
        first_offset = struct.unpack('<I', data[6:10])[0]
        print(f"\n第一个offset: 0x{first_offset:x}")

        # 也许offset处的数据没有标准RLE头？
        # 让我直接解码并看看结果
        # 假设RLE数据从offset表后开始，并且前2字节是某种标记
        # 然后是24x24的像素数据

        # 让我检查offset 0x56处作为RLE数据
        off_data = data[0x56:]
        print(f"\n从offset 0x56的数据:")
        print(f"  前20字节: {off_data[:20].hex()}")

        # 这些数据看起来像RLE命令
        # 0x81 0x60 -> bit7=1, bit6=0 -> SKIP count=((0x81*4)&0xFF)>>2 + 1 = 4+1=5
        # 但让我手动检查
        value = 0x81
        count_1 = ((value * 4) & 0xFF) >> 2
        if count_1 == 0:
            count_1 = 1
        count_1 += 1
        bit7 = (value >> 7) & 1
        bit6 = (value >> 6) & 1
        print(f"\n第一个字节 0x81:")
        print(f"  bit7={bit7}, bit6={bit6}")
        print(f"  count_1 = {count_1}")

if __name__ == '__main__':
    main()