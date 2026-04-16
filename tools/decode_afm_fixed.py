#!/usr/bin/env python3
"""
ANI.DAT 正确解码器 - 修复命令 0x09
"""

import struct
from PIL import Image
import os
import sys

# 获取脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

# 默认路径
ANI_DAT_PATH = os.path.join(PROJECT_DIR, 'game', 'ANI.DAT')
OUTPUT_DIR = os.path.join(PROJECT_DIR, 'docs', 'afm_animations')

# 全局缓冲区
palette_buf = bytearray(768)
pixel_buf = bytearray(64000)


def decode_pixel_rle(data: bytes, pos: int) -> int:
    """命令 0x06: RLE 解码像素"""
    global pixel_buf
    src_pos = pos
    dst_pos = 0
    
    while src_pos < len(data) and dst_pos < 64000:
        b = data[src_pos]
        src_pos += 1
        
        if (b & 0xC0) == 0xC0:
            count = b & 0x3F
            if src_pos < len(data):
                color = data[src_pos]
                src_pos += 1
                for i in range(min(count, 64000 - dst_pos)):
                    pixel_buf[dst_pos + i] = color
                dst_pos += count
        else:
            if dst_pos < 64000:
                pixel_buf[dst_pos] = b
            dst_pos += 1
    
    return src_pos - pos


def process_frame(param: int, frame_data: bytes):
    """处理帧数据"""
    global palette_buf, pixel_buf
    
    if param == 0 or len(frame_data) == 0:
        return
    
    data_pos = 0
    
    for _ in range(param):
        if data_pos >= len(frame_data):
            break
        
        cmd = frame_data[data_pos]
        data_pos += 1
        
        if cmd == 0x00:
            # 填充调色板
            if data_pos < len(frame_data):
                color = frame_data[data_pos]
                data_pos += 1
                for i in range(256):
                    palette_buf[i * 3] = color
                    palette_buf[i * 3 + 1] = color
                    palette_buf[i * 3 + 2] = color
        
        elif cmd == 0x01:
            # 复制调色板
            if data_pos + 768 <= len(frame_data):
                palette_buf[:] = frame_data[data_pos:data_pos + 768]
                data_pos += 768
        
        elif cmd == 0x02:
            # RLE 解码调色板
            src_pos = data_pos
            dst_pos = 0
            while dst_pos < 768 and src_pos < len(frame_data):
                b = frame_data[src_pos]
                src_pos += 1
                if (b & 0xC0) == 0xC0:
                    count = b & 0x3F
                    if src_pos < len(frame_data):
                        color = frame_data[src_pos]
                        src_pos += 1
                        for i in range(min(count, 768 - dst_pos)):
                            palette_buf[dst_pos + i] = color
                        dst_pos += count
                else:
                    palette_buf[dst_pos] = b
                    dst_pos += 1
            data_pos = src_pos
        
        elif cmd == 0x04:
            # 填充像素缓冲区
            if data_pos < len(frame_data):
                fill_byte = frame_data[data_pos]
                data_pos += 1
                for i in range(64000):
                    pixel_buf[i] = fill_byte
        
        elif cmd == 0x05:
            # 复制像素数据
            if data_pos + 64000 <= len(frame_data):
                pixel_buf[:] = frame_data[data_pos:data_pos + 64000]
                data_pos += 64000
        
        elif cmd == 0x06:
            # RLE 解码像素
            data_pos += decode_pixel_rle(frame_data, data_pos)
        
        elif cmd == 0x07:
            # 点绘制: [count:WORD][offset:WORD][color:BYTE]...
            count = struct.unpack('<H', frame_data[data_pos:data_pos+2])[0]
            data_pos += 2
            
            for _ in range(count):
                if data_pos + 3 > len(frame_data):
                    break
                offset = struct.unpack('<H', frame_data[data_pos:data_pos+2])[0]
                color = frame_data[data_pos+2]
                data_pos += 3
                
                if offset < 64000:
                    pixel_buf[offset] = color
        
        elif cmd == 0x08:
            # 填充段: [count:WORD][offset:WORD][size:BYTE][color:BYTE]...
            count = struct.unpack('<H', frame_data[data_pos:data_pos+2])[0]
            data_pos += 2
            
            for _ in range(count):
                if data_pos + 4 > len(frame_data):
                    break
                offset = struct.unpack('<H', frame_data[data_pos:data_pos+2])[0]
                size = frame_data[data_pos+2]
                color = frame_data[data_pos+3]
                data_pos += 4
                
                for i in range(min(size, 64000 - offset)):
                    pixel_buf[offset + i] = color
        
        elif cmd == 0x09:
            # 复制数据: [count:WORD][dst:WORD][size:BYTE][data: size bytes]...
            count = struct.unpack('<H', frame_data[data_pos:data_pos+2])[0]
            data_pos += 2
            
            for _ in range(count):
                if data_pos + 3 > len(frame_data):
                    break
                dst = struct.unpack('<H', frame_data[data_pos:data_pos+2])[0]
                size = frame_data[data_pos+2]
                data_pos += 3
                
                # 复制数据到像素缓冲区
                for i in range(min(size, 64000 - dst)):
                    if data_pos + i < len(frame_data):
                        pixel_buf[dst + i] = frame_data[data_pos + i]
                
                data_pos += size


