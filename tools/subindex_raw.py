#!/usr/bin/env python3
"""FDOTHER.DAT 子索引格式原始数据分析

通过十六进制dump来理解实际的数据结构
"""

import struct

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

def hexdump(data, offset=0, length=128):
    """生成十六进制dump"""
    lines = []
    for i in range(0, min(length, len(data)), 16):
        hex_part = ' '.join(f'{b:02x}' for b in data[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        lines.append(f'{offset + i:08x}  {hex_part:<48}  |{ascii_part}|')
    return '\n'.join(lines)

def analyze_subindex_raw(data, res_idx):
    """分析资源的原始子索引数据"""
    data_full = read_dat_file()
    resources = get_resources(data_full)
    
    res = next((r for r in resources if r['index'] == res_idx), None)
    if not res:
        print(f"资源 {res_idx} 不存在")
        return
    
    block = data_full[res['start']:res['end']]
    
    print(f"\n{'='*70}")
    print(f"资源 {res_idx} 原始数据分析")
    print(f"{'='*70}")
    print(f"偏移: 0x{res['start']:06X}")
    print(f"大小: {res['size']} 字节")
    
    print(f"\n前 128 字节:")
    print(hexdump(block, res['start'], 128))
    
    # 尝试解析头部
    print(f"\n头部解析:")
    
    # 读取前几个WORD
    words = []
    for i in range(min(10, len(block) // 2)):
        w = struct.unpack_from('<H', block, i * 2)[0]
        words.append(w)
    
    print(f"前10个WORD: {words}")
    
    # 分析可能的格式
    
    # 格式A: [count:WORD][padding:WORD][offsets:DWORD...]
    count_a = words[0]
    if count_a > 1 and count_a < 500:
        print(f"\n假设格式A: count={count_a}, 后跟 DWORD 偏移")
        offsets_a = []
        for i in range(min(count_a, 10)):
            pos = 4 + i * 4  # 跳过 count 和 padding
            if pos + 4 <= len(block):
                d = struct.unpack_from('<I', block, pos)[0]
                offsets_a.append(d)
        print(f"偏移表: {offsets_a}")
    
    # 格式B: [count:WORD][offsets:WORD...]
    print(f"\n假设格式B: count={count_a}, 后跟 WORD 偏移")
    offsets_b = []
    for i in range(1, min(count_a + 1, 11)):
        if i * 2 <= len(block):
            w = struct.unpack_from('<H', block, i * 2)[0]
            offsets_b.append(w)
    print(f"偏移表: {offsets_b}")
    
    # 格式C: [count:WORD][padding:WORD][header_size:WORD][offsets...]
    print(f"\n假设格式C: 带头部")
    if len(block) >= 8:
        count_c = words[0]
        padding = words[1]
        header_size = words[2] if len(words) > 2 else 0
        print(f"count={count_c}, padding={padding}, header_size={header_size}")
    
    # 查找规律 - 检查偏移是否递增
    print(f"\n偏移规律分析:")
    
    # 检查 DWORD 偏移是否在合理范围内
    if count_a > 1 and count_a < 500:
        print(f"检查 DWORD 偏移是否指向块内:")
        for i in range(min(count_a, 5)):
            pos = 4 + i * 4
            if pos + 4 <= len(block):
                d = struct.unpack_from('<I', block, pos)[0]
                in_range = "有效" if d < res['size'] else "超出范围"
                print(f"  offset[{i}] = {d} (0x{d:04X}) - {in_range}")

def analyze_multiple_resources():
    """分析多个资源的子索引格式"""
    data = read_dat_file()
    resources = get_resources(data)
    
    # 分析几个典型资源
    for idx in [1, 18, 26, 44]:
        analyze_subindex_raw(data, idx)
    
    # 尝试找共同模式
    print(f"\n\n{'='*70}")
    print("模式分析")
    print(f"{'='*70}")
    
    # 收集所有子索引的头部
    headers = []
    for res in resources:
        block = data[res['start']:res['end']]
        if len(block) >= 8:
            w0 = struct.unpack_from('<H', block, 0)[0]
            w1 = struct.unpack_from('<H', block, 2)[0]
            w2 = struct.unpack_from('<H', block, 4)[0]
            w3 = struct.unpack_from('<H', block, 6)[0]
            
            # 检查是否像子索引 (第一个WORD是合理数量)
            if 2 <= w0 <= 500:
                headers.append({
                    'index': res['index'],
                    'size': res['size'],
                    'w0': w0,
                    'w1': w1,
                    'w2': w2,
                    'w3': w3
                })
    
    print(f"\n可能的子索引资源: {len(headers)}")
    print(f"\n头部WORD统计:")
    print(f"{'资源':>6} {'大小':>8} {'w0':>6} {'w1':>6} {'w2':>6} {'w3':>6}")
    print("-" * 50)
    for h in headers[:20]:
        print(f"{h['index']:>6} {h['size']:>8} {h['w0']:>6} {h['w1']:>6} {h['w2']:>6} {h['w3']:>6}")

if __name__ == '__main__':
    analyze_multiple_resources()
