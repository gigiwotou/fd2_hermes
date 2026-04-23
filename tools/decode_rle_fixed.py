#!/usr/bin/env python3
"""
FDOTHER RLE 解码 - 基于 sub_4E98D 逆向分析精确实现
关键逻辑:
- value = *src++
- v12 = 2 * value  (即左移1位，测试bit6和bit7)
- count_1 = ((value * 4) & 0xFF) >> 2 + 1 = (value & 0x3F) + 1

根据 bit7(命令) 和 bit6(类型) 组合:
- bit7=0, bit6=0 (00-3F): 复制数据
- bit7=0, bit6=1 (40-7F): 填充单色
- bit7=1, bit6=0 (80-BF): 跳过(透明)
- bit7=1, bit6=1 (C0-FF): 隔像素写入
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def read_resource(file, index):
    start, size = read_index(file, index)
    file.seek(start)
    return file.read(size)

def decode_rle_final(data, screen_width=320):
    """精确实现 sub_4E98D"""
    if len(data) < 4:
        return None

    width = struct.unpack('<H', data[0:2])[0]
    height = struct.unpack('<H', data[2:4])[0]

    if width == 0 or height == 0 or height > 300 or width > 320:
        return None

    src = data[4:]
    src_idx = 0
    dst = bytearray()
    row_remain = width
    v8 = screen_width - width  # 行跳转值

    h = height
    while h > 0:
        c = row_remain
        while c > 0:
            if src_idx >= len(src):
                return None

            value = src[src_idx]
            src_idx += 1
            v12 = (value * 2) & 0xFF  # 左移1位，bit7移入CF，bit6移入bit7

            count_1 = ((value * 4) & 0xFF) >> 2
            if count_1 == 0:
                count_1 = 1
            count_1 += 1

            # 测试 bit7 (通过 v12 的进位)
            bit7 = (value >> 7) & 1
            bit6 = (value >> 6) & 1

            if not bit7:
                # bit7=0: 数据命令 (00-7F)
                if not bit6:
                    # bit6=0 (00-3F): qmemcpy 复制
                    if src_idx + count_1 > len(src):
                        return None
                    dst.extend(src[src_idx:src_idx + count_1])
                    src_idx += count_1
                else:
                    # bit6=1 (40-7F): memset 填充
                    if src_idx >= len(src):
                        return None
                    byte = src[src_idx]
                    src_idx += 1
                    dst.extend([byte] * count_1)
                c -= count_1
            else:
                # bit7=1: RLE命令 (80-FF)
                if not bit6:
                    # bit6=0 (80-BF): 跳过 dst += count_1
                    dst.extend([0] * count_1)
                else:
                    # bit6=1 (C0-FF): 隔像素 memset
                    if src_idx >= len(src):
                        return None
                    byte = src[src_idx]
                    src_idx += 1
                    for i in range(count_1):
                        dst.append(byte)
                        if len(dst) < screen_width:
                            dst.append(0)  # 透明像素
                c -= count_1

        # 行跳转
        dst.extend([0] * v8)
        h -= 1

    return bytes(dst), width, screen_width

def save_pgm(filename, data, width, height):
    """保存为PGM格式"""
    with open(filename, 'wb') as f:
        f.write(f"P5\n{width} {height}\n255\n".encode())
        f.write(data)

def main():
    with open(DAT_FILE, 'rb') as f:
        print("=== FDOTHER RLE 解码测试 ===\n")

        # 测试几个资源
        tests = [
            (18, 16, 16, "头像"),
            (19, 30, 30, "头像"),
            (1, 24, 24, "小图标"),
        ]

        for idx, expected_w, expected_h, desc in tests:
            data = read_resource(f, idx)
            print(f"索引 {idx} ({desc}, 预期 {expected_w}x{expected_h}):")

            actual_w = struct.unpack('<H', data[0:2])[0]
            actual_h = struct.unpack('<H', data[2:4])[0]
            print(f"  头文件: w={actual_w}, h={actual_h}")
            print(f"  前16字节: {data[:16].hex()}")

            result = decode_rle_final(data, 320)
            if result:
                img, w, sw = result
                h_actual = len(img) // sw
                print(f"  解码成功: {w}x{h_actual}")

                save_pgm(f'/home/yinming/fd2_hermes/decoded_images/res{idx}_final.pgm', img, sw, h_actual)

                # 统计非零像素
                nonzero = sum(1 for b in img if b > 0)
                print(f"  非零像素: {nonzero} / {len(img)} ({100*nonzero/len(img):.1f}%)")
            else:
                print(f"  解码失败")
            print()

if __name__ == '__main__':
    main()