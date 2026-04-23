#!/usr/bin/env python3
"""
FDOTHER RLE 解码调试
用简单图案资源验证解码逻辑
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

def decode_rle_simple(data, screen_width=320):
    """
    简化的 RLE 解码
    命令格式 (2位):
    - 00 (0x00-0x3F): 复制, count=(cmd&0x3F)+1
    - 01 (0x40-0x7F): 填充, count=(cmd&0x3F)+1, 读1字节重复
    - 10 (0x80-0xBF): 跳过, count=(cmd&0x3F)+1
    - 11 (0xC0-0xFF): 隔点, count=(cmd&0x3F)+1, 读1字节, 隔1像素写
    """
    if len(data) < 4:
        return None

    width = struct.unpack('<H', data[0:2])[0]
    height = struct.unpack('<H', data[2:4])[0]

    if width == 0 or height > 200 or width > 320:
        return None

    src = data[4:]
    src_pos = 0

    row_buf = []

    print(f"  解码: {width}x{height}, screen_width={screen_width}")

    for row in range(height):
        x = 0
        while x < width:
            if src_pos >= len(src):
                print(f"  错误: src_pos={src_pos} >= len(src)={len(src)} at row={row}, x={x}")
                return None

            cmd = src[src_pos]
            src_pos += 1

            # count = (cmd & 0x3F) + 1
            count = (cmd & 0x3F) + 1

            if cmd < 0x80:
                # bit7=0: 复制
                end_x = min(x + count, width)
                actual_count = end_x - x
                for i in range(actual_count):
                    if src_pos >= len(src):
                        print(f"  错误: src 越界 at row={row}, x={x}")
                        return None
                    row_buf.append(src[src_pos])
                    src_pos += 1
                x = end_x

                if x < width and (cmd & 0x3F) + 1 > actual_count:
                    # 还有更多数据在同一行
                    pass
            elif cmd < 0xC0:
                # 80-BF: 跳过
                if cmd & 0x40:
                    # 跳过
                    for i in range(count):
                        if x < width:
                            row_buf.append(0)
                            x += 1
                else:
                    # 40-7F: 填充
                    if src_pos >= len(src):
                        return None
                    byte = src[src_pos]
                    src_pos += 1
                    for i in range(count):
                        if x < width:
                            row_buf.append(byte)
                            x += 1
            else:
                # C0-FF: 隔点写入
                if src_pos >= len(src):
                    return None
                byte = src[src_pos]
                src_pos += 1
                for i in range(count):
                    if x < width:
                        row_buf.append(byte)
                        x += 1
                        if x < width:
                            row_buf.append(0)  # 透明像素
                            x += 1

        # 行末尾填充到 screen_width
        while x < screen_width:
            row_buf.append(0)
            x += 1

    return bytes(row_buf), width, screen_width

def decode_rle_v3(data, screen_width=320):
    """sub_4E98D 逻辑的精确实现"""
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
    v8 = screen_width - width

    h = height
    while h > 0:
        c = row_remain
        while c > 0:
            if src_idx >= len(src):
                return None
            v = src[src_idx]
            src_idx += 1
            v12 = (v * 2) & 0xFF

            # 测试 bit 7
            if not (v & 0x80):
                # bit7=0: 复制
                count_1 = ((v * 4) & 0xFF) >> 2
                if count_1 == 0:
                    count_1 = 1
                count_1 += 1

                if v & 0x40:
                    # bit6=1: 跳过 (00-3F 中 bit6=1)
                    dst.extend([0] * count_1)
                else:
                    # bit6=0: 复制数据 (00-3F 中 bit6=0)
                    if src_idx + count_1 > len(src):
                        return None
                    dst.extend(src[src_idx:src_idx + count_1])
                    src_idx += count_1
                c -= count_1
            else:
                # bit7=1: RLE
                count_1 = ((v * 4) & 0xFF) >> 2
                if count_1 == 0:
                    count_1 = 1
                count_1 += 1

                # 测试 bit 6
                if v12 & 0x80:
                    # bit6=1: 10 (80-BF) 跳过
                    dst.extend([0] * count_1)
                else:
                    # bit6=0: 01/11 (40-7F/C0-FF) 需要字节
                    if src_idx >= len(src):
                        return None
                    byte = src[src_idx]
                    src_idx += 1

                    if v12 & 0x40:
                        # 11 (C0-FF): 隔点
                        c_remain = count_1
                        while c_remain > 0:
                            dst.append(byte)
                            c_remain -= 1
                            if c_remain > 0:
                                dst.append(0)
                                c_remain -= 1
                            if c_remain > 0:
                                dst.append(0)  # 跳过一个像素
                                c_remain -= 1
                    else:
                        # 01 (40-7F): 填充
                        dst.extend([byte] * count_1)
                c -= count_1
        # 行跳转
        dst.extend([0] * v8)
        h -= 1

    return bytes(dst), width, screen_width

def main():
    with open(DAT_FILE, 'rb') as f:
        print("=== 调试 RLE 解码 ===\n")

        # 索引 18: 16x16 简单图标
        data = read_resource(f, 18)
        print(f"索引 18: 16x16 头像")
        print(f"  数据前32字节: {data[:32].hex()}")

        result = decode_rle_v3(data, 320)
        if result:
            img, w, sw = result
            print(f"  结果: {w}x{len(img)//sw}, 解码成功")

            # 保存为pgm查看
            with open(f'/home/yinming/fd2_hermes/decoded_images/res18_v3.pgm', 'wb') as out:
                out.write(f"P5\n{w} {len(img)//sw}\n255\n".encode())
                out.write(img)
            print(f"  已保存为 PGM")
        else:
            print(f"  解码失败")

if __name__ == '__main__':
    main()