#!/usr/bin/env python3
"""FDOTHER.DAT 子项 RLE 解码器

基于观察到的数据模式解码子项图像
"""

import struct
import os

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'
OUTPUT_DIR = '/home/yinming/fd2_hermes/extracted/fdother/'

def read_dat_file():
    with open(DAT_FILE, 'rb') as f:
        return f.read()

def get_resources(data):
    if data[:6] != b'LLLLLL':
        return []
    
    resources = []
    index = 0
    
    while True:
        offset = 4 * index + 6
        if offset + 8 > len(data):
            break
        
        start = struct.unpack_from('<I', data, offset)[0]
        end = struct.unpack_from('<I', data, offset + 4)[0]
        
        if start == 0 and end == 0:
            break
        
        if start >= end or start >= len(data) or end > len(data):
            break
        
        resources.append({'index': index, 'start': start, 'end': end, 'size': end - start})
        index += 1
    
    return resources

def parse_subindex(block):
    if len(block) < 12:
        return None
    
    count = struct.unpack_from('<H', block, 0)[0]
    count_copy = struct.unpack_from('<H', block, 2)[0]
    
    if count != count_copy or count < 2 or count > 500:
        return None
    
    offsets = []
    for i in range(count):
        pos = 8 + i * 4
        if pos + 4 <= len(block):
            offsets.append(struct.unpack_from('<I', block, pos)[0])
    
    return {'count': count, 'offsets': offsets}

def decode_rle_v1(data, width, height):
    """RLE 解码版本 1 - 基于 AFM 类似格式
    
    观察到的模式:
    - 数据从偏移 10 开始 (跳过头部)
    - 包含重复的命令模式
    
    尝试解码为逐行数据
    """
    if len(data) < 10:
        return None
    
    # 跳过头部 [width:2][height:2][pad:4][unk:2]
    compressed = data[10:]
    
    pixels = [0] * (width * height)
    pos = 0
    src = 0
    
    while src < len(compressed) and pos < len(pixels):
        cmd = compressed[src]
        src += 1
        
        # 尝试不同的解码方式
        
        # 方式 A: 直接像素值 (0x00-0x3F)
        if cmd < 0x40:
            pixels[pos] = cmd
            pos += 1
        
        # 方式 B: 带参数的命令
        elif cmd < 0x80:
            if src < len(compressed):
                val = compressed[src]
                src += 1
                count = (cmd & 0x3F) + 1
                for _ in range(count):
                    if pos < len(pixels):
                        pixels[pos] = val
                        pos += 1
        
        # 方式 C: 跳过/透明 (0x80-0xBF)
        elif cmd < 0xC0:
            count = (cmd & 0x3F) + 1
            pos += count  # 保持为 0 (透明)
        
        # 方式 D: 填充 (0xC0-0xFF)
        else:
            if src < len(compressed):
                val = compressed[src]
                src += 1
                count = (cmd & 0x3F) + 1
                for _ in range(count):
                    if pos < len(pixels):
                        pixels[pos] = val
                        pos += 1
    
    return bytes(pixels) if pos >= width * height // 2 else None

def decode_rle_v2(data, width, height):
    """RLE 解码版本 2 - 逐行解码
    
    每行独立编码，行结束标记
    """
    if len(data) < 10:
        return None
    
    compressed = data[10:]
    pixels = []
    src = 0
    
    for row in range(height):
        row_pixels = [0] * width
        col = 0
        row_start = src
        
        while col < width and src < len(compressed):
            b = compressed[src]
            src += 1
            
            # 尝试识别行结束
            if b == 0x00 and col > 0:
                # 可能是行结束
                break
            
            # 直接颜色
            if col < width:
                row_pixels[col] = b
                col += 1
        
        pixels.extend(row_pixels)
    
    return bytes(pixels) if len(pixels) >= width * height // 2 else None

def decode_rle_v3(data, width, height):
    """RLE 解码版本 3 - 基于观察到的实际模式
    
    模式分析:
    - c2 40 -> 可能是 (0xC2-0xC0=2) 次重复 0x40
    - c4 c4 c4 c4 -> 可能是多重命令
    
    解码规则:
    - 0x00-0x3F: 直接像素值
    - 0x40-0x7F: 下一个字节重复 (cmd - 0x40 + 1) 次
    - 0x80-0xBF: 跳过 (cmd - 0x80 + 1) 像素 (透明)
    - 0xC0-0xFF: 下一个字节重复 (cmd - 0xC0 + 1) 次
    """
    if len(data) < 10:
        return None
    
    # 读取额外的头部参数
    extra = struct.unpack_from('<H', data, 8)[0]  # 偏移 8 的值
    
    compressed = data[10:]
    pixels = [0] * (width * height)
    pos = 0
    src = 0
    
    while src < len(compressed) and pos < len(pixels):
        cmd = compressed[src]
        src += 1
        
        if cmd < 0x40:
            # 直接像素
            pixels[pos] = cmd
            pos += 1
        
        elif cmd < 0x80:
            # 重复: count = cmd - 0x40 + 1
            if src < len(compressed):
                val = compressed[src]
                src += 1
                count = cmd - 0x40 + 1
                for _ in range(count):
                    if pos < len(pixels):
                        pixels[pos] = val
                        pos += 1
        
        elif cmd < 0xC0:
            # 跳过: count = cmd - 0x80 + 1
            count = cmd - 0x80 + 1
            pos += count
        
        else:
            # 填充: count = cmd - 0xC0 + 1
            if src < len(compressed):
                val = compressed[src]
                src += 1
                count = cmd - 0xC0 + 1
                for _ in range(count):
                    if pos < len(pixels):
                        pixels[pos] = val
                        pos += 1
    
    return bytes(pixels)

