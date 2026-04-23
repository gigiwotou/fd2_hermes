#!/usr/bin/env python3
"""
FDOTHER.DAT 图片验证脚本
验证 sub_2EB9F 的解码逻辑是否正确
"""
import struct
import sys

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    """读取 FDOTHER 索引表获取资源位置 sub_111BA: fseek(file, 4*index+6, 0)"""
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def read_resource(file, index):
    """读取指定索引的 FDOTHER 资源"""
    start, size = read_index(file, index)
    file.seek(start)
    data = file.read(size)
    return data

def decode_rle(data, width, height, screen_width, value=-1):
    """RLE 解码 - sub_4E98D 逻辑"""
    if len(data) < 4:
        return None

    count = struct.unpack('<H', data[0:2])[0]
    height_decode = struct.unpack('<H', data[2:4])[0]

    # 实际应该用传入的 width/height，但这里用解码出来的
    actual_width = count
    actual_height = height_decode

    src = bytearray(data[4:])
    dst = bytearray()
    src_pos = 0

    row_remaining = actual_width
    v8 = screen_width - actual_width  # 行跳转

    while actual_height > 0:
        count = row_remaining
        while count > 0:
            if src_pos >= len(src):
                return None, actual_width, actual_height

            value_byte = src[src_pos]
            src_pos += 1
            v12 = value_byte * 2

            if not (value_byte & 0x80):
                # bit 7 = 0: 原始数据
                count_1 = ((value_byte * 4) & 0xFF) >> 2
                if count_1 == 0:
                    count_1 = 1
                count_1 = count_1 + 1

                if value_byte & 0x40:
                    # bit 6 = 1: 跳过
                    dst.extend([0] * count_1)
                else:
                    # bit 6 = 0: 复制
                    if src_pos + count_1 > len(src):
                        return None, actual_width, actual_height
                    dst.extend(src[src_pos:src_pos + count_1])
                    src_pos += count_1
                count -= count_1
            else:
                # bit 7 = 1: RLE 命令
                count_1 = ((value_byte * 4) & 0xFF) >> 2
                if count_1 == 0:
                    count_1 = 1
                count_1 = count_1 + 1

                if value_byte & 0x40:
                    # bit 6 = 1: 单色填充
                    if src_pos >= len(src):
                        return None, actual_width, actual_height
                    fill_byte = src[src_pos]
                    src_pos += 1
                    dst.extend([fill_byte] * count_1)
                else:
                    # bit 6 = 0: 隔像素写入
                    if src_pos >= len(src):
                        return None, actual_width, actual_height
                    fill_byte = src[src_pos]
                    src_pos += 1
                    for i in range(count_1):
                        dst.append(fill_byte)
                        if len(dst) < screen_width:
                            dst.append(0)  # 透明像素
                count -= count_1

        # 行跳转
        dst.extend([0] * v8)
        actual_height -= 1

    return bytes(dst), actual_width, actual_height

def analyze_resource(data):
    """分析资源格式"""
    if len(data) < 4:
        return "TOO_SMALL"

    # 检查是否 LMI1 格式
    if data[:4] == b'LMI1':
        frame_count = struct.unpack('<H', data[4:6])[0]
        return f"LMI1_ANIMATION_frames={frame_count}"

    # 检查是否嵌套 DAT
    if data[:6] == b'LLLLLL':
        sub_count = struct.unpack('<I', data[6:10])[0] if len(data) >= 10 else 0
        return f"NESTED_DAT_subs={sub_count}"

    # 尝试 RLE 解码
    w = struct.unpack('<H', data[0:2])[0]
    h = struct.unpack('<H', data[2:4])[0]

    if w > 0 and h > 0 and w <= 320 and h <= 200:
        expected_size = 4 + (w * h * 2)  # 近似
        if len(data) >= expected_size // 2:
            return f"RLE_IMAGE {w}x{h}"

    return f"UNKNOWN w={w} h={h} size={len(data)}"

def main():
    with open(DAT_FILE, 'rb') as f:
        # 分析前20个资源
        print("=== FDOTHER.DAT 资源分析 ===\n")
        print(f"{'Index':<6} {'Size':<10} {'Format':<30} {'前16字节(hex)'}")
        print("-" * 80)

        for i in range(20):
            start, size = read_index(f, i)
            f.seek(start)
            header = f.read(16)

            fmt = analyze_resource(header)
            print(f"{i:<6} {size:<10} {fmt:<30} {header.hex()}")

if __name__ == '__main__':
    main()