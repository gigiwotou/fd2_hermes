#!/usr/bin/env python3
"""
FDOTHER.DAT 完整资源提取工具 v2
=================================
基于逆向 sub_111BA, sub_16886, sub_4E98D 的结果:
- 4字节索引表 (sub_111BA: fseek(file, 4*index+6, 0))
- 索引0 = 768字节调色板 (sub_11DF2: FDOTHER_DAT + 3*a5)
- LMI1动画: "LMI1"+w(帧数)+h(首帧偏移), 从偏移6用4字节索引每帧
- RLE图像: word w + word h + RLE数据
- 嵌套DAT: "LLLLLL"+4字节子索引 (sub_25A96播放音频)
- 音频: 8位PCM原始数据 (AIL_set_sample_address)

输出BMP(无需PIL)和WAV格式
"""

import struct, os, sys

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'
OUTPUT_DIR = '/home/yinming/fd2_hermes/extracted/fdother_v2/'

def parse_offsets(dat_data):
    """解析4字节索引表"""
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
    """加载指定索引的资源"""
    if index >= len(offsets) - 1:
        return None
    start = offsets[index]
    end = offsets[index + 1]
    return dat_data[start:end]

def decode_rle(rle_data, max_pixels=None):
    """解码RLE压缩数据 (sub_4E98D)"""
    if len(rle_data) < 4:
        return None, None, []
    w = struct.unpack_from('<H', rle_data, 0)[0]
    h = struct.unpack_from('<H', rle_data, 2)[0]
    if w == 0 or h == 0 or w > 640 or h > 480:
        return w, h, []
    
    total = w * h
    if max_pixels:
        total = min(total, max_pixels)
    
    pos = 4
    pixels = []
    while len(pixels) < total and pos < len(rle_data):
        cmd = rle_data[pos]
        pos += 1
        if cmd & 0x80:  # 重复模式
            count = cmd & 0x7F
            if count == 0:
                count = 128
            if pos >= len(rle_data):
                break
            val = rle_data[pos]
            pos += 1
            pixels.extend([val] * count)
        else:  # 原始模式
            count = cmd
            if count == 0:
                count = 128
            end = min(pos + count, len(rle_data))
            pixels.extend(rle_data[pos:end])
            pos = end
    
    pixels = pixels[:total]
    return w, h, pixels

def write_bmp(filename, w, h, pixels, palette=None):
    """写8位索引BMP文件"""
    if not pixels or w <= 0 or h <= 0:
        return False
    
    # 默认调色板 (灰度)
    if palette is None:
        palette = bytes([i // 3 if i < 768 else 0 for i in range(1024)])
    
    row_size = (w + 3) & ~3  # 4字节对齐
    padding = row_size - w
    
    img_size = row_size * h
    file_size = 1078 + img_size  # 14+40+1024调色板+图像
    
    with open(filename, 'wb') as f:
        # BMP头
        f.write(b'BM')
        f.write(struct.pack('<I', file_size))
        f.write(struct.pack('<HH', 0, 0))
        f.write(struct.pack('<I', 1078))
        # DIB头
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
        # 调色板
        f.write(palette[:1024])
        # 像素 (BMP从底到顶)
        for y in range(h - 1, -1, -1):
            row_start = y * w
            row = pixels[row_start:row_start + w]
            f.write(bytes(row))
            f.write(b'\x00' * padding)
    return True

def write_wav(filename, pcm_data, sample_rate=8000):
    """写8位PCM WAV文件"""
    data_size = len(pcm_data)
    with open(filename, 'wb') as f:
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + data_size))
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))
        f.write(struct.pack('<H', 1))  # PCM
        f.write(struct.pack('<H', 1))  # 单声道
        f.write(struct.pack('<I', sample_rate))
        f.write(struct.pack('<I', sample_rate))  # 字节率
        f.write(struct.pack('<H', 1))  # 块对齐
        f.write(struct.pack('<H', 8))  # 8位
        f.write(b'data')
        f.write(struct.pack('<I', data_size))
        f.write(pcm_data)