def save_image(pixels, width, height, palette, output_path):
    """保存为 PNG 图像"""
    try:
        from PIL import Image
    except ImportError:
        print("需要安装 PIL: pip install Pillow")
        return False
    
    img = Image.new('RGB', (width, height))
    
    for y in range(height):
        for x in range(width):
            idx = y * width + x
            if idx < len(pixels):
                color_idx = pixels[idx]
                if color_idx < len(palette):
                    img.putpixel((x, y), palette[color_idx])
                else:
                    img.putpixel((x, y), (255, 0, 255))  # 品红表示越界
            else:
                img.putpixel((x, y), (0, 0, 0))
    
    img.save(output_path)
    return True

def load_palette(data, res_idx=0):
    """加载调色板"""
    resources = get_resources(data)
    
    # 调色板资源索引
    palette_indices = [0, 8, 57, 76, 99, 101, 102]
    
    if res_idx >= len(palette_indices):
        res_idx = 0
    
    pal_res = next((r for r in resources if r['index'] == palette_indices[res_idx]), None)
    if not pal_res:
        return [(i, i, i) for i in range(256)]  # 灰度
    
    pal_data = data[pal_res['start']:pal_res['end']]
    
    palette = []
    for i in range(256):
        if i * 3 + 3 <= len(pal_data):
            r = pal_data[i * 3] * 4  # DOS 6-bit -> 8-bit
            g = pal_data[i * 3 + 1] * 4
            b = pal_data[i * 3 + 2] * 4
            palette.append((min(255, r), min(255, g), min(255, b)))
        else:
            palette.append((0, 0, 0))
    
    return palette

def extract_and_render(data, res_idx, sub_idx, output_dir):
    """提取并渲染子项"""
    resources = get_resources(data)
    res = next((r for r in resources if r['index'] == res_idx), None)
    if not res:
        print(f"资源 {res_idx} 不存在")
        return
    
    block = data[res['start']:res['end']]
    subindex = parse_subindex(block)
    
    if not subindex or sub_idx >= len(subindex['offsets']):
        print(f"子项 {sub_idx} 不存在")
        return
    
    offset = subindex['offsets'][sub_idx]
    next_offset = subindex['offsets'][sub_idx + 1] if sub_idx + 1 < len(subindex['offsets']) else len(block)
    
    subblock = block[offset:next_offset]
    
    if len(subblock) < 10:
        print(f"子项数据太短: {len(subblock)}")
        return
    
    # 解析头部
    width = struct.unpack_from('<H', subblock, 0)[0]
    height = struct.unpack_from('<H', subblock, 2)[0]
    
    print(f"\n资源 {res_idx}, 子项 {sub_idx}:")
    print(f"  宽度: {width}, 高度: {height}")
    print(f"  数据大小: {len(subblock)} 字节")
    print(f"  预期像素: {width * height}")
    
    # 加载调色板
    palette = load_palette(data, 0)
    
    # 尝试多种解码方式
    os.makedirs(output_dir, exist_ok=True)
    
    # 解码 v3
    pixels_v3 = decode_rle_v3(subblock, width, height)
    
    # 保存 v3
    output_path_v3 = os.path.join(output_dir, f'res{res_idx}_sub{sub_idx}_v3.png')
    if save_image(pixels_v3, width, height, palette, output_path_v3):
        print(f"  保存 v3: {output_path_v3}")
    
    # 也保存原始数据作为参考
    raw_path = os.path.join(output_dir, f'res{res_idx}_sub{sub_idx}.raw')
    with open(raw_path, 'wb') as f:
        f.write(subblock)
    print(f"  原始数据: {raw_path}")
    
    return output_path_v3

def main():
    data = read_dat_file()
    
    print("=" * 70)
    print("FDOTHER.DAT 子项图像提取")
    print("=" * 70)
    
    # 提取几个测试图像
    test_items = [
        (18, 2),   # 9x105 精灵
        (18, 4),   # 另一个精灵
        (26, 1),   # 大型精灵
        (19, 2),   # 类似资源 18
        (44, 6),   # 横条图像
    ]
    
    for res_idx, sub_idx in test_items:
        extract_and_render(data, res_idx, sub_idx, OUTPUT_DIR)
    
    print(f"\n完成！输出目录: {OUTPUT_DIR}")

if __name__ == '__main__':
    main()
