#!/usr/bin/env python3
"""
分析索引1偏移0x56处的RLE数据
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def decode_rle_standard(data, w, h, screen_width=320):
    """标准RLE解码"""
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

            # count_1 计算
            count_1 = ((value * 4) & 0xFF) >> 2
            if count_1 == 0:
                count_1 = 1
            count_1 += 1

            bit7 = (value >> 7) & 1
            bit6 = (value >> 6) & 1

            if not bit7:
                # bit7=0: COPY 或 FILL
                if not bit6:
                    # 00-3F: COPY
                    if src_idx + count_1 > len(src):
                        return None
                    dst.extend(src[src_idx:src_idx + count_1])
                    src_idx += count_1
                else:
                    # 40-7F: FILL
                    if src_idx >= len(src):
                        return None
                    byte = src[src_idx]
                    src_idx += 1
                    dst.extend([byte] * count_1)
                c -= count_1
            else:
                # bit7=1: RLE 命令
                if not bit6:
                    # 80-BF: SKIP
                    dst.extend([0] * count_1)
                else:
                    # C0-FF: INTERLEAVE
                    if src_idx >= len(src):
                        return None
                    byte = src[src_idx]
                    src_idx += 1
                    # 隔像素写入
                    for i in range(count_1):
                        dst.append(byte)
                        if len(dst) < screen_width * 200:
                            dst.append(0)
                c -= count_1

        dst.extend([0] * v8)
        height -= 1

    return bytes(dst), w, screen_width

def main():
    with open(DAT_FILE, 'rb') as f:
        start, size = read_index(f, 1)
        f.seek(start)
        data = f.read(size)

        print(f"索引1: {size} 字节")
        print(f"头: width={struct.unpack('<H', data[0:2])[0]}, height={struct.unpack('<H', data[2:4])[0]}")

        # 尝试从偏移0x56解码
        rle_offset = 0x56
        print(f"\n从偏移0x56 ({rle_offset}) 解码:")
        rle_data = data[rle_offset:]

        w = struct.unpack('<H', rle_data[0:2])[0]
        h = struct.unpack('<H', rle_data[2:4])[0]
        print(f"  RLE头: width={w}, height={h}")

        if 8 <= w <= 64 and 8 <= h <= 64:
            result = decode_rle_standard(rle_data, w, h, 320)
            if result:
                img, dec_w, dec_h = result
                print(f"  解码成功: {dec_w}x{dec_h}, {len(img)}字节")
            else:
                print(f"  解码失败")
        else:
            print(f"  尺寸无效，跳过")

        # 也分析offset表后的RLE数据
        print("\n分析offset表后的第一个DWORD作为偏移:")
        off_val = struct.unpack('<I', data[6:10])[0]
        print(f"  字节6-9的DWORD值: 0x{off_val:x} ({off_val})")

        # 也许offset表后面紧接着就是RLE数据？让我检查字节24+
        print("\n字节24-50:")
        print(f"  {data[24:50].hex()}")

        # 如果这是RLE数据
        rle_data2 = data[24:]
        w2 = struct.unpack('<H', rle_data2[0:2])[0]
        h2 = struct.unpack('<H', rle_data2[2:4])[0]
        print(f"\n从字节24的RLE头: {w2}x{h2}")

if __name__ == '__main__':
    main()