#!/usr/bin/env python3
"""
FDOTHER.DAT 解码器 - 针对动画渲染资源
从 sub_2D80D 和 sub_31529 等关键函数提取的索引:
- 索引 0: 基础图片
- 索引 1, 2, 3, 4, 5: 各种角色图标
- 索引 9, 15, 16, 17: UI/背景元素
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    """读取 FDOTHER 索引: fseek(file, 4*index+6, 0)"""
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def decode_rle(data, screen_width=320):
    """sub_4E98D RLE 解码"""
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

            value = src[src_idx]
            src_idx += 1

            count_1 = ((value * 4) & 0xFF) >> 2
            if count_1 == 0:
                count_1 = 1
            count_1 += 1

            bit7 = (value >> 7) & 1
            bit6 = (value >> 6) & 1

            if not bit7:
                # bit7=0: 数据命令 (00-7F)
                if not bit6:
                    # bit6=0 (00-3F): 复制
                    if src_idx + count_1 > len(src):
                        return None
                    dst.extend(src[src_idx:src_idx + count_1])
                    src_idx += count_1
                else:
                    # bit6=1 (40-7F): 填充
                    if src_idx >= len(src):
                        return None
                    byte = src[src_idx]
                    src_idx += 1
                    dst.extend([byte] * count_1)
                c -= count_1
            else:
                # bit7=1: RLE命令 (80-FF)
                if not bit6:
                    # bit6=0 (80-BF): 跳过
                    dst.extend([0] * count_1)
                else:
                    # bit6=1 (C0-FF): 隔像素
                    if src_idx >= len(src):
                        return None
                    byte = src[src_idx]
                    src_idx += 1
                    for i in range(count_1):
                        dst.append(byte)
                        if len(dst) < screen_width * (height - h + 1):
                            dst.append(0)
                c -= count_1

        dst.extend([0] * v8)
        h -= 1

    return bytes(dst), width, screen_width

def save_raw(filename, data, width, height):
    """保存为原始RGB格式"""
    with open(filename, 'wb') as f:
        # 使用调色板索引保存为256色pgm
        f.write(f"P5\n{width} {height}\n255\n".encode())
        f.write(data)

def analyze_and_decode(file, idx, expected_desc=""):
    """分析并解码单个资源"""
    start, size = read_index(file, idx)
    file.seek(start)
    data = file.read(size)

    if len(data) < 4:
        return f"索引 {idx}: 数据太小 ({size} 字节)"

    w = struct.unpack('<H', data[0:2])[0]
    h = struct.unpack('<H', data[2:4])[0]

    result = f"索引 {idx}: {size} 字节, 尺寸 {w}x{h}"

    if expected_desc:
        result += f" ({expected_desc})"

    # 检查是否是 LMI1 动画
    if data[:4] == b'LMI1':
        frames = struct.unpack('<H', data[4:6])[0]
        result += f", LMI1动画 {frames} 帧"
        return result

    # 尝试 RLE 解码
    if w > 0 and h > 0 and w <= 320 and h <= 200:
        decoded = decode_rle(data, 320)
        if decoded:
            img, dec_w, dec_h = decoded
            result += f", 解码成功 {dec_w}x{dec_h}"

            # 保存
            save_raw(f'/home/yinming/fd2_hermes/decoded_images/res{idx:03d}.pgm', img, dec_w, dec_h)
        else:
            result += ", 解码失败"
    else:
        result += f", 跳过 (尺寸异常)"

    return result

def main():
    # 动画中实际使用的 FDOTHER 资源索引 (从反编译代码提取)
    animation_indices = [
        (0, "基础图片"),
        (1, "小图标 24x24"),
        (2, "结构化数据"),
        (3, "LMI1动画 23帧"),
        (9, "LMI1动画 12帧"),
        (15, "全屏背景 320x200"),
        (16, "宽幅背景 462x113"),
        (17, "宽幅背景 462x113"),
        (18, "头像 16x16"),
        (19, "头像 30x30"),
        (22, "小图标 14x14"),
        (32, "最小图标 10x10"),
        (33, "最小图标 10x10"),
    ]

    print("=== FDOTHER 动画资源解码 ===\n")

    with open(DAT_FILE, 'rb') as f:
        for idx, desc in animation_indices:
            result = analyze_and_decode(f, idx, desc)
            print(result)
            print()

if __name__ == '__main__':
    main()