#!/usr/bin/env python3
"""FDOTHER.DAT 子索引正确解析器

发现的格式:
[count:WORD][count_copy:WORD][padding:WORD][padding:WORD][offsets:DWORD...]

偏移是相对于子索引数据块的起始位置
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
        
        resources.append({
            'index': index,
            'start': start,
            'end': end,
            'size': end - start
        })
        index += 1
    
    return resources

def parse_subindex_correct(block):
    """正确解析子索引格式
    
    格式:
    [count:WORD]       @ 0
    [count_copy:WORD]  @ 2  (应该等于 count)
    [padding:WORD]     @ 4  (通常是 0)
    [padding:WORD]     @ 6  (通常是 0)
    [offsets:DWORD...] @ 8+
    """
    if len(block) < 12:
        return None
    
    count = struct.unpack_from('<H', block, 0)[0]
    count_copy = struct.unpack_from('<H', block, 2)[0]
    padding1 = struct.unpack_from('<H', block, 4)[0]
    padding2 = struct.unpack_from('<H', block, 6)[0]
    
    # 验证格式
    if count != count_copy:
        return None
    
    if count < 2 or count > 500:
        return None
    
    # 读取偏移表
    offsets = []
    header_size = 8  # 头部 8 字节
    
    for i in range(count):
        pos = header_size + i * 4
        if pos + 4 > len(block):
            break
        
        offset = struct.unpack_from('<I', block, pos)[0]
        offsets.append(offset)
    
    return {
        'count': count,
        'padding': (padding1, padding2),
        'offsets': offsets,
        'header_size': header_size
    }

def analyze_subitems(data, res):
    """分析资源的子项"""
    block = data[res['start']:res['end']]
    
    subindex = parse_subindex_correct(block)
    if not subindex:
        return None
    
    subitems = []
    
    for i in range(len(subindex['offsets'])):
        offset = subindex['offsets'][i]
        
        # 计算子项大小
        if i + 1 < len(subindex['offsets']):
            next_offset = subindex['offsets'][i + 1]
        else:
            next_offset = len(block)
        
        size = next_offset - offset
        
        if offset < len(block) and size > 0:
            subblock = block[offset:offset + min(size, 256)]
            
            subitem = {
                'index': i,
                'offset': offset,
                'size': size,
                'data_preview': subblock[:32].hex() if len(subblock) >= 32 else subblock.hex()
            }
            
            # 尝试识别类型
            if size == 768:
                subitem['type'] = 'palette'
            elif size >= 8:
                # 检查图像头
                w = struct.unpack_from('<H', subblock, 0)[0]
                h = struct.unpack_from('<H', subblock, 2)[0]
                
                if 1 <= w <= 640 and 1 <= h <= 480:
                    expected = w * h
                    if expected <= size:
                        subitem['type'] = 'image'
                        subitem['width'] = w
                        subitem['height'] = h
                        subitem['expected_size'] = expected
            
            if 'type' not in subitem:
                subitem['type'] = 'unknown'
            
            subitems.append(subitem)
    
    return {
        'resource_index': res['index'],
        'resource_size': res['size'],
        'subindex': subindex,
        'subitems': subitems
    }

def extract_subitem(data, res_idx, subitem_idx):
    """提取单个子项"""
    data_full = read_dat_file()
    resources = get_resources(data_full)
    
    res = next((r for r in resources if r['index'] == res_idx), None)
    if not res:
        return None
    
    result = analyze_subitems(data_full, res)
    if not result or subitem_idx >= len(result['subitems']):
        return None
    
    subitem = result['subitems'][subitem_idx]
    block = data_full[res['start']:res['end']]
    
    # 提取数据
    subblock = block[subitem['offset']:subitem['offset'] + subitem['size']]
    
    return {
        'info': subitem,
        'data': subblock
    }

def main():
    data = read_dat_file()
    resources = get_resources(data)
    
    print("=" * 70)
    print("FDOTHER.DAT 子索引完整分析")
    print("=" * 70)
    
    # 统计
    total_subindexed = 0
    total_subitems = 0
    image_count = 0
    palette_count = 0
    
    all_images = []
    
    for res in resources:
        result = analyze_subitems(data, res)
        if result:
            total_subindexed += 1
            total_subitems += len(result['subitems'])
            
            for si in result['subitems']:
                if si['type'] == 'image':
                    image_count += 1
                    all_images.append({
                        'resource': res['index'],
                        'subitem': si['index'],
                        'width': si.get('width', 0),
                        'height': si.get('height', 0),
                        'size': si['size']
                    })
                elif si['type'] == 'palette':
                    palette_count += 1
    
    print(f"\n统计:")
    print(f"  有子索引的资源: {total_subindexed}")
    print(f"  子项总数: {total_subitems}")
    print(f"  图像子项: {image_count}")
    print(f"  调色板子项: {palette_count}")
    
    # 显示图像列表
    if all_images:
        print(f"\n图像列表 (前30个):")
        print(f"{'资源':>6} {'子项':>6} {'尺寸':>12} {'大小':>8}")
        print("-" * 40)
        for img in all_images[:30]:
            print(f"{img['resource']:>6} {img['subitem']:>6} {img['width']}x{img['height']:>8} {img['size']:>8}")
    
    # 详细分析几个资源
    print(f"\n" + "=" * 70)
    print("详细分析")
    print("=" * 70)
    
    for res_idx in [18, 26, 44]:
        res = next((r for r in resources if r['index'] == res_idx), None)
        if res:
            result = analyze_subitems(data, res)
            if result:
                print(f"\n--- 资源 {res_idx} ---")
                print(f"子项数: {len(result['subitems'])}")
                
                images = [si for si in result['subitems'] if si['type'] == 'image']
                if images:
                    print(f"包含图像: {len(images)}")
                    for img in images[:5]:
                        print(f"  [{img['index']}] {img['width']}x{img['height']} @ offset {img['offset']}")
    
    # 导出示例
    print(f"\n" + "=" * 70)
    print("导出示例图像")
    print("=" * 70)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 导出资源 18 的第一个图像子项
    extracted = extract_subitem(data, 18, 2)  # 子项 2 是第一个图像
    if extracted and extracted['info']['type'] == 'image':
        print(f"\n提取: 资源 18, 子项 2")
        print(f"  尺寸: {extracted['info']['width']}x{extracted['info']['height']}")
        
        # 保存原始数据
        raw_path = os.path.join(OUTPUT_DIR, 'res18_sub2.raw')
        with open(raw_path, 'wb') as f:
            f.write(extracted['data'])
        print(f"  保存到: {raw_path}")

if __name__ == '__main__':
    main()
