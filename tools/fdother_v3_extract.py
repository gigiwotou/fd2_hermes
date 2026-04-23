#!/usr/bin/env python3
"""
FDOTHER.DAT 完整资源提取工具 v3
=================================
基于逆向 sub_111BA, sub_16886, sub_4E98D 的完整实现:
- 4字节索引表 (sub_111BA: fseek(file, 4*index+6, 0))
- 索引0 = 768字节调色板 (sub_11DF2)
- LMI1动画: "LMI1"+frame_count(2B)+first_frame_offset(2B), 从偏移6用4字节索引每帧
- RLE v2图像: 2位命令码(00原始/01填充/10跳过/11隔像素), 基于sub_4E98D
- 嵌套DAT: "LLLLLL"+4字节子索引 (sub_25A96播放音频)
- 音频: 8位PCM原始数据 (AIL_set_sample_address)
"""

import struct, os, sys

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'
OUTPUT_DIR = '/home/yinming/fd2_hermes/extracted/fdother_v3/'

def parse_offsets(dat_data):
    """解析4字节索引表 (基于sub_111BA的4*index+6偏移)"""
    offsets = []
    off = 6
    prev = 0
    while off + 4 <= len(dat_data):
        val = struct.unpack_from('<I', dat_data, off)[0]
        if val < prev or val > len(dat_data):
            break
        offsets.append(val)
        prev = val
        off += 4
        if len(offsets) > 500:
            break
    return offsets

def load_resource(dat_data, offsets, index):
    if index >= len(offsets) - 1:
        return None
    return dat_data[offsets[index]:offsets[index + 1]]

def decode_rle_v2(rle_data):
    """基于sub_4E98D的RLE解码 (4种模式: 00原始/01填充/10跳过/11隔像素)"""
    if len(rle_data) < 4:
        return None, None, []
    
    w = struct.unpack_from('<H', rle_data, 0)[0]
    h = struct.unpack_from('<H', rle_data, 2)[0]
    if w == 0 or h == 0 or w > 800 or h > 600:
        return w, h, []
    
    dst = [0] * (w * h)
    src_pos = 4
    
    for row in range(h):
        x = 0
        remaining = w
        
        while remaining > 0 and src_pos < len(rle_data):
            cmd = rle_data[src_pos]
            src_pos += 1
            
            bit7 = (cmd >> 7) & 1
            bit6 = (cmd >> 6) & 1
            count = (cmd & 0x3F) + 1
            mode = (bit7 << 1) | bit6
            
            if mode == 0:  # 00: 原始数据 (从src复制count字节)
                for i in range(count):
                    if x >= w or src_pos >= len(rle_data):
                        break
                    dst[row * w + x] = rle_data[src_pos]
                    src_pos += 1
                    x += 1
                    remaining -= 1
                    
            elif mode == 1:  # 01: 单色填充 (读1字节,重复count次)
                if src_pos >= len(rle_data):
                    break
                val = rle_data[src_pos]
                src_pos += 1
                for i in range(count):
                    if x >= w:
                        break
                    dst[row * w + x] = val
                    x += 1
                    remaining -= 1
                    
            elif mode == 2:  # 10: 跳过 (透明,保持原值)
                x += count
                remaining -= count
                
            elif mode == 3:  # 11: 隔像素写入 (读1字节,每隔1像素写,消耗2*count像素位)
                if src_pos >= len(rle_data):
                    break
                val = rle_data[src_pos]
                src_pos += 1
                for i in range(count):
                    if x + 1 >= w:
                        break
                    dst[row * w + x + 1] = val
                    x += 2
                    remaining -= 2
    
    return w, h, dst

