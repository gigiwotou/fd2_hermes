#!/usr/bin/env python3
"""FDOTHER.DAT 子项格式重新分析

像素计数不匹配说明头部解析或RLE假设错误。
需要重新理解数据结构。

关键线索:
1. 资源18子项2: 数据143字节, 声称9x105=945像素, 但v3解码只得819像素
2. 资源28子项0: 数据567字节, 声称198x158=31284像素, 但解码只得6686像素
3. 资源28子项0 头部有异常: pad=65536(0x10000), unk=31232(0x7A00)

重新思考头部格式...
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

def reanalyze_header(subblock, res_idx, sub_idx):
    """重新分析头部格式"""
    print(f"\n{'='*70}")
    print(f"头部重新分析: 资源 {res_idx}, 子项 {sub_idx}")
    print(f"数据大小: {len(subblock)} 字节")
    print(f"前 16 字节: {subblock[:16].hex()}")
    
    # 尝试多种头部格式
    
    # 格式A: [w:2][h:2][pad:4][unk:2] = 10 字节头
    w_a = struct.unpack_from('<H', subblock, 0)[0]
    h_a = struct.unpack_from('<H', subblock, 2)[0]
    
    # 格式B: [w:2][h:2][x:2][y:2][unk1:2][unk2:2] = 12 字节头
    x_b = struct.unpack_from('<H', subblock, 4)[0]
    y_b = struct.unpack_from('<H', subblock, 6)[0]
    u1_b = struct.unpack_from('<H', subblock, 8)[0]
    u2_b = struct.unpack_from('<H', subblock, 10)[0]
    
    print(f"\n格式A: w={w_a}, h={h_a}, pixels={w_a*h_a}")
    print(f"格式B: w={w_a}, h={h_a}, x={x_b}, y={y_b}, u1={u1_b}, u2={u2_b}")
    
    # 检查偏移 4-7 是否是 DWORD
    d1 = struct.unpack_from('<I', subblock, 4)[0]
    print(f"偏移4作为DWORD: {d1} (0x{d1:08X})")
    
    # 另一种可能: 整个数据不是从偏移10开始
    # 也许头部更短或更长
    # 查找数据中像素开始的位置
    
    # 观察资源18子项2的数据:
    # 09 00 69 00 00 00 00 00 00 05 00 2c 00 40 27 c2
    # 如果头部只有 4 字节 (width + height):
    # 09 00 69 00 -> w=9, h=105
    # 然后从偏移4开始就是数据
    # 00 00 00 00 00 05 00 2c 00 40 27 c2...
    
    # 或者头部是 8 字节:
    # 09 00 69 00 00 00 00 00 -> w=9, h=105, pad=0
    # 然后从偏移8开始:
    # 00 05 00 2c 00 40 27 c2...
    
    # 关键观察: 偏移4后的 00 00 00 00 可能是:
    # - 如果是精灵: hot_x=0, hot_y=0
    # - 如果是偏移: 数据区偏移=0
    
    # 再看另一个线索: 在FD2的反编译代码中
    # sub_111BA 是DAT加载函数
    # 游戏如何使用这些子项数据?
    
    # 让我尝试一种全新的思路:
    # 这可能不是RLE, 而是一种 sprite 格式
    # 数据可能是列优先存储的, 而不是行优先
    
    print(f"\n--- 尝试: 列优先存储 ---")
    # 如果 width=9, height=105
    # 每列 105 像素, 共 9 列
    # 数据可能按列存储
    
    # 尝试另一种头部:
    # 偏移 8 的值 = 0x0500 = 1280
    # 对资源18子项2: 偏移8是 00 05 -> 0x0500 = 1280 (little endian)
    # 等等, 00 05 in LE = 0x0500 = 1280? 不, 05 00 = 0x0005 = 5
    
    # 重新看数据:
    # 09 00 69 00 00 00 00 00 00 05 00 2c 00 40 27 c2
    # w=0x0009=9, h=0x0069=105
    # byte[4..7] = 00 00 00 00
    # byte[8] = 00
    # byte[9] = 05
    # byte[10] = 00
    # byte[11] = 2c
    
    # 新假设: 头部结构可能是:
    # [width:2][height:2][flags:4][data_offset:2]
    # data_offset = 5? -> 数据从偏移 5 开始? 不对
    
    # 或者:
    # [width:2][height:2][hot_x:2][hot_y:2][line_data_size:2][...]
    # line_data_size = 0x0000 (偏移8-9)
    # 不, 那没有意义
    
    # 让我看看AFM格式的头部作为参考
    # AFM 头部 173 字节, 偏移 165-166 是帧数
    # AFM 帧: [size:2][param:2][pad:4][data...]
    
    # 子项头部可能类似AFM帧:
    # [width:2][height:2][size:2][param:2][data...]
    # 但这里 width=9, height=105, size=0, param=0 不太对
    
    # 试试完全不同的思路:
    # 也许偏移0不是width, 而是某种命令代码
    # 0x0009 可能是一个子命令
    
    print(f"\n--- 尝试: 命令流格式 ---")
    # 如果 0x09 是命令码, 0x69 是参数
    # 命令 0x09 在AFM中是"复制数据"
    
    # 让我看看所有子项的第一个WORD的分布
    return subblock[:16]

def scan_all_subitem_headers(data, resources):
    """扫描所有子项的头部模式"""
    print(f"\n\n{'='*70}")
    print(f"所有子项头部模式扫描")
    print(f"{'='*70}")
    
    results = []
    
    for res_idx in [1, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 30, 32, 33, 34, 44]:
        res = next((r for r in resources if r['index'] == res_idx), None)
        if not res:
            continue
        
        block = data[res['start']:res['end']]
        subindex = parse_subindex(block)
        if not subindex:
            continue
        
        for i in range(min(3, len(subindex['offsets']))):
            offset = subindex['offsets'][i]
            next_offset = subindex['offsets'][i + 1] if i + 1 < len(subindex['offsets']) else len(block)
            
            if offset >= len(block) or next_offset > len(block):
                continue
            
            subblock = block[offset:next_offset]
            
            if len(subblock) < 16:
                continue
            
            # 读取各种可能的头部字段
            w = struct.unpack_from('<H', subblock, 0)[0]
            h = struct.unpack_from('<H', subblock, 2)[0]
            d1 = struct.unpack_from('<H', subblock, 4)[0]
            d2 = struct.unpack_from('<H', subblock, 6)[0]
            d3 = struct.unpack_from('<H', subblock, 8)[0]
            d4 = struct.unpack_from('<H', subblock, 10)[0]
            
            results.append({
                'res': res_idx,
                'sub': i,
                'size': len(subblock),
                'w': w, 'h': h,
                'd1': d1, 'd2': d2,
                'd3': d3, 'd4': d4
            })
    
    print(f"{'资源':>4} {'子项':>4} {'大小':>6} {'w':>4} {'h':>4} {'d1':>5} {'d2':>5} {'d3':>5} {'d4':>5}")
    print("-" * 60)
    
    for r in results:
        print(f"{r['res']:>4} {r['sub']:>4} {r['size']:>6} {r['w']:>4} {r['h']:>4} {r['d1']:>5} {r['d2']:>5} {r['d3']:>5} {r['d4']:>5}")
    
    # 分析模式
    print(f"\n模式分析:")
    
    # 检查 d1,d2 是否总是 0
    all_zero_d1d2 = all(r['d1'] == 0 and r['d2'] == 0 for r in results)
    print(f"  d1,d2 总是0: {all_zero_d1d2}")
    
    # 检查 d3,d4 的值
    d3_values = set(r['d3'] for r in results)
    d4_values = set(r['d4'] for r in results)
    print(f"  d3 唯一值: {sorted(d3_values)[:20]}")
    print(f"  d4 唯一值: {sorted(d4_values)[:20]}")

def try_decode_with_offset(data, subblock, data_start_offset):
    """尝试从不同偏移开始解码"""
    width = struct.unpack_from('<H', subblock, 0)[0]
    height = struct.unpack_from('<H', subblock, 2)[0]
    expected = width * height
    
    compressed = subblock[data_start_offset:]
    
    # 用 v3 解码
    pixels = [0] * expected
    pos = 0
    src = 0
    
    while src < len(compressed) and pos < expected:
        cmd = compressed[src]
        src += 1
        
        hi = cmd & 0xC0
        lo = cmd & 0x3F
        
        if hi == 0x00:
            pixels[pos] = cmd
            pos += 1
        elif hi == 0x40:
            if src < len(compressed):
                val = compressed[src]
                src += 1
                count = lo + 1
                for _ in range(count):
                    if pos < expected:
                        pixels[pos] = val
                        pos += 1
        elif hi == 0x80:
            count = lo + 1
            pos += count
        else:
            if src < len(compressed):
                val = compressed[src]
                src += 1
                count = lo + 1
                for _ in range(count):
                    if pos < expected:
                        pixels[pos] = val
                        pos += 1
    
    return pos, expected

def test_data_offsets(subblock, res_idx, sub_idx):
    """测试不同数据起始偏移"""
    width = struct.unpack_from('<H', subblock, 0)[0]
    height = struct.unpack_from('<H', subblock, 2)[0]
    
    print(f"\n测试资源 {res_idx} 子项 {sub_idx} (w={width}, h={height}, expected={width*height})")
    
    for offset in [4, 6, 8, 10, 12, 14]:
        decoded, expected = try_decode_with_offset(None, subblock, offset)
        match = "MATCH!" if decoded == expected else f"{decoded}/{expected}"
        print(f"  offset={offset}: decoded={match}")

def main():
    data = read_dat_file()
    resources = get_resources(data)
    
    # 扫描所有子项头部
    scan_all_subitem_headers(data, resources)
    
    # 对几个子项重新分析头部
    for res_idx in [18, 28]:
        res = next((r for r in resources if r['index'] == res_idx), None)
        if not res:
            continue
        
        block = data[res['start']:res['end']]
        subindex = parse_subindex(block)
        if not subindex:
            continue
        
        sub_idx = 2 if res_idx == 18 else 0
        offset = subindex['offsets'][sub_idx]
        next_offset = subindex['offsets'][sub_idx + 1] if sub_idx + 1 < len(subindex['offsets']) else len(block)
        
        subblock = block[offset:next_offset]
        reanalyze_header(subblock, res_idx, sub_idx)
        test_data_offsets(subblock, res_idx, sub_idx)

if __name__ == '__main__':
    main()
