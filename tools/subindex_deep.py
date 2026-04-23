#!/usr/bin/env python3
"""FDOTHER.DAT 子索引格式深度分析

发现:
- 子索引格式: [count:WORD][offsets:WORD pairs...]
- 偏移是成对出现的: [offset_low:WORD][offset_high:WORD]
- 实际偏移 = offset_low (offset_high 似乎总是0)
"""

import struct
import sys

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_dat_file():
    with open(DAT_FILE, 'rb') as f:
        return f.read()

def get_resources(data):
    """获取所有有效资源"""
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
        
        resources.append({
            'index': index,
            'start': start,
            'end': end,
            'size': end - start
        })
        index += 1
    
    return resources

def parse_subindex_v2(block):
    """解析子索引 - 新格式发现
    
    格式:
    [count:WORD]
    [sub0_offset_low:WORD][sub0_offset_high:WORD]
    [sub1_offset_low:WORD][sub1_offset_high:WORD]
    ...
    
    offset_high 通常是 0，offset_low 是实际偏移
    """
    if len(block) < 4:
        return None
    
    count = struct.unpack_from('<H', block, 0)[0]
    
    if count < 2 or count > 500:
        return None
    
    # 读取偏移对
    offsets = []
    for i in range(count):
        pos = 2 + i * 4  # 每对 4 字节
        if pos + 4 > len(block):
            break
        
        low = struct.unpack_from('<H', block, pos)[0]
        high = struct.unpack_from('<H', block, pos + 2)[0]
        
        # 实际偏移 = low (high 通常是 0)
        offsets.append({
            'index': i,
            'offset_low': low,
            'offset_high': high,
            'actual_offset': low + (high << 16) if high else low
        })
    
    return {
        'count': count,
        'offsets': offsets
    }

def parse_image_header(data):
    """解析图像头部
    
    格式:
    [width:WORD][height:WORD]
    [unknown1:DWORD]
    [frame_offsets...]
    """
    if len(data) < 8:
        return None
    
    width = struct.unpack_from('<H', data, 0)[0]
    height = struct.unpack_from('<H', data, 2)[0]
    
    # 验证尺寸合理性
    if width == 0 or height == 0 or width > 640 or height > 480:
        return None
    
    return {
        'width': width,
        'height': height,
        'expected_size': width * height
    }

def analyze_resource_deep(data, res):
    """深度分析单个资源"""
    block = data[res['start']:res['end']]
    
    print(f"\n{'='*70}")
    print(f"资源 {res['index']} 深度分析")
    print(f"{'='*70}")
    print(f"大小: {res['size']:,} 字节")
    
    # 解析子索引
    subindex = parse_subindex_v2(block)
    if not subindex:
        print("无有效子索引")
        return
    
    print(f"\n子项数: {subindex['count']}")
    
    # 分析每个子项
    print(f"\n子项详情:")
    print(f"{'索引':>4} {'偏移':>6} {'大小':>6} {'格式':<15} {'信息'}")
    print("-" * 70)
    
    for i, off in enumerate(subindex['offsets'][:15]):  # 只显示前15个
        actual = off['actual_offset']
        
        # 计算子项大小
        next_off = subindex['offsets'][i + 1]['actual_offset'] if i + 1 < len(subindex['offsets']) else len(block)
        size = next_off - actual
        
        # 解析子项内容
        if actual < len(block) and size > 0:
            subblock = block[actual:actual + min(size, 64)]
            
            # 尝试识别格式
            format_type = "unknown"
            info = ""
            
            # 检查图像头
            img = parse_image_header(subblock)
            if img and img['expected_size'] <= size:
                format_type = "image"
                info = f"{img['width']}x{img['height']} ({img['expected_size']} bytes)"
            elif len(subblock) >= 4:
                # 检查是否是调色板
                if size == 768:
                    format_type = "palette"
                    info = "256 colors"
                else:
                    # 显示前几个字节
                    first_bytes = subblock[:8].hex()
                    info = f"hex: {first_bytes}"
            
            print(f"{i:>4} {actual:>6} {size:>6} {format_type:<15} {info}")

def analyze_subitem_images(data, res, output_dir=None):
    """分析子项中的图像数据"""
    block = data[res['start']:res['end']]
    
    subindex = parse_subindex_v2(block)
    if not subindex:
        return []
    
    images = []
    
    for i, off in enumerate(subindex['offsets']):
        actual = off['actual_offset']
        next_off = subindex['offsets'][i + 1]['actual_offset'] if i + 1 < len(subindex['offsets']) else len(block)
        size = next_off - actual
        
        if actual < len(block) and size > 8:
            subblock = block[actual:actual + size]
            
            # 尝试解析图像
            img = parse_image_header(subblock)
            if img and img['expected_size'] <= size:
                # 提取像素数据 (从偏移 8 开始，跳过 width/height 和未知字段)
                # 但需要找到实际数据起始位置
                
                # 查找数据开始位置 - 通常在帧偏移表之后
                # 暂时假设数据从固定偏移开始
                
                images.append({
                    'index': i,
                    'offset': actual,
                    'size': size,
                    'width': img['width'],
                    'height': img['height'],
                    'expected_pixels': img['expected_size']
                })
    
    return images

def main():
    data = read_dat_file()
    resources = get_resources(data)
    
    # 重点分析几个资源
    focus_resources = [1, 18, 19, 20, 26, 27, 44]
    
    for idx in focus_resources:
        res = next((r for r in resources if r['index'] == idx), None)
        if res:
            analyze_resource_deep(data, res)
    
    # 统计所有子索引资源中的图像
    print(f"\n\n{'='*70}")
    print("图像统计")
    print(f"{'='*70}")
    
    total_images = 0
    image_sizes = []
    
    for res in resources:
        images = analyze_subitem_images(data, res)
        if images:
            total_images += len(images)
            for img in images:
                image_sizes.append(f"{img['width']}x{img['height']}")
            
            if len(images) > 0:
                print(f"\n资源 {res['index']}: {len(images)} 个图像")
                for img in images[:5]:
                    print(f"  [{img['index']}] {img['width']}x{img['height']} @ offset {img['offset']}")
    
    print(f"\n总图像数: {total_images}")
    
    # 统计尺寸分布
    from collections import Counter
    size_dist = Counter(image_sizes)
    print(f"\n尺寸分布:")
    for size, count in size_dist.most_common(10):
        print(f"  {size}: {count} 个")

if __name__ == '__main__':
    main()