def write_bmp(filename, w, h, pixels, palette=None):
    """写8位索引BMP"""
    if not pixels or w <= 0 or h <= 0:
        return False
    if palette is None:
        palette = bytes([i // 3 if i < 768 else 0 for i in range(1024)])
    
    row_size = (w + 3) & ~3
    img_size = row_size * h
    file_size = 1078 + img_size
    
    with open(filename, 'wb') as f:
        f.write(b'BM')
        f.write(struct.pack('<I', file_size))
        f.write(struct.pack('<HH', 0, 0))
        f.write(struct.pack('<I', 1078))
        f.write(struct.pack('<I', 40))
        f.write(struct.pack('<i', w))
        f.write(struct.pack('<i', h))
        f.write(struct.pack('<HH', 1, 8))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', img_size))
        f.write(struct.pack('<i', 2835))
        f.write(struct.pack('<i', 2835))
        f.write(struct.pack('<I', 256))
        f.write(struct.pack('<I', 0))
        f.write(palette[:1024])
        for y in range(h - 1, -1, -1):
            row = pixels[y * w:(y + 1) * w]
            f.write(bytes(row))
            f.write(b'\x00' * (row_size - w))
    return True

def write_wav(filename, pcm_data, sample_rate=8000):
    """写8位PCM WAV"""
    data_size = len(pcm_data)
    with open(filename, 'wb') as f:
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + data_size))
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))
        f.write(struct.pack('<H', 1))
        f.write(struct.pack('<H', 1))
        f.write(struct.pack('<I', sample_rate))
        f.write(struct.pack('<I', sample_rate))
        f.write(struct.pack('<H', 1))
        f.write(struct.pack('<H', 8))
        f.write(b'data')
        f.write(struct.pack('<I', data_size))
        f.write(pcm_data)

def is_likely_audio(data, threshold=0.65):
    if len(data) < 10:
        return False
    sample = data[:min(200, len(data))]
    near_center = sum(1 for b in sample if 90 <= b <= 170)
    return near_center / len(sample) > threshold

def is_palette(data):
    """检测是否是768字节调色板"""
    if len(data) != 768:
        return False
    # 调色板值通常在0-63范围(6位VGA)
    max_val = max(data)
    return max_val <= 63

def extract_lmi1(res_data, output_prefix, palette=None):
    """提取LMI1动画帧 (基于sub_16886: *(DWORD*)(a7+4*a8+6)+a7)"""
    if len(res_data) < 8 or res_data[:4] != b'LMI1':
        return 0
    
    frame_count = struct.unpack_from('<H', res_data, 4)[0]
    first_offset = struct.unpack_from('<H', res_data, 6)[0]
    
    extracted = 0
    for i in range(frame_count):
        idx_off = 6 + i * 4
        if idx_off + 4 > len(res_data):
            break
        
        frame_off = struct.unpack_from('<I', res_data, idx_off)[0]
        if frame_off == 0 or frame_off >= len(res_data):
            continue
        
        # 帧大小
        if i + 1 < frame_count:
            next_idx = 6 + (i + 1) * 4
            next_off = struct.unpack_from('<I', res_data, next_idx)[0] if next_idx + 4 <= len(res_data) else len(res_data)
        else:
            next_off = len(res_data)
        
        frame_size = min(next_off - frame_off, len(res_data) - frame_off)
        if frame_size <= 0 or frame_size > 500000:
            continue
        
        frame_data = res_data[frame_off:frame_off + frame_size]
        fw, fh, pixels = decode_rle_v2(frame_data)
        
        if fw and fh and len(pixels) == fw * fh:
            out_file = f"{output_prefix}_frame{i:03d}.bmp"
            write_bmp(out_file, fw, fh, pixels, palette)
            extracted += 1
    
    return extracted

