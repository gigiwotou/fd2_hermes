#!/usr/bin/env python3
"""FDOTHER.DAT 子项数据逐字节分析

通过跟踪解码过程，找出真正的 RLE 格式
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

def trace_decode(subblock, res_idx, sub_idx):
    """逐字节跟踪解码过程"""
    if len(subblock) < 10:
        return
    
    width = struct.unpack_from('<H', subblock, 0)[0]
    height = struct.unpack_from('<H', subblock, 2)[0]
    pad1 = struct.unpack_from('<I', subblock, 4)[0]
    unk1 = struct.unpack_from('<H', subblock, 8)[0]
    
    print(f"\n{'='*70}")
    print(f"子项解码跟踪: 资源 {res_idx}, 子项 {sub_idx}")
    print(f"{'='*70}")
    print(f"头部: width={width}, height={height}, pad={pad1}, unk={unk1}")
    print(f"数据大小: {len(subblock)} 字节")
    print(f"预期像素: {width * height}")
    
    # 显示全部原始数据
    print(f"\n完整数据 (hex):")
    for i in range(0, len(subblock), 32):
        hex_part = ' '.join(f'{b:02x}' for b in subblock[i:i+32])
        print(f"  {i:04x}: {hex_part}")
    
    # 尝试理解数据结构
    # 关键观察: 子项很小但描述的图像很大
    # 例如: 9x105=945 像素, 但数据只有 143 字节
    # 数据中有大量 0x40, 0x80, 0xC0, 0xC2 等高位字节
    
    # 新假设: 数据不是逐像素的, 而是逐列或某种压缩格式
    # 让我分析具体数据模式
    
    print(f"\n逐字节命令分析:")
    
    data_start = 10  # 跳过头部
    src = data_start
    
    cmd_count = 0
    while src < len(subblock) and cmd_count < 50:
        b = subblock[src]
        
        # 高 2 位决定命令类型
        hi = b & 0xC0
        lo = b & 0x3F
        
        if hi == 0x00:  # 0x00-0x3F
            print(f"  [{src:04x}] {b:02x} -> 直接像素: {b}")
            src += 1
        elif hi == 0x40:  # 0x40-0x7F
            if src + 1 < len(subblock):
                val = subblock[src + 1]
                count = lo + 1
                print(f"  [{src:04x}] {b:02x} {val:02x} -> 重复 {count} 次: 颜色 {val}")
                src += 2
            else:
                print(f"  [{src:04x}] {b:02x} -> 数据截断")
                break
        elif hi == 0x80:  # 0x80-0xBF
            count = lo + 1
            print(f"  [{src:04x}] {b:02x} -> 跳过 {count} 像素 (透明)")
            src += 1
        else:  # 0xC0-0xFF
            if src + 1 < len(subblock):
                val = subblock[src + 1]
                count = lo + 1
                print(f"  [{src:04x}] {b:02x} {val:02x} -> 填充 {count} 次: 颜色 {val}")
                src += 2
            else:
                print(f"  [{src:04x}] {b:02x} -> 数据截断")
                break
        
        cmd_count += 1
    
    # 统计: 计算总像素数
    print(f"\n像素计数:")
    src = data_start
    total_pixels = 0
    while src < len(subblock):
        b = subblock[src]
        hi = b & 0xC0
        lo = b & 0x3F
        
        if hi == 0x00:
            total_pixels += 1
            src += 1
        elif hi == 0x40:
            total_pixels += lo + 1
            src += 2
        elif hi == 0x80:
            total_pixels += lo + 1
            src += 1
        else:
            total_pixels += lo + 1
            src += 2
    
    print(f"  预期: {width * height}")
    print(f"  计算: {total_pixels}")
    print(f"  匹配: {'是' if total_pixels == width * height else '否'}")

def main():
    data = read_dat_file()
    resources = get_resources(data)
    
    # 选择几个典型子项进行详细分析
    # 资源 18: 小型精灵 (9x105)
    res = next((r for r in resources if r['index'] == 18), None)
    if res:
        block = data[res['start']:res['end']]
        subindex = parse_subindex(block)
        if subindex:
            offset = subindex['offsets'][2]  # 子项 2
            next_offset = subindex['offsets'][3]
            subblock = block[offset:next_offset]
            trace_decode(subblock, 18, 2)
    
    # 资源 28: 较大图像 (198x158)
    res = next((r for r in resources if r['index'] == 28), None)
    if res:
        block = data[res['start']:res['end']]
        subindex = parse_subindex(block)
        if subindex:
            offset = subindex['offsets'][0]
            next_offset = subindex['offsets'][1]
            subblock = block[offset:next_offset]
            trace_decode(subblock, 28, 0)

if __name__ == '__main__':
    main()
