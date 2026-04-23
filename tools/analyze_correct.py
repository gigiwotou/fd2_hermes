#!/usr/bin/env python3
"""
FDOTHER 索引1结构分析 - 正确版本
- 字节0-1: width (little-endian)
- 字节2-3: height (little-endian)
- 字节4-5: 子项数量
- 字节6+: 偏移表 (每项4字节, little-endian)
- RLE数据从偏移表第一项值开始
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def decode_rle(data, expected_w, expected_h):
    """RLE 解码"""
    if len(data) < 4:
        return None

    w = struct.unpack('<H', data[0:2])[0]
    h = struct.unpack('<H', data[2:4])[0]

    if expected_w and expected_h:
        if w != expected_w or h != expected_h:
            # 可能是另一个偏移处的数据
            if w > 320 or h > 300:
                return None

    src = data[4:]
    src_idx = 0
    dst = bytearray()
    width = w if expected_w else 320
    row_remain = width
    v8 = 320 - width

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
                        if len(dst) < 320 * (200 - height + 1):
                            dst.append(0)
                c -= count_1

        dst.extend([0] * v8)
        height -= 1

    return bytes(dst), width, 320

def main():
    with open(DAT_FILE, 'rb') as f:
        start, size = read_index(f, 1)
        f.seek(start)
        data = f.read(size)

        print(f"=== 索引 1 分析 ===")
        print(f"总大小: {size} 字节")

        w = struct.unpack('<H', data[0:2])[0]
        h = struct.unpack('<H', data[2:4])[0]
        sub_count = struct.unpack('<H', data[4:6])[0]

        print(f"width={w}, height={h}, 子项数={sub_count}")

        # 偏移表从字节6开始
        print("\n偏移表:")
        offsets = []
        for i in range(min(sub_count, 20)):
            off = 6 + i * 4
            if off + 4 <= size:
                val = struct.unpack('<I', data[off:off+4])[0]
                offsets.append(val)
                print(f"  子项{i}: 偏移=0x{val:x} ({val})")

        # 从第一个偏移处解码RLE数据
        print(f"\n尝试从偏移0x{offsets[0]:x}解码:")
        rle_start = offsets[0]
        rle_data = data[rle_start:]

        # 检查RLE头
        rle_w = struct.unpack('<H', rle_data[0:2])[0]
        rle_h = struct.unpack('<H', rle_data[2:4])[0]
        print(f"  RLE头: width={rle_w}, height={rle_h}")

        result = decode_rle(rle_data, None, None)
        if result:
            img, dec_w, dec_h = result
            print(f"  解码成功: {dec_w}x{dec_h}")

            # 保存
            with open(f'/home/yinming/fd2_hermes/decoded_images/res01_decoded.pgm', 'wb') as out:
                out.write(f"P5\n{dec_w}\n{dec_h}\n255\n".encode())
                out.write(img)
            print(f"  已保存")
        else:
            print(f"  解码失败")

        # 同样测试索引18
        print("\n=== 索引 18 分析 (对比) ===")
        f.seek(0, 0)
        start, size = read_index(f, 18)
        f.seek(start)
        data18 = f.read(size)

        w18 = struct.unpack('<H', data18[0:2])[0]
        h18 = struct.unpack('<H', data18[2:4])[0]
        sub_count18 = struct.unpack('<H', data18[4:6])[0]

        print(f"width={w18}, height={h18}, 子项数={sub_count18}")

        # 检查偏移表
        offsets18 = []
        for i in range(min(sub_count18, 20)):
            off = 6 + i * 4
            if off + 4 <= size:
                val = struct.unpack('<I', data18[off:off+4])[0]
                offsets18.append(val)

        print(f"偏移表: {[hex(o) for o in offsets18[:5]]}")

if __name__ == '__main__':
    main()