#!/usr/bin/env python3
"""FDOTHER.DAT 子项图像批量提取和验证

提取多个子项图像，并生成 HTML 报告用于查看
"""

import struct
import os
import base64

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

def decode_rle_v3(data, width, height):
    """RLE 解码"""
    if len(data) < 10:
        return None
    
    compressed = data[10:]
    pixels = [0] * (width * height)
    pos = 0
    src = 0
    
    while src < len(compressed) and pos < len(pixels):
        cmd = compressed[src]
        src += 1
        
        if cmd < 0x40:
            pixels[pos] = cmd
            pos += 1
        elif cmd < 0x80:
            if src < len(compressed):
                val = compressed[src]
                src += 1
                count = cmd - 0x40 + 1
                for _ in range(count):
                    if pos < len(pixels):
                        pixels[pos] = val
                        pos += 1
        elif cmd < 0xC0:
            count = cmd - 0x80 + 1
            pos += count
        else:
            if src < len(compressed):
                val = compressed[src]
                src += 1
                count = cmd - 0xC0 + 1
                for _ in range(count):
                    if pos < len(pixels):
                        pixels[pos] = val
                        pos += 1
    
    return bytes(pixels)

def load_palette(data, res_idx=0):
    resources = get_resources(data)
    palette_indices = [0, 8, 57, 76, 99, 101, 102]
    
    if res_idx >= len(palette_indices):
        res_idx = 0
    
    pal_res = next((r for r in resources if r['index'] == palette_indices[res_idx]), None)
    if not pal_res:
        return [(i, i, i) for i in range(256)]
    
    pal_data = data[pal_res['start']:pal_res['end']]
    
    palette = []
    for i in range(256):
        if i * 3 + 3 <= len(pal_data):
            r = pal_data[i * 3] * 4
            g = pal_data[i * 3 + 1] * 4
            b = pal_data[i * 3 + 2] * 4
            palette.append((min(255, r), min(255, g), min(255, b)))
        else:
            palette.append((0, 0, 0))
    
    return palette

def save_png(pixels, width, height, palette, output_path):
    try:
        from PIL import Image
    except ImportError:
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
                    img.putpixel((x, y), (255, 0, 255))
            else:
                img.putpixel((x, y), (0, 0, 0))
    
    img.save(output_path)
    return True

def generate_html_report(images, output_path):
    """生成 HTML 报告"""
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>FDOTHER.DAT 子项图像提取报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #eee; }
        h1 { color: #4a9; }
        .image-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .image-item { background: #2a2a2a; padding: 15px; border-radius: 8px; }
        .image-item img { max-width: 100%; image-rendering: pixelated; border: 1px solid #444; }
        .image-item .info { margin-top: 10px; font-size: 12px; color: #aaa; }
        .image-item .title { font-weight: bold; color: #4a9; margin-bottom: 5px; }
    </style>
</head>
<body>
    <h1>FDOTHER.DAT 子项图像提取报告</h1>
    <p>共提取 {count} 个图像</p>
    <div class="image-grid">
'''.format(count=len(images))
    
    for img in images:
        # 读取图像并转为 base64
        try:
            with open(img['path'], 'rb') as f:
                img_data = base64.b64encode(f.read()).decode()
            
            html += f'''
        <div class="image-item">
            <div class="title">资源 {img['res_idx']} 子项 {img['sub_idx']}</div>
            <img src="data:image/png;base64,{img_data}" style="width: {max(img['width'] * 4, 100)}px;">
            <div class="info">
                尺寸: {img['width']}x{img['height']}<br>
                数据大小: {img['data_size']} 字节<br>
                压缩率: {img['data_size'] / (img['width'] * img['height']):.2%}
            </div>
        </div>
'''
        except Exception as e:
            html += f'''
        <div class="image-item">
            <div class="title">资源 {img['res_idx']} 子项 {img['sub_idx']}</div>
            <div style="color: red;">加载失败: {e}</div>
        </div>
'''
    
    html += '''
    </div>
</body>
</html>
'''
    
    with open(output_path, 'w') as f:
        f.write(html)

def main():
    data = read_dat_file()
    resources = get_resources(data)
    palette = load_palette(data, 0)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 提取所有子索引资源的子项
    images = []
    
    subindex_resources = [1, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 30, 32, 33, 34, 44]
    
    for res_idx in subindex_resources:
        res = next((r for r in resources if r['index'] == res_idx), None)
        if not res:
            continue
        
        block = data[res['start']:res['end']]
        subindex = parse_subindex(block)
        
        if not subindex:
            continue
        
        # 提取前几个子项
        for sub_idx in range(min(5, len(subindex['offsets']))):
            offset = subindex['offsets'][sub_idx]
            next_offset = subindex['offsets'][sub_idx + 1] if sub_idx + 1 < len(subindex['offsets']) else len(block)
            
            if offset >= len(block) or next_offset > len(block):
                continue
            
            subblock = block[offset:next_offset]
            
            if len(subblock) < 10:
                continue
            
            width = struct.unpack_from('<H', subblock, 0)[0]
            height = struct.unpack_from('<H', subblock, 2)[0]
            
            if width <= 0 or height <= 0 or width > 640 or height > 480:
                continue
            
            # 解码
            pixels = decode_rle_v3(subblock, width, height)
            if not pixels:
                continue
            
            # 保存
            filename = f'res{res_idx}_sub{sub_idx}.png'
            output_path = os.path.join(OUTPUT_DIR, filename)
            
            if save_png(pixels, width, height, palette, output_path):
                images.append({
                    'res_idx': res_idx,
                    'sub_idx': sub_idx,
                    'width': width,
                    'height': height,
                    'data_size': len(subblock),
                    'path': output_path
                })
                print(f"提取: 资源 {res_idx} 子项 {sub_idx} ({width}x{height})")
    
    # 生成报告
    report_path = os.path.join(OUTPUT_DIR, 'report.html')
    generate_html_report(images, report_path)
    print(f"\n报告已生成: {report_path}")
    print(f"共提取 {len(images)} 个图像")

if __name__ == '__main__':
    main()
