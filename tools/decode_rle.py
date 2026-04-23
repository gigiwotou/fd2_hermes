#!/usr/bin/env python3
"""
FDOTHER.DAT RLE 解码验证
基于 sub_4E98D 逆向分析
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    """读取 FDOTHER 索引: fseek(file, 4*index+6, 0)"""
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def decode_rle_v2(data, screen_width=320):
    """
    RLE 解码 - sub_4E98D 逻辑修正版
    2位命令码 (bit7=命令类型, bit6=子类型):
    - 00 (0x00-0x3F): 原始数据复制, count = (value & 0x3F) + 1
    - 01 (0x40-0x7F): 单色填充, count = (value & 0x3F) + 1
    - 10 (0x80-0xBF): 透明跳过, count = (value & 0x3F) + 1
    - 11 (0xC0-0xFF): 隔像素写入, count = (value & 0x3F) + 1
    """
    if len(data) < 4:
        return None

    width = struct.unpack('<H', data[0:2])[0]
    height = struct.unpack('<H', data[2:4])[0]

    if width == 0 or height == 0:
        return None

    src = data[4:]
    src_pos = 0

    # 输出行缓冲
    row_buf = []
    dst_rows = []

    while height > 0:
        x = 0
        while x < width:
            if src_pos >= len(src):
                return None

            cmd = src[src_pos]
            src_pos += 1

            # count = (cmd & 0x3F) + 1
            count = (cmd & 0x3F) + 1

            if cmd & 0x80:
                # RLE 命令
                if cmd & 0x40:
                    # 01 或 11: 需要数据字节
                    if src_pos >= len(src):
                        return None
                    byte = src[src_pos]
                    src_pos += 1

                    if cmd & 0x20:
                        # 11 (0xC0-0xFF): 隔像素写入
                        for i in range(count):
                            row_buf.append(byte)
                            if x + 1 < width:
                                row_buf.append(0)  # 透明
                                x += 1
                            x += 1
                    else:
                        # 01 (0x40-0x7F): 单色填充
                        for i in range(count):
                            row_buf.append(byte)
                            x += 1
                else:
                    # 10 (0x80-0xBF): 透明跳过
                    for i in range(count):
                        row_buf.append(0)
                        x += 1
            else:
                # 00 (0x00-0x3F): 原始数据
                for i in range(count):
                    if src_pos >= len(src):
                        return None
                    row_buf.append(src[src_pos])
                    src_pos += 1
                    x += 1

        # 行跳转 (到达屏幕右端后跳过到下一行开始位置)
        padding = screen_width - width
        row_buf.extend([0] * padding)
        dst_rows.append(bytes(row_buf))
        row_buf = []
        height -= 1

    return b''.join(dst_rows), width, screen_width

def save_bmp(filename, data, width, height, palette=None):
    """保存为BMP文件"""
    with open(filename, 'wb') as f:
        # BMP Header
        f.write(b'BM')
        row_size = (width * 3 + 3) & ~3  # 行字节对齐
        f.write(struct.pack('<I', 14 + 40 + row_size * height))  # 文件大小
        f.write(struct.pack('<H', 0))  # 保留
        f.write(struct.pack('<H', 0))  # 保留
        f.write(struct.pack('<I', 14 + 40))  # 数据偏移

        # DIB Header
        f.write(struct.pack('<I', 40))  # header size
        f.write(struct.pack('<i', width))  # width
        f.write(struct.pack('<i', height))  # height (+ = bottom-up)
        f.write(struct.pack('<H', 1))  # planes
        f.write(struct.pack('<H', 24))  # bits per pixel
        f.write(struct.pack('<I', 0))  # compression
        f.write(struct.pack('<I', row_size * height))  # image size
        f.write(struct.pack('<i', 0))  # x pixels per meter
        f.write(struct.pack('<i', 0))  # y pixels per meter
        f.write(struct.pack('<I', 0))  # colors used
        f.write(struct.pack('<I', 0))  # important colors

        # 像素数据 (BGR)
        for row in reversed(data if isinstance(data, list) else [data]):
            f.write(row)

def main():
    with open(DAT_FILE, 'rb') as f:
        print("=== 测试 RLE 解码 ===\n")

        # 测试几个已知尺寸的资源
        test_indices = [1, 10, 11, 16, 17, 18, 19, 22]

        for idx in test_indices:
            start, size = read_index(f, idx)
            f.seek(start)
            data = f.read(size)

            if len(data) < 4:
                continue

            w = struct.unpack('<H', data[0:2])[0]
            h = struct.unpack('<H', data[2:4])[0]

            print(f"索引 {idx}: {size} 字节, 头={data[:4].hex()}")

            if w > 0 and h > 0 and w <= 320 and h <= 200:
                result = decode_rle_v2(data, 320)
                if result:
                    img_data, dec_w, dec_h = result
                    bmp_data = []
                    for i in range(dec_h):
                        row = img_data[i*dec_w:(i+1)*dec_w]
                        bmp_row = []
                        for p in row:
                            # 使用简单灰度调色板
                            bmp_row.extend([p, p, p])
                        bmp_data.append(bytes(bmp_row))

                    save_bmp(f'/home/yinming/fd2_hermes/decoded_images/res{idx:03d}_test.bmp',
                            bmp_data, dec_w, dec_h)
                    print(f"  -> 解码成功: {dec_w}x{dec_h}, 已保存")
                else:
                    print(f"  -> 解码失败")
            else:
                print(f"  -> 跳过 (尺寸异常: {w}x{h})")
            print()

if __name__ == '__main__':
    main()