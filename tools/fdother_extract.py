#!/usr/bin/env python3
"""
FDOTHER.DAT 图像提取和转换工具

基于 FD2.EXE 反编译代码分析:
- sub_111BA: DAT文件加载函数
- sub_4E98D: RLE解压函数 (地址 0x4E98D)

RLE压缩格式:
============
头部: [width:2][height:2]
数据: 逐行压缩
  - 0x00-0x3F: 交错写入
  - 0x40-0x7F: RLE填充 (后跟1字节值)
  - 0x80-0xBF: 复制 (后跟n字节)
  - 0xC0-0xFF: 跳过 (保持原值)

使用方法:
=========
提取单个资源:
  python3 fdother_extract.py extract 5
  
导出PNG:
  python3 fdother_extract.py export 5 --output image_05.png
  
批量导出:
  python3 fdother_extract.py export-all
"""

import struct
import sys
import os

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'
OUTPUT_DIR = '/home/yinming/fd2_hermes/extracted/fdother/'

def read_dat():
    with open(DAT_FILE, 'rb') as f:
        return f.read()

def decode_fd2_rle(data):
    """FD2 RLE解码器 - 基于sub_4E98D"""
    if len(data) < 4:
        return bytes(), 0, 0
    
    count = struct.unpack('<H', data[0:2])[0]  # 宽度
    lines = struct.unpack('<H', data[2:4])[0]  # 高度
    
    if count == 0 or lines == 0 or count > 1000 or lines > 1000:
        return bytes(), 0, 0
    
    output = []
    src = 4
    
    for line in range(lines):
        line_output = [0] * count  # 初始化为0
        pos = 0
        remaining = count
        
        while remaining > 0 and src < len(data):
            value = data[src]
            src += 1
            count_1 = (value & 0x3F) + 1
            
            if value >= 0x80:
                if value >= 0xC0:  # 跳过
                    pos += count_1
                    remaining -= count_1
                else:  # 复制
                    for _ in range(count_1):
                        if pos < count and src < len(data):
                            line_output[pos] = data[src]
                            src += 1
                            pos += 1
                            remaining -= 1
            else:
                if value >= 0x40:  # RLE填充
                    if src < len(data):
                        fill = data[src]
                        src += 1
                        for _ in range(count_1):
                            if pos < count:
                                line_output[pos] = fill
                                pos += 1
                                remaining -= 1
                else:  # 交错
                    if src < len(data):
                        fill = data[src]
                        src += 1
                        for _ in range(count_1):
                            if pos < count:
                                line_output[pos] = fill
                                pos += 1
                                remaining -= 1
                            if pos < count:
                                pos += 1
                                remaining -= 1
        
        output.extend(line_output)
    
        return bytes(output[:count * lines]), count, lines

def decode_lmi1(data):
    """解码 LMI1 格式 (列存储动画)"""
    if len(data) < 8 or data[:4] != b'LMI1':
        return bytes(), 0, 0
    
    w = struct.unpack('<H', data[4:6])[0]
    h = struct.unpack('<H', data[6:8])[0]
    
    # 解析帧偏移表: [00 00][offset:2] 模式
    offsets = []
    i = 8
    while i < len(data) - 4:
        if data[i] == 0 and data[i+1] == 0:
            val = struct.unpack('<H', data[i+2:i+4])[0]
            if val > 0 and val < len(data):
                offsets.append(val)
                i += 4
            else:
                break
        else:
            break
    
    # 解码每帧 (每帧是一列)
    frames = []
    for frame_idx in range(min(len(offsets), w)):
        offset = offsets[frame_idx]
        frame_end = offsets[frame_idx + 1] if frame_idx + 1 < len(offsets) else len(data)
        frame_data = data[offset:frame_end]
        decoded = decode_rle(frame_data)
        # 取前h字节
        frames.append(decoded[:h] if len(decoded) >= h else decoded + bytes(h - len(decoded)))
    
    # 合成图像 (列优先转行优先)
    image = []
    for y in range(h):
        for x in range(w):
            if x < len(frames) and y < len(frames[x]):
                image.append(frames[x][y])
            else:
                image.append(0)
    
    return bytes(image), w, h


def get_resources(data):
    """获取所有有效资源"""
    if data[:6] != b'LLLLLL':
        return []
    
    index_count = struct.unpack('<I', data[6:10])[0]
    resources = []
    
    for i in range(index_count):
        offset = 10 + i * 8
        if offset + 8 > len(data):
            break
        start = struct.unpack('<I', data[offset:offset+4])[0]
        end = struct.unpack('<I', data[offset+4:offset+8])[0]
        
        if start > 0 and start < end and end <= len(data):
            resources.append({
                'index': i,
                'start': start,
                'end': end,
                'size': end - start
            })
    
    return resources