def decode_afm(data: bytes, afm_offset: int, output_dir: str, afm_index: int):
    """解码单个 AFM 资源"""
    global palette_buf, pixel_buf
    
    frame_count = struct.unpack('<H', data[afm_offset + 165:afm_offset + 167])[0]
    frame_start = afm_offset + 173
    
    print(f"\nAFM {afm_index}: 偏移 0x{afm_offset:X}, 帧数 {frame_count}")
    
    # 重置缓冲区
    palette_buf = bytearray(768)
    pixel_buf = bytearray(64000)
    
    frames = []
    prev_pixel_buf = bytearray(64000)
    
    pos = frame_start
    
    for i in range(frame_count):
        if pos + 8 > len(data):
            break
        
        size = struct.unpack('<H', data[pos:pos+2])[0]
        param = struct.unpack('<H', data[pos+2:pos+4])[0]
        
        frame_data = data[pos+8:pos+8+size] if size > 0 else b''
        
        prev_pixel_buf[:] = pixel_buf
        process_frame(param, frame_data)
        
        pos += 8 + size
        
        if pixel_buf == prev_pixel_buf:
            continue
        
        img = Image.new('P', (320, 200))
        img.putdata(list(pixel_buf))
        
        # DOS 调色板转换 (6 位 -> 8 位)
        pal = []
        for j in range(256):
            r = min(255, palette_buf[j * 3] * 4)
            g = min(255, palette_buf[j * 3 + 1] * 4)
            b = min(255, palette_buf[j * 3 + 2] * 4)
            pal.extend([r, g, b])
        
        img.putpalette(pal)
        frames.append(img)
    
    print(f"  解码了 {len(frames)} 帧")
    
    if frames:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'afm_{afm_index}.gif')
        
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=100,
            loop=0
        )
        
        print(f"  保存到: {output_path}")
        print(f"  文件大小: {os.path.getsize(output_path):,} 字节")


def main():
    # 使用项目相对路径
    ani_dat_path = ANI_DAT_PATH
    output_dir = OUTPUT_DIR
    
    # 支持命令行参数
    if len(sys.argv) > 1:
        ani_dat_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    
    print("=" * 70)
    print("ANI.DAT AFM 解码器")
    print("=" * 70)
    print(f"输入文件: {ani_dat_path}")
    print(f"输出目录: {output_dir}")
    
    with open(ani_dat_path, 'rb') as f:
        data = f.read()
    
    # 找到所有 AFM 偏移
    afm_offsets = []
    pos = 6
    
    while pos < len(data) - 4:
        offset = struct.unpack('<I', data[pos:pos+4])[0]
        if offset == 0:
            break
        
        if offset < len(data) and offset + 167 < len(data):
            frame_count = struct.unpack('<H', data[offset + 165:offset + 167])[0]
            if frame_count > 0 and frame_count < 1000:
                afm_offsets.append(offset)
        
        pos += 4
        if len(afm_offsets) > 20:
            break
    
    print(f"找到 {len(afm_offsets)} 个 AFM 资源")
    
    for idx, offset in enumerate(afm_offsets):
        decode_afm(data, offset, output_dir, idx)
    
    print(f"\n完成！所有动画保存在: {output_dir}")


if __name__ == '__main__':
    main()