def extract_nested_dat(res_data, output_prefix, palette=None):
    """提取嵌套DAT (LLLLLL) 子资源"""
    if len(res_data) < 6 or res_data[:6] != b'LLLLLL':
        return 0, 0, 0
    
    sub_offsets = parse_offsets(res_data)
    bmp_count = wav_count = 0
    total_sub = len(sub_offsets) - 1
    
    for j in range(total_sub):
        sub_start = sub_offsets[j]
        sub_end = sub_offsets[j + 1]
        if sub_start >= sub_end or sub_end > len(res_data):
            continue
        
        sub_data = res_data[sub_start:sub_end]
        out_prefix = f"{output_prefix}_sub{j:02d}"
        
        # 递归LMI1
        if len(sub_data) >= 4 and sub_data[:4] == b'LMI1':
            n = extract_lmi1(sub_data, out_prefix, palette)
            bmp_count += n
            continue
        
        # 调色板
        if is_palette(sub_data):
            with open(f"{out_prefix}_palette.pal", 'wb') as f:
                f.write(sub_data)
            continue
        
        # 音频
        if is_likely_audio(sub_data):
            write_wav(f"{out_prefix}_audio.wav", sub_data)
            wav_count += 1
            continue
        
        # RLE图像
        fw, fh, pixels = decode_rle_v2(sub_data)
        if fw and fh and len(pixels) == fw * fh:
            write_bmp(f"{out_prefix}.bmp", fw, fh, pixels, palette)
            bmp_count += 1
            continue
        
        # 未识别
        with open(f"{out_prefix}_raw.bin", 'wb') as f:
            f.write(sub_data)
    
    return total_sub, bmp_count, wav_count

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    data = open(DAT_FILE, 'rb').read()
    offsets = parse_offsets(data)
    num_resources = len(offsets) - 1
    
    print(f"FDOTHER.DAT: {len(data)} 字节, {num_resources} 个资源")
    print()
    
    # 加载调色板 (索引0)
    palette_data = load_resource(data, offsets, 0)
    palette = None
    if palette_data and len(palette_data) == 768:
        bmp_palette = bytearray(1024)
        for i in range(256):
            bmp_palette[i*4] = palette_data[i*3+2]
            bmp_palette[i*4+1] = palette_data[i*3+1]
            bmp_palette[i*4+2] = palette_data[i*3]
            bmp_palette[i*4+3] = 0
        palette = bytes(bmp_palette)
        with open(os.path.join(OUTPUT_DIR, 'res000_palette.pal'), 'wb') as f:
            f.write(palette_data)
        print(f"索引0: 调色板 (768字节, 256色 RGB)")
    
    stats = {'bmp': 0, 'wav': 0, 'pal': 0, 'lmi1': 0, 'nested': 0, 'raw': 0, 'empty': 0}
    
    for i in range(1, num_resources):
        res_data = load_resource(data, offsets, i)
        if not res_data or len(res_data) == 0:
            stats['empty'] += 1
            continue
        
        prefix = os.path.join(OUTPUT_DIR, f'res{i:03d}')
        
        # LMI1动画
        if len(res_data) >= 4 and res_data[:4] == b'LMI1':
            n = extract_lmi1(res_data, prefix, palette)
            stats['lmi1'] += 1
            stats['bmp'] += n
            if n == 0:
                with open(f"{prefix}_lmi1_raw.bin", 'wb') as f:
                    f.write(res_data)
                stats['raw'] += 1
            print(f"索引{i}: LMI1 ({len(res_data)}B, {n}帧)")
            continue
        
        # 嵌套DAT
        if len(res_data) >= 6 and res_data[:6] == b'LLLLLL':
            total, nbmp, nwav = extract_nested_dat(res_data, prefix, palette)
            stats['nested'] += 1
            stats['bmp'] += nbmp
            stats['wav'] += nwav
            raw_count = total - nbmp - nwav
            stats['raw'] += raw_count
            print(f"索引{i}: 嵌套DAT ({len(res_data)}B, {total}子: {nbmp}BMP+{nwav}WAV+{raw_count}原始)")
            continue
        
        # 调色板
        if is_palette(res_data):
            with open(f"{prefix}_palette.pal", 'wb') as f:
                f.write(res_data)
            stats['pal'] += 1
            print(f"索引{i}: 调色板 ({len(res_data)}B)")
            continue
        
        # 音频
        if is_likely_audio(res_data):
            write_wav(f"{prefix}_audio.wav", res_data)
            stats['wav'] += 1
            print(f"索引{i}: 音频 ({len(res_data)}B)")
            continue
        
        # RLE图像
        fw, fh, pixels = decode_rle_v2(res_data)
        if fw and fh and len(pixels) == fw * fh:
            filled = sum(1 for p in pixels if p != 0)
            write_bmp(f"{prefix}.bmp", fw, fh, pixels, palette)
            stats['bmp'] += 1
            print(f"索引{i}: RLE图像 {fw}x{fh} ({len(res_data)}B, {filled}像素)")
            continue
        
        # 未识别
        with open(f"{prefix}_unknown.bin", 'wb') as f:
            f.write(res_data)
        stats['raw'] += 1
        print(f"索引{i}: 未识别 ({len(res_data)}B, 头部={res_data[:8].hex()})")
    
    # 统计
    all_files = os.listdir(OUTPUT_DIR)
    total_files = len(all_files)
    bmp_files = sum(1 for f in all_files if f.endswith('.bmp'))
    wav_files = sum(1 for f in all_files if f.endswith('.wav'))
    pal_files = sum(1 for f in all_files if f.endswith('.pal'))
    other_files = total_files - bmp_files - wav_files - pal_files
    
    print(f"\n{'='*50}")
    print(f"FDOTHER.DAT 提取完成!")
    print(f"  BMP图像: {bmp_files}")
    print(f"  WAV音频: {wav_files}")
    print(f"  调色板:  {pal_files}")
    print(f"  其他:    {other_files}")
    print(f"  总文件:  {total_files}")
    print(f"输出: {OUTPUT_DIR}")

if __name__ == '__main__':
    main()
