#!/usr/bin/env python3
"""
FDOTHER.DAT 解码器 v2.0
基于逆向工程 sub_4E98D 函数实现
修复了运算符优先级bug: (((4*value)&0xFF)>>2)+1

使用方法:
    python decode_fdother.py [索引号]
    
示例:
    python decode_fdother.py          # 解码所有资源
    python decode_fdother.py 9        # 解码索引9
    python decode_fdother.py 9 10 11  # 解码多个索引
"""
import struct
import sys
import os

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'
OUTPUT_DIR = '/home/yinming/fd2_hermes/decoded_hermes'

def decode_fdother_rle(src_data, width, height, value_1=-1):
    """
    RLE 解码器 - 基于 sub_4E98D 反编译代码
    
    每行处理:
    - bit7=1, bit6=1: 跳转模式 (dst前移)
    - bit7=1, bit6=0: 复制模式 (从src复制)
    - bit7=0, bit6=0: 填充模式 (用下一字节填充)
    - bit7=0, bit6=1: 继续外层循环
    
    count_1 = (((4*value)&0xFF)>>2) + 1 = value + 1
    """
    src = list(src_data)
    src_idx = 0
    total_pixels = width * height
    dst = bytearray(total_pixels)
    dst_idx = 0
    
    for row in range(height):
        count = width
        
        # Phase 1: bit7=1
        while count > 0:
            while count > 0:
                if src_idx >= len(src):
                    return bytes(dst[:dst_idx])
                value = src[src_idx]
                src_idx += 1
                v12 = value * 2
                if (value & 0x80) == 0:
                    break
                count_1 = (((4 * value) & 0xFF) >> 2) + 1
                if (v12 & 0x80) != 0:
                    dst_idx += count_1
                    count -= count_1
                    if count == 0:
                        break
                else:
                    count -= count_1
                    for i in range(count_1):
                        if src_idx < len(src) and dst_idx < total_pixels:
                            dst[dst_idx] = src[src_idx]
                            src_idx += 1
                            dst_idx += 1
                    if count == 0:
                        break
            # Phase 2: bit7=0
            while count > 0:
                if src_idx >= len(src):
                    return bytes(dst[:dst_idx])
                value = src[src_idx]
                src_idx += 1
                v12 = value * 2
                if (value & 0x80) == 0:
                    break
                count_1 = (((4 * value) & 0xFF) >> 2) + 1
                if (v12 & 0x80) == 0:
                    count -= count_1
                    fill_val = src[src_idx] if src_idx < len(src) else 0
                    src_idx += 1
                    for i in range(count_1):
                        if dst_idx < total_pixels:
                            dst[dst_idx] = fill_val
                            dst_idx += 1
                    if count == 0:
                        break
            # Phase 3: 两像素填充
            while count > 0:
                if src_idx >= len(src):
                    return bytes(dst[:dst_idx])
                value = src[src_idx]
                src_idx += 1
                v12 = value * 2
                if (value & 0x80) == 0:
                    break
                count_1 = (((4 * value) & 0xFF) >> 2) + 1
                if (v12 & 0x80) != 0:
                    count = count - count_1 - count_1
                    fill_val = src[src_idx] if src_idx < len(src) else 0
                    src_idx += 1
                    for i in range(count_1 * 2):
                        if dst_idx < total_pixels:
                            dst[dst_idx] = fill_val
                            dst_idx += 1
                    if count <= 0:
                        break
                else:
                    dst_idx += count_1
                    count -= count_1
                    if count == 0:
                        break
    
    return bytes(dst[:dst_idx])


def decode_index(data, idx):
    """解码指定索引"""
    off = 6 + idx * 8
    if off + 8 > len(data):
        return None, 0, 0, "索引超出范围"
    
    start = struct.unpack('<I', data[off:off+4])[0]
    end = struct.unpack('<I', data[off+4:off+8])[0]
    
    if start >= len(data) or end > len(data) or start >= end:
        return None, 0, 0, "无效范围"
    
    res_data = data[start:end]
    
    if len(res_data) < 4:
        return None, 0, 0, "数据太短"
    
    w = struct.unpack('<H', res_data[0:2])[0]
    h = struct.unpack('<H', res_data[2:4])[0]
    
    # 检查特殊类型
    if res_data[:6] == b'LLLLLL':
        return None, w, h, "LLLLLL类型(需要特殊处理)"
    
    if res_data[:4] == b'LMI1':
        return None, w, h, "LMI1类型(需要特殊处理)"
    
    expected = w * h
    if w == 0 or h == 0 or expected > 1000000:
        return None, w, h, f"尺寸异常({w}x{h})"
    
    try:
        encoded = res_data[4:]
        decoded = decode_fdother_rle(encoded, w, h, -1)
        if len(decoded) == expected:
            return decoded, w, h, "成功"
        else:
            return None, w, h, f"长度不匹配({len(decoded)}/{expected})"
    except Exception as e:
        return None, w, h, f"异常:{e}"


def export_all():
    """导出所有可解码资源"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(DAT_FILE, 'rb') as f:
        data = f.read()
    
    success = []
    failed = []
    
    for idx in range(52):
        decoded, w, h, status = decode_index(data, idx)
        
        if decoded:
            pgm = f"P5\n{w} {h}\n255\n".encode() + decoded
            path = f"{OUTPUT_DIR}/idx_{idx:02d}.pgm"
            with open(path, 'wb') as f:
                f.write(pgm)
            success.append(idx)
            print(f"索引{idx:2d}: {w}x{h} ✓")
        else:
            failed.append((idx, status))
            print(f"索引{idx:2d}: {status}")
    
    print(f"\n成功: {len(success)}, 失败: {len(failed)}")
    return success, failed


def export_single(idx):
    """导出单个索引"""
    with open(DAT_FILE, 'rb') as f:
        data = f.read()
    
    decoded, w, h, status = decode_index(data, idx)
    
    if decoded:
        pgm = f"P5\n{w} {h}\n255\n".encode() + decoded
        path = f"{OUTPUT_DIR}/idx_{idx:02d}.pgm"
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(path, 'wb') as f:
            f.write(pgm)
        print(f"索引{idx}: {w}x{h} -> {path}")
    else:
        print(f"索引{idx}: {status}")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            try:
                idx = int(arg)
                export_single(idx)
            except ValueError:
                print(f"无效参数: {arg}")
    else:
        export_all()