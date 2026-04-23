#!/usr/bin/env python3
"""FDOTHER.DAT 子项数据格式深度分析

分析子项数据的真实格式，不只是简单的 width/height 头
"""

import struct
import os

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

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

def parse_subindex(block):
    """解析子索引"""
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
            offset = struct.unpack_from('<I', block, pos)[0]
            offsets.append(offset)
    
    return {'count': count, 'offsets': offsets}

def hexdump(data, length=64):
    """简短十六进制dump"""
    lines = []
    for i in range(0, min(length, len(data)), 16):
        hex_part = ' '.join(f'{b:02x}' for b in data[i:i+16])
        lines.append(f"  {i:04x}: {hex_part}")
    return '\n'.join(lines)

def analyze_subitem_format(subblock, res_idx, sub_idx):
    """深入分析子项格式"""
    print(f"\n{'='*70}")
    print(f"子项格式分析: 资源 {res_idx}, 子项 {sub_idx}")
    print(f"{'='*70}")
    print(f"大小: {len(subblock)} 字节")
    print(f"\n十六进制:")
    print(hexdump(subblock, 128))
    
    # 尝试多种解析方式
    
    # 方式1: 图像头 [width:WORD][height:WORD][unknown:DWORD][frames...]
    if len(subblock) >= 8:
        w = struct.unpack_from('<H', subblock, 0)[0]
        h = struct.unpack_from('<H', subblock, 2)[0]
        d1 = struct.unpack_from('<H', subblock, 4)[0]
        d2 = struct.unpack_from('<H', subblock, 6)[0]
        
        print(f"\n解析方式1 (图像头):")
        print(f"  width={w}, height={h}, data1={d1}, data2={d2}")
        
        if 1 <= w <= 640 and 1 <= h <= 480:
            expected = w * h
            print(f"  预期像素数: {expected}")
            print(f"  实际数据量: {len(subblock) - 8}")
            
            if expected == len(subblock) - 8:
                print(f"  => 可能是 RAW 像素数据")
            elif len(subblock) - 8 < expected:
                print(f"  => 可能是压缩数据 (RLE)")
    
    # 方式2: 精灵/图标头 [width:WORD][height:WORD][hot_x:WORD][hot_y:WORD][data...]
    if len(subblock) >= 8:
        w = struct.unpack_from('<H', subblock, 0)[0]
        h = struct.unpack_from('<H', subblock, 2)[0]
        hx = struct.unpack_from('<H', subblock, 4)[0]
        hy = struct.unpack_from('<H', subblock, 6)[0]
        
        print(f"\n解析方式2 (精灵头):")
        print(f"  width={w}, height={h}, hot_x={hx}, hot_y={hy}")
    
    # 方式3: RLE压缩 [width:WORD][height:WORD][compressed_data...]
    if len(subblock) >= 4:
        w = struct.unpack_from('<H', subblock, 0)[0]
        h = struct.unpack_from('<H', subblock, 2)[0]
        
        print(f"\n解析方式3 (RLE压缩):")
        print(f"  width={w}, height={h}")
        
        # 检查数据是否像RLE
        data_start = 4
        remaining = subblock[data_start:]
        
        # RLE特征: 大量重复字节或特定模式
        unique_bytes = len(set(remaining[:64]))
        print(f"  前64字节唯一值: {unique_bytes}")
        
        if unique_bytes < 16:
            print(f"  => 可能是RLE压缩 (低熵)")
    
    # 方式4: 帧动画 [frame_count:WORD][frame_offsets...]
    if len(subblock) >= 4:
        fc = struct.unpack_from('<H', subblock, 0)[0]
        
        print(f"\n解析方式4 (帧动画):")
        print(f"  可能的帧数: {fc}")
        
        if 2 <= fc <= 100:
            # 尝试读取帧偏移
            frames = []
            for i in range(fc):
                pos = 2 + i * 2
                if pos + 2 <= len(subblock):
                    foff = struct.unpack_from('<H', subblock, pos)[0]
                    if foff < len(subblock):
                        frames.append(foff)
            
            if len(frames) > 1:
                print(f"  帧偏移: {frames[:10]}")
    
    # 方式5: 直接索引像素数据 (无头)
    # 检查数据分布
    if len(subblock) >= 64:
        byte_dist = {}
        for b in subblock[:256]:
            byte_dist[b] = byte_dist.get(b, 0) + 1
        
        top_bytes = sorted(byte_dist.items(), key=lambda x: -x[1])[:5]
        print(f"\n数据分布分析:")
        print(f"  最常见字节: {top_bytes}")
        
        # 如果 0 是最常见的，可能是有效的索引像素数据
        if top_bytes[0][0] == 0:
            print(f"  => 可能是索引像素数据 (背景色占多数)")

def main():
    data = read_dat_file()
    resources = get_resources(data)
    
    # 分析几个代表性的子项
    focus_items = [
        (18, 2),   # 资源 18 的子项 2
        (18, 4),   # 资源 18 的子项 4
        (26, 1),   # 资源 26 的子项 1
        (44, 6),   # 资源 44 的子项 6 (图像)
        (19, 2),   # 资源 19 的子项 2
    ]
    
    for res_idx, sub_idx in focus_items:
        res = next((r for r in resources if r['index'] == res_idx), None)
        if not res:
            continue
        
        block = data[res['start']:res['end']]
        subindex = parse_subindex(block)
        
        if not subindex or sub_idx >= len(subindex['offsets']):
            continue
        
        offset = subindex['offsets'][sub_idx]
        next_offset = subindex['offsets'][sub_idx + 1] if sub_idx + 1 < len(subindex['offsets']) else len(block)
        
        subblock = block[offset:next_offset]
        analyze_subitem_format(subblock, res_idx, sub_idx)

if __name__ == '__main__':
    main()
