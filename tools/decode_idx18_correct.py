#!/usr/bin/env python3
"""
FDOTHER 索引18完整分析
假设字节0-3是RLE头 (width, height)，字节4+是RLE数据
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def decode_rle_raw(data, w, h, screen_width=320):
    """直接RLE解码"""
    if len(data) < 4:
        return None

    src = data[4:]  # 跳过width,height头
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
                    # 复制
                    if src_idx + count_1 > len(src):
                        return None
                    dst.extend(src[src_idx:src_idx + count_1])
                    src_idx += count_1
                else:
                    # 填充
                    if src_idx >= len(src):
                        return None
                    byte = src[src_idx]
                    src_idx += 1
                    dst.extend([byte] * count_1)
                c -= count_1
            else:
                if not bit6:
                    # 跳过
                    dst.extend([0] * count_1)
                else:
                    # 隔点
                    if src_idx >= len(src):
                        return None
                    byte = src[src_idx]
                    src_idx += 1
                    for i in range(count_1):
                        dst.append(byte)
                        dst.append(0)
                c -= count_1

        dst.extend([0] * v8)
        height -= 1

    return bytes(dst), w, screen_width

def main():
    with open(DAT_FILE, 'rb') as f:
        start, size = read_index(f, 18)
        f.seek(start)
        data = f.read(size)

        print(f"索引18: {size} 字节")

        w = struct.unpack('<H', data[0:2])[0]
        h = struct.unpack('<H', data[2:4])[0]
        print(f"width={w}, height={h}")

        # 解码
        result = decode_rle_raw(data, w, h, 320)
        if result:
            img, dec_w, dec_h = result
            print(f"解码成功: {dec_w}x{dec_h}, 像素数={len(img)}")

            # 统计
            nonzero = sum(1 for p in img if p > 0)
            print(f"非零像素: {nonzero} ({100*nonzero/len(img):.1f}%)")

            # 保存
            with open('/home/yinming/fd2_hermes/decoded_images/res18_final.pgm', 'wb') as out:
                out.write(f"P5\n{dec_w}\n{320}\n255\n".encode())
                out.write(img)
            print("已保存")
        else:
            print("解码失败")

        # 分析字节4-7的含义
        print(f"\n字节4-7: {data[4:8].hex()} = {struct.unpack('<I', data[4:8])[0]}")
        print(f"字节8-11: {data[8:12].hex()} = {struct.unpack('<I', data[8:12])[0]}")
        print(f"字节12-15: {data[12:16].hex()} = {struct.unpack('<I', data[12:16])[0]}")

        # 这些值是否是偏移？0x48=72, 0x6d=109, 0x23b=571...
        print(f"\n如果字节8-11是偏移 (0x48 = 72):")
        if 72 + 4 <= size:
            chunk = data[72:76]
            w2 = struct.unpack('<H', chunk[0:2])[0]
            h2 = struct.unpack('<H', chunk[2:4])[0]
            print(f"  偏移72处: width={w2}, height={h2}")

if __name__ == '__main__':
    main()