def is_likely_audio(data, threshold=0.65):
    """检测数据是否可能是8位PCM音频"""
    if len(data) < 10:
        return False
    sample = data[:min(200, len(data))]
    near_center = sum(1 for b in sample if 90 <= b <= 170)
    return near_center / len(sample) > threshold

def extract_lmi1(res_data, output_prefix, palette=None):
    """提取LMI1动画的所有帧"""
    if len(res_data) < 8 or res_data[:4] != b'LMI1':
        return 0
    
    w_val = struct.unpack_from('<H', res_data, 4)[0]
    h_val = struct.unpack_from('<H', res_data, 6)[0]
    
    # w_val = 帧数, h_val = 首帧偏移 (基于sub_16886的逆向)
    frame_count = w_val
    frame0_offset = h_val
    
    extracted = 0
    for i in range(frame_count):
        idx_off = 6 + i * 4
        if idx_off + 4 > len(res_data):
            break
        
        frame_off = struct.unpack_from('<I', res_data, idx_off)[0]
        if frame_off == 0 or frame_off >= len(res_data):
            continue
        
        # 下一帧偏移
        if i + 1 < frame_count:
            next_off = struct.unpack_from('<I', res_data, 6 + (i + 1) * 4)[0]
        else:
            next_off = len(res_data)
        
        # 计算帧大小 (不超过资源末尾)
        frame_size = min(next_off - frame_off, len(res_data) - frame_off)
        if frame_size <= 0 or frame_size > 200000:
            continue
        
        frame_data = res_data[frame_off:frame_off + frame_size]
        
        # 尝试RLE解码
        fw, fh, pixels = decode_rle(frame_data, max_pixels=320*200)
        if fw and fh and len(pixels) == fw * fh:
            out_file = f"{output_prefix}_frame{i:03d}.bmp"
            write_bmp(out_file, fw, fh, pixels, palette)
            extracted += 1
        else:
            # 保存原始数据
            out_file = f"{output_prefix}_frame{i:03d}_raw.bin"
            with open(out_file, 'wb') as f:
                f.write(frame_data)
    
    return extracted

