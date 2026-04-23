#!/usr/bin/env python3
"""FDOTHER.DAT 子索引结构深入分析

分析子索引的格式和内容
"""

import struct
import sys
import os

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

def analyze_subindex_format(data, res):
    """深入分析单个资源的子索引格式"""
    block = data[res['start']:res['end']]
    
    if len(block) < 4:
        return None
    
    result = {
        'index': res['index'],
        'size': res['size'],
        'format': 'unknown'
    }
    
    # 尝试不同的子索引格式
    
    # 格式1: WORD count + DWORD offsets[]
    first_word = struct.unpack_from('<H', block, 0)[0]
    if first_word > 1 and first_word < 500:
        # 验证偏移是否合理
        valid = True
        offsets = []
        for i in range(first_word):
            off = 2 + i * 4
            if off + 4 <= len(block):
                val = struct.unpack_from('<I', block, off)[0]
                offsets.append(val)
                # 偏移应该在块内
                if val > len(block):
                    valid = False
            else:
                valid = False
                break
        
        if valid and len(offsets) > 1:
            result['format'] = 'word_count_dword_offsets'
            result['sub_count'] = first_word
            result['offsets'] = offsets[:20]  # 只保留前20个
            result['sub_sizes'] = []
            
            # 计算子项大小
            for i in range(min(len(offsets) - 1, 20)):
                size = offsets[i + 1] - offsets[i]
                result['sub_sizes'].append(size)
    
    # 格式2: WORD count + WORD offsets[]
    if result['format'] == 'unknown':
        if first_word > 1 and first_word < 500:
            valid = True
            offsets = []
            for i in range(first_word):
                off = 2 + i * 2
                if off + 2 <= len(block):
                    val = struct.unpack_from('<H', block, off)[0]
                    offsets.append(val)
                    if val > len(block):
                        valid = False
                else:
                    valid = False
                    break
            
            if valid and len(offsets) > 1:
                result['format'] = 'word_count_word_offsets'
                result['sub_count'] = first_word
                result['offsets'] = offsets[:20]
    
    # 格式3: 直接数据 (无子索引)
    if result['format'] == 'unknown':
        # 检查是否是调色板
        if res['size'] == 768:
            result['format'] = 'palette'
        # 检查是否是 RLE 压缩图像
        elif first_word < 1000:
            # 可能是 width
            second_word = struct.unpack_from('<H', block, 2)[0]
            if second_word > 0 and second_word < 1000:
                result['format'] = 'possible_rle_image'
                result['possible_width'] = first_word
                result['possible_height'] = second_word
    
    return result

def analyze_subitem_content(data, res, subindex_info):
    """分析子项的内容"""
    block = data[res['start']:res['end']]
    
    if subindex_info['format'] not in ['word_count_dword_offsets', 'word_count_word_offsets']:
        return subindex_info
    
    offsets = subindex_info.get('offsets', [])
    if len(offsets) < 2:
        return subindex_info
    
    subitems = []
    
    for i in range(min(len(offsets) - 1, 10)):
        start = offsets[i]
        end = offsets[i + 1] if i + 1 < len(offsets) else len(block)
        
        if start >= end or start >= len(block):
            continue
        
        subblock = block[start:end]
        
        item = {
            'index': i,
            'offset': start,
            'size': end - start,
            'first_bytes': subblock[:16].hex() if len(subblock) >= 16 else subblock.hex()
        }
        
        # 尝试识别子项类型
        if len(subblock) >= 4:
            first_dword = struct.unpack_from('<I', subblock, 0)[0]
            
            # 检查是否是另一个子索引
            if first_dword > 1 and first_dword < 100 and first_dword * 4 < len(subblock):
                item['possible_subsub_count'] = first_dword
            
            # 检查是否是图像数据 (width, height)
            w = struct.unpack_from('<H', subblock, 0)[0]
            h = struct.unpack_from('<H', subblock, 2)[0]
            if w > 0 and w < 500 and h > 0 and h < 500:
                expected_size = w * h
                # 允许一些误差 (可能是压缩数据)
                if abs(item['size'] - expected_size) < expected_size * 2:
                    item['possible_image'] = f"{w}x{h}"
        
        subitems.append(item)
    
    subindex_info['subitems'] = subitems
    return subindex_info

def main():
    data = read_dat_file()
    resources = get_resources(data)
    
    print("=" * 70)
    print("FDOTHER.DAT 子索引结构分析")
    print("=" * 70)
    print(f"\n文件大小: {len(data):,} 字节")
    print(f"有效资源: {len(resources)} 个")
    
    # 找出有子索引的资源
    print("\n" + "=" * 70)
    print("子索引资源分析")
    print("=" * 70)
    
    subindexed = []
    
    for res in resources:
        info = analyze_subindex_format(data, res)
        if info and info['format'] in ['word_count_dword_offsets', 'word_count_word_offsets']:
            subindexed.append(info)
            
            print(f"\n--- 资源 {res['index']} ---")
            print(f"大小: {res['size']:,} 字节")
            print(f"格式: {info['format']}")
            print(f"子项数: {info.get('sub_count', 'N/A')}")
            
            if 'offsets' in info:
                print(f"偏移表 (前10): {info['offsets'][:10]}")
            
            if 'sub_sizes' in info and info['sub_sizes']:
                print(f"子项大小 (前10): {info['sub_sizes'][:10]}")
                
                # 统计子项大小分布
                sizes = info['sub_sizes']
                if sizes:
                    avg = sum(sizes) / len(sizes)
                    print(f"子项大小: 平均={avg:.0f}, 最小={min(sizes)}, 最大={max(sizes)}")
    
    # 深入分析前几个子索引资源
    print("\n" + "=" * 70)
    print("子项内容分析 (前5个子索引资源)")
    print("=" * 70)
    
    for info in subindexed[:5]:
        res = next((r for r in resources if r['index'] == info['index']), None)
        if res:
            info = analyze_subitem_content(data, res, info)
            
            print(f"\n--- 资源 {res['index']} 子项 ---")
            if 'subitems' in info:
                for item in info['subitems'][:5]:
                    print(f"  [{item['index']}] offset={item['offset']}, size={item['size']}")
                    print(f"       first bytes: {item['first_bytes']}")
                    if 'possible_image' in item:
                        print(f"       可能是图像: {item['possible_image']}")
                    if 'possible_subsub_count' in item:
                        print(f"       可能是嵌套子索引: count={item['possible_subsub_count']}")
    
    # 统计
    print("\n" + "=" * 70)
    print("统计信息")
    print("=" * 70)
    print(f"有子索引的资源: {len(subindexed)} 个")
    
    if subindexed:
        total_subitems = sum(s.get('sub_count', 0) for s in subindexed)
        print(f"子项总数: {total_subitems}")
        
        # 找出常见的子项大小
        all_sizes = []
        for s in subindexed:
            all_sizes.extend(s.get('sub_sizes', []))
        
        if all_sizes:
            from collections import Counter
            size_counts = Counter(all_sizes)
            print(f"\n常见子项大小:")
            for size, count in size_counts.most_common(10):
                print(f"  {size:,} 字节: {count} 次")

if __name__ == '__main__':
    main()
