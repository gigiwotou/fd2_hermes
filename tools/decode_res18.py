#!/usr/bin/env python3
"""
正确解码sub_count=0的FDOTHER资源
索引18: width=16, height=16, RLE数据从字节4开始
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def decode_rle_simple(data, start, width, height, screen_width=320):
    """简单RLE解码"""
    src = data[start:]
    src_idx = 0
    dst = bytearray()

    v8 = screen_width - width  # 行填充

    print(f"解码: {width}x{height}, screen_width={screen_width}, v8={v8}")
    print(f"RLE数据前40字节: {src[:40].hex()}")

    h = height
    while h > 0:
        c = width
        while c > 0:
            if src_idx >= len(src):
                print(f"  源数据耗尽 at src_idx={src_idx}")
                return bytes(dst)

            value = src[src_idx]
            src_idx += 1

            # 从代码提取的算法
            count_1 = ((value * 4) & 0xFF) >> 2
            if count_1 == 0:
                count_1 = 1
            count_1 += 1

            bit7 = (value >> 7) & 1
            bit6 = (value >> 6) & 1

            if not bit7:
                # 直接数据
                if not bit6:
                    # COPY - 直接复制
                    if src_idx + count_1 > len(src):
                        count_1 = len(src) - src_idx
                    dst.extend(src[src_idx:src_idx + count_1])
                    src_idx += count_1
                    c -= count_1
                else:
                    # FILL - 单色填充
                    if src_idx >= len(src):
                        break
                    byte = src[src_idx]
                    src_idx += 1
                    dst.extend([byte] * count_1)
                    c -= count_1
            else:
                # RLE
                if not bit6:
                    # SKIP - 透明跳过
                    dst.extend([0] * count_1)
                    c -= count_1
                else:
                    # INTER - 隔像素写入
                    if src_idx >= len(src):
                        break
                    byte = src[src_idx]
                    src_idx += 1
                    dst.extend([byte] * count_1)
                    c -= count_1

        # 行尾填充
        if c > 0:
            dst.extend([0] * c)
        dst.extend([0] * v8)
        h -= 1

    print(f"解码完成: {len(dst)} 字节")
    return bytes(dst)

def save_pgm(data, width, height, filename):
    """保存为PGM"""
    # 先扩展到screen_width x height
    screen_w = 320
    expanded = bytearray(screen_w * height)
    for y in range(height):
        expanded[y * screen_w:(y+1) * screen_w] = data[y * screen_w:(y+1) * screen_w]

    with open(filename, 'wb') as f:
        f.write(f"P5\n{width} {height}\n255\n".encode())
        f.write(bytes(data))

    # 也保存裁剪版本
    with open(filename.replace('.pgm', '_crop.pgm'), 'wb') as f:
        f.write(f"P5\n{width} {height}\n255\n".encode())
        f.write(bytes(data))

def main():
    with open(DAT_FILE, 'rb') as f:
        start, size = read_index(f, 18)
        f.seek(start)
        data = f.read(size)

        # 索引18: sub_count=0, width=16, height=16
        w = struct.unpack('<H', data[0:2])[0]
        h = struct.unpack('<H', data[2:4])[0]
        sub_count = struct.unpack('<H', data[4:6])[0]

        print(f"索引18: {w}x{h}, sub_count={sub_count}\n")

        # 如果sub_count=0，RLE数据从字节4开始？
        # 如果sub_count>0，RLE数据从某处开始...

        # 尝试从字节4开始解码
        print("=== 尝试从字节4解码 ===")
        result = decode_rle_simple(data, 4, w, h, 320)

        if len(result) == 320 * h:
            save_pgm(result, 320, h, 'decoded_images/res018_v4.pgm')
            print(f"已保存 res018_v4.pgm ({len(result)} 字节)")
        elif len(result) > 0:
            # 可能是裁剪尺寸
            actual_w = min(w, 320)
            save_pgm(result, actual_w, h, 'decoded_images/res018_v4.pgm')
            print(f"已保存 res018_v4.pgm (实际{len(result)}字节)")

if __name__ == '__main__':
    main()