def extract_nested_dat(res_data, output_prefix, palette=None):
    """提取嵌套DAT (LLLLLL头) 的子资源"""
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
        
        # 递归检测LMI1
        if len(sub_data) >= 4 and sub_data[:4] == b'LMI1':
            n = extract_lmi1(sub_data, out_prefix, palette)
            bmp_count += n
            continue
        
        # 检测音频
        if is_likely_audio(sub_data):
            write_wav(f"{out_prefix}_audio.wav", sub_data)
            wav_count += 1
            continue
        
        # 尝试RLE解码
        fw, fh, pixels = decode_rle(sub_data)
        if fw and fh and len(pixels) == fw * fh:
            write_bmp(f"{out_prefix}.bmp", fw, fh, pixels, palette)
            bmp_count += 1
            continue
        
        # 未识别 - 作为原始数据保存
        out_file = f"{out_prefix}_raw.bin"
        with open(out_file, 'wb') as f:
            f.write(sub_data)
    
    return total_sub, bmp_count, wav_count

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    data = open(DAT_FILE, 'rb').read()
    offsets = parse_offsets(data)
    num_resources = len(offsets) - 1
    
    print(f"FDOTHER.DAT: {len(data)} 字节, {num_resources} 个资源")
    print(f"索引表: {len(offsets)} 个偏移值")
    print()
    
    # 加载调色板 (索引0)
    palette_data = load_resource(data, offsets, 0)
    if palette_data and len(palette_data) == 768:
        # 转换为BMP调色板格式 (1024字节: 256*4 BGRX)
        bmp_palette = bytearray(1024)
        for i in range(256):
            bmp_palette[i*4] = palette_data[i*3+2]      # B
            bmp_palette[i*4+1] = palette_data[i*3+1]    # G
            bmp_palette[i*4+2] = palette_data[i*3]      # R
            bmp_palette[i*4+3] = 0                       # X
        palette = bytes(bmp_palette)
        # 保存调色板
        with open(os.path.join(OUTPUT_DIR, 'res000_palette.pal'), 'wb') as f:
            f.write(palette_data)
        print(f"索引0: 调色板 (768字节, 256色 RGB)")
    else:
        palette = None
        print(f"索引0: 无效调色板 (大小={len(palette_data) if palette_data else 0})")
    
    # 统计
    stats = {'bmp': 0, 'wav': 0, 'pal': 1 if palette_data else 0, 'lmi1': 0, 'nested': 0, 'raw': 0, 'empty': 0}
    
    # 提取所有资源
    for i in range(1, num_resources):
        res_data = load_resource(data, offsets, i)
        if not res_data or len(res_data) == 0:
            stats['empty'] += 1
            continue
        
        prefix = os.path.join(OUTPUT_DIR, f'res{i:03d}')
        
        # LMI1 动画
        if len(res_data) >= 4 and res_data[:4] == b'LMI1':
            n = extract_lmi1(res_data, prefix, palette)
            stats['lmi1'] += 1
            stats['bmp'] += n
            if n == 0:
                # 保存原始LMI1数据
                with open(f"{prefix}_lmi1_raw.bin", 'wb') as f:
                    f.write(res_data)
                stats['raw'] += 1
            print(f"索引{i}: LMI1动画 ({len(res_data)}B, {n}帧提取)")
            continue
        
        # 嵌套DAT (LLLLLL)
        if len(res_data) >= 6 and res_data[:6] == b'LLLLLL':
            total, nbmp, nwav = extract_nested_dat(res_data, prefix, palette)
            stats['nested'] += 1
            stats['bmp'] += nbmp
            stats['wav'] += nwav
            raw_count = total - nbmp - nwav
            stats['raw'] += raw_count
            print(f"索引{i}: 嵌套DAT ({len(res_data)}B, {total}子资源: {nbmp}BMP+{nwav}WAV+{raw_count}原始)")
            continue
        
        # 音频数据
        if is_likely_audio(res_data):
            write_wav(f"{prefix}_audio.wav", res_data)
            stats['wav'] += 1
            print(f"索引{i}: 音频 ({len(res_data)}B)")
            continue
        
        # RLE图像
        fw, fh, pixels = decode_rle(res_data)
        if fw and fh and len(pixels) == fw * fh:
            write_bmp(f"{prefix}.bmp", fw, fh, pixels, palette)
            stats['bmp'] += 1
            print(f"索引{i}: RLE图像 {fw}x{fh} ({len(res_data)}B)")
            continue
        
        # 特殊格式 - 资源2(结构化数据)和资源4(位平面?)
        if i in [2, 4]:
            with open(f"{prefix}_special.bin", 'wb') as f:
                f.write(res_data)
            stats['raw'] += 1
            print(f"索引{i}: 特殊数据 ({len(res_data)}B)")
            continue
        
        # 未识别
        with open(f"{prefix}_unknown.bin", 'wb') as f:
            f.write(res_data)
        stats['raw'] += 1
        print(f"索引{i}: 未识别 ({len(res_data)}B, 头部={res_data[:8].hex()})")
    
    print(f"\n{'='*50}")
    print(f"FDOTHER.DAT 提取完成!")
    print(f"总资源: {num_resources}")
    print(f"  BMP图像: {stats['bmp']}")
    print(f"  WAV音频: {stats['wav']}")
    print(f"  调色板:  {stats['pal']}")
    print(f"  LMI1动画: {stats['lmi1']}组")
    print(f"  嵌套DAT: {stats['nested']}组")
    print(f"  原始/未识别: {stats['raw']}")
    print(f"  空资源:  {stats['empty']}")
    print(f"输出目录: {OUTPUT_DIR}")

if __name__ == '__main__':
    main()
