#!/usr/bin/env python3
"""分析 FDOTHER.DAT 中的 LMI1 格式资源"""

import struct
import os
import sys

dat_path = '/home/yinming/fd2_dat/game/FDOTHER.DAT'
with open(dat_path, 'rb') as f:
    data = f.read()

def get_resource(idx):
    offset = 4 * idx + 6
    start = struct.unpack('<I', data[offset:offset+4])[0]
    end = struct.unpack('<I', data[offset+4:offset+8])[0]
    if start > 0 and end > start and end <= len(data):
        return data[start:end]
    return None

def hex_dump(buf, start_offset=0, max_bytes=128):
    for i in range(0, min(max_bytes, len(buf)), 16):
        hex_str = ' '.join(f'{buf[i+j]:02x}' for j in range(min(16, len(buf)-i)))
        ascii_str = ''.join(chr(buf[i+j]) if 32 <= buf[i+j] < 127 else '.' for j in range(min(16, len(buf)-i)))
        print(f"  {start_offset+i:04x}: {hex_str:<48s}  {ascii_str}")

# 收集所有资源的基本信息
print("=" * 70)
print("FDOTHER.DAT 资源分类总览")
print("=" * 70)

categories = {
    'PALETTE': [],    # 768字节调色板
    'SPRITE': [],     # [width][height][pixel_data] 精灵
    'RAW_IMAGE': [],  # 320x200 raw 图像
    'COMP_IMAGE': [], # 320x200 压缩图像
    'LMI1': [],       # LMI1 动画格式
    'LLLL': [],       # 嵌套DAT容器
    'OTHER': [],      # 其他
}

for idx in range(103):
    r = get_resource(idx)
    if r is None:
        continue
    
    size = len(r)
    if size < 4:
        categories['OTHER'].append((idx, size, ''))
        continue
    
    magic = r[:4]
    
    if size == 768 and idx == 0:
        categories['PALETTE'].append((idx, size, '768B palette'))
    elif magic == b'LMI1':
        categories['LMI1'].append((idx, size, magic.decode('ascii', errors='replace')))
    elif magic == b'LLLL':
        categories['LLLL'].append((idx, size, magic.decode('ascii', errors='replace')))
    else:
        # 检查是否 [width][height][pixels]
        if size >= 4:
            w = struct.unpack('<H', r[0:2])[0]
            h = struct.unpack('<H', r[2:4])[0]
            if w > 0 and h > 0 and w * h == size - 4:
                if w == 320 and h == 200:
                    categories['RAW_IMAGE'].append((idx, size, f'{w}x{h} raw'))
                else:
                    categories['SPRITE'].append((idx, size, f'{w}x{h} sprite'))
            elif w > 0 and h > 0 and w == 320 and h == 200:
                categories['COMP_IMAGE'].append((idx, size, f'{w}x{h} compressed'))
            else:
                categories['OTHER'].append((idx, size, f'w={w}h={h}'))

for cat, items in categories.items():
    if items:
        print(f"\n{cat} ({len(items)} 个):")
        for idx, size, desc in items:
            print(f"  [{idx:3d}] {size:7d}B  {desc}")

# 深入分析 LMI1 格式
print("\n" + "=" * 70)
print("LMI1 格式深入分析")
print("=" * 70)

for idx in range(103):
    r = get_resource(idx)
    if r is None or len(r) < 8 or r[:4] != b'LMI1':
        continue
    
    count = struct.unpack('<H', r[4:6])[0]
    header_size = struct.unpack('<H', r[6:8])[0]
    frame_data_total = len(r) - header_size
    
    print(f"\n--- FDOTHER[{idx}]: {len(r)}B, frames={count}, header_size={header_size} ---")
    print(f"头部数据:")
    hex_dump(r, 0, min(header_size, 128))
    
    if count > 0 and frame_data_total > 0:
        # 检查帧大小是否固定
        if frame_data_total % count == 0:
            frame_size = frame_data_total // count
            print(f"  帧大小固定: {frame_size} 字节")
            
            # 看帧0数据
            print(f"  帧0数据 (从偏移{header_size}):")
            hex_dump(r, header_size, min(frame_size, 64))
            
            # 分析帧0中的图像尺寸信息
            f0 = r[header_size:header_size+frame_size]
            if frame_size >= 4:
                fw = struct.unpack('<H', f0[0:2])[0]
                fh = struct.unpack('<H', f0[2:4])[0]
                if 0 < fw <= 320 and 0 < fh <= 200:
                    pixel_bytes = frame_size - 4
                    if fw * fh <= pixel_bytes:
                        print(f"  帧0含图像: {fw}x{fh}, 像素数据={pixel_bytes}B")
        else:
            # 变长帧 - 用偏移表
            print(f"  帧大小不固定! 总帧数据={frame_data_total}, 平均={frame_data_total/count:.1f}")
            
            # 解析偏移表 (每条4字节: [2B pad=0][2B offset])
            # 但看 FDOTHER[3] 的成功案例: word_hi才是偏移
            offsets = []
            for fi in range(count):
                eo = 8 + fi * 4
                if eo + 4 > header_size:
                    break
                word_hi = struct.unpack('<H', r[eo+2:eo+4])[0]
                offsets.append(word_hi)
            
            if len(offsets) > 1:
                print(f"  偏移表 (word_hi): {offsets[:5]}...")
                deltas = [offsets[i+1]-offsets[i] for i in range(min(5, len(offsets)-1))]
                print(f"  帧大小(delta): {deltas}")
                
                # 检查 word_hi 是否是文件内绝对偏移
                if offsets[0] < len(r):
                    print(f"  -> 可能是绝对偏移 (word_hi[0]={offsets[0]} < {len(r)})")
                    # 读帧0数据
                    f0_start = offsets[0]
                    f0_end = offsets[1] if len(offsets) > 1 else len(r)
                    f0_size = f0_end - f0_start
                    print(f"  帧0: offset={f0_start}, size={f0_size}")
                    if f0_start < len(r) and f0_end <= len(r):
                        hex_dump(r, f0_start, min(f0_size, 48))
                elif offsets[0] > 0xFF00:
                    # 可能是 segment:offset 形式 (DOS!)
                    # 或者字节序需要调整
                    # 试: 整个DWORD作为segmented地址
                    print(f"  -> word_hi值太大, 可能是分段地址或其他编码")
                    
                    # 也许偏移表格式是每条2字节?
                    word_offsets = []
                    for fi in range(min(count, (header_size - 8) // 2)):
                        wo = struct.unpack('<H', r[8 + fi*2:10 + fi*2])[0]
                        word_offsets.append(wo)
                    print(f"  试2字节偏移: {word_offsets[:10]}...")