def load_palette(pal_file):
    """加载调色板文件"""
    with open(pal_file, 'rb') as f:
        pal_data = f.read()
    
    palette = []
    for i in range(256):
        if i * 3 + 3 <= len(pal_data):
            r = pal_data[i * 3] * 4  # DOS 6-bit -> 8-bit
            g = pal_data[i * 3 + 1] * 4
            b = pal_data[i * 3 + 2] * 4
            palette.append((r, g, b))
    
    return palette

def save_png(pixels, width, height, palette, output_path):
    """保存为PNG (需要PIL)"""
    try:
        from PIL import Image
    except ImportError:
        print("需要安装PIL: pip install Pillow")
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
                    img.putpixel((x, y), (255, 0, 255))  # 品红表示错误
            else:
                img.putpixel((x, y), (0, 0, 0))
    
    img.save(output_path)
    return True

def extract_resource(data, idx, output_raw=True):
    """提取单个资源"""
    resources = get_resources(data)
    
    for res in resources:
        if res['index'] == idx:
            res_data = data[res['start']:res['end']]
            
            if res['size'] == 768:
                # 调色板
                return {'type': 'palette', 'data': res_data}
            
            decoded, w, h = decode_fd2_rle(res_data)
            
            if w > 0 and h > 0:
                return {
                    'type': 'image',
                    'width': w,
                    'height': h,
                    'pixels': decoded,
                    'raw_data': res_data
                }
            else:
                return {'type': 'unknown', 'data': res_data}
    
    return None

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    data = read_dat()
    cmd = sys.argv[1]
    
    if cmd == 'extract' and len(sys.argv) >= 3:
        idx = int(sys.argv[2])
        result = extract_resource(data, idx)
        
        if result:
            if result['type'] == 'image':
                print(f"资源 {idx}: {result['width']}x{result['height']}")
                print(f"像素数: {len(result['pixels'])}")
                
                # 保存RAW
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                raw_path = os.path.join(OUTPUT_DIR, f'resource_{idx:03d}.raw')
                with open(raw_path, 'wb') as f:
                    f.write(result['pixels'])
                print(f"保存到: {raw_path}")
            elif result['type'] == 'palette':
                print(f"资源 {idx}: 调色板 (768字节)")
            else:
                print(f"资源 {idx}: 未知类型 ({len(result['data'])}字节)")
    
    elif cmd == 'export' and len(sys.argv) >= 3:
        idx = int(sys.argv[2])
        result = extract_resource(data, idx)
        
        if result and result['type'] == 'image':
            # 尝试加载调色板
            palette = [(i, i, i) for i in range(256)]  # 灰度默认
            
            # 查找同目录下的调色板
            for pal_idx in [28, 49, 50]:
                pal_file = os.path.join(OUTPUT_DIR, f'resource_{pal_idx:03d}.pal')
                if os.path.exists(pal_file):
                    palette = load_palette(pal_file)
                    print(f"使用调色板: {pal_file}")
                    break
            
            output_path = sys.argv[4] if len(sys.argv) >= 5 and sys.argv[3] == '--output' else \
                          os.path.join(OUTPUT_DIR, f'resource_{idx:03d}.png')
            
            if save_png(result['pixels'], result['width'], result['height'], palette, output_path):
                print(f"导出PNG: {output_path}")
    
    elif cmd == 'export-all':
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # 先提取调色板
        for pal_idx in [28, 49, 50]:
            result = extract_resource(data, pal_idx)
            if result and result['type'] == 'palette':
                pal_path = os.path.join(OUTPUT_DIR, f'resource_{pal_idx:03d}.pal')
                with open(pal_path, 'wb') as f:
                    f.write(result['data'])
                print(f"调色板 {pal_idx} 已保存")
        
        # 导出所有图像
        palette = load_palette(os.path.join(OUTPUT_DIR, 'resource_028.pal'))
        
        resources = get_resources(data)
        for res in resources:
            result = extract_resource(data, res['index'])
            if result and result['type'] == 'image':
                output_path = os.path.join(OUTPUT_DIR, f'resource_{res["index"]:03d}.png')
                if save_png(result['pixels'], result['width'], result['height'], palette, output_path):
                    print(f"[{res['index']:3d}] {result['width']}x{result['height']} -> {output_path}")
    
    else:
        print(f"未知命令或参数不足")
        print(__doc__)

if __name__ == '__main__':
    main()
