#!/usr/bin/env python3
"""
尝试从索引18的字节6开始解码
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def decode_rle(data, screen_width=320):
    """RLE 解码 - sub_4E98D"""
    if len(data) < 4:
        return None

    w = struct.unpack('<H', data[0:2])[0]
    h = struct.unpack('<H', data[2:4])[0]

    if w == 0 or h == 0 or w > 320 or h > 300:
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
                        if len(dst) < screen_width * (200 - height + 1):
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

        # 从字节6开始的数据
        print(f"\n从字节6开始的前40字节: {data[6:46].hex()}")

        # 检查字节6-7的uint16
        w_at_6 = struct.unpack('<H', data[6:8])[0]
        h_at_6 = struct.unpack('<H', data[8:10])[0]
        print(f"字节6-7作为width: {w_at_6}")
        print(f"字节8-9作为height: {h_at_6}")

        # 尝试从字节6解码
        rle_data = data[6:]
        print(f"\n从字节6解码:")
        result = decode_rle(rle_data, 320)
        if result:
            img, w, h = result
            print(f"  成功: {w}x{h}, 像素数={len(img)}")

            # 保存
            with open('/home/yinming/fd2_hermes/decoded_images/res18_from6.pgm', 'wb') as out:
                out.write(f"P5\n{w}\n{h}\n255\n".encode())
                out.write(img)
            print("  已保存到 res18_from6.pgm")
        else:
            print("  失败")

        # 也尝试从字节4开始
        print(f"\n从字节4解码:")
        rle_data = data[4:]
        result = decode_rle(rle_data, 320)
        if result:
            img, w, h = result
            print(f"  成功: {w}x{h}")
        else:
            print("  失败")

        # 尝试从字节8开始 (假设字节6是子项数量)
        print(f"\n从字节8解码 (假设字节6是子项数):")
        rle_data = data[8:]
        result = decode_rle(rle_data, 320)
        if result:
            img, w, h = result
            print(f"  成功: {w}x{h}")
        else:
            print("  失败")

if __name__ == '__main__':
    main()