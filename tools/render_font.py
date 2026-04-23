#!/usr/bin/env python3
"""渲染FDOTHER.DAT资源4的16x16位图字体为BMP图像"""

import struct

data = open('/home/yinming/fd2_dat/game/FDOTHER.DAT', 'rb').read()

offsets = []
off = 6
prev = 0
while off + 4 <= len(data):
    val = struct.unpack_from('<I', data, off)[0]
    if val < prev or val > len(data): break
    offsets.append(val)
    prev = val
    off += 4
    if len(offsets) > 500: break

res4 = data[offsets[4]:offsets[5]]
num_chars = len(res4) // 32  # 1824

# 渲染为BMP - 每行64个字符, 列数ceil(1824/64)=29行
cols = 64
rows = (num_chars + cols - 1) // cols
char_w = 16
char_h = 16
img_w = cols * char_w
img_h = rows * char_h

# 生成灰度图像
pixels = bytearray(img_w * img_h)

for ci in range(num_chars):
    base = ci * 32
    row_in_sheet = ci // cols
    col_in_sheet = ci % cols
    x0 = col_in_sheet * char_w
    y0 = row_in_sheet * char_h
    
    for r in range(16):
        if base + r*2 + 1 >= len(res4):
            break
        byte0 = res4[base + r*2]
        byte1 = res4[base + r*2 + 1]
        
        for bit in range(8):
            px = x0 + bit
            py = y0 + r
            if px < img_w and py < img_h:
                if (byte0 >> (7-bit)) & 1:
                    pixels[py * img_w + px] = 255
        
        for bit in range(8):
            px = x0 + 8 + bit
            py = y0 + r
            if px < img_w and py < img_h:
                if (byte1 >> (7-bit)) & 1:
                    pixels[py * img_w + px] = 255

# 写8位灰度BMP
row_size = (img_w + 3) & ~3
img_size = row_size * img_h
file_size = 1078 + img_size

# 灰度调色板
palette = bytearray(1024)
for i in range(256):
    palette[i*4] = i  # B
    palette[i*4+1] = i  # G
    palette[i*4+2] = i  # R

with open('/home/yinming/fd2_hermes/extracted/fdother_v3/res004_font_sheet.bmp', 'wb') as f:
    f.write(b'BM')
    f.write(struct.pack('<I', file_size))
    f.write(struct.pack('<HH', 0, 0))
    f.write(struct.pack('<I', 1078))
    f.write(struct.pack('<I', 40))
    f.write(struct.pack('<i', img_w))
    f.write(struct.pack('<i', img_h))
    f.write(struct.pack('<HH', 1, 8))
    f.write(struct.pack('<I', 0))
    f.write(struct.pack('<I', img_size))
    f.write(struct.pack('<i', 0))
    f.write(struct.pack('<i', 0))
    f.write(struct.pack('<I', 256))
    f.write(struct.pack('<I', 0))
    f.write(palette)
    for y in range(img_h - 1, -1, -1):
        row = pixels[y * img_w:(y + 1) * img_w]
        f.write(bytes(row))
        f.write(b'\x00' * (row_size - img_w))

print(f"字体渲染完成: {num_chars}字符, {img_w}x{img_h}, 保存为 res004_font_sheet.bmp")

# 顺便也分析资源2
res2 = data[offsets[2]:offsets[3]]
# 头部解析为uint32: 0x0138=312, 0x031C=796, 0x0005=5, 0x06E4=1764
# 也尝试作为uint16对: 0x0138=312(宽?), 0x0000=0, 0x031C=796, 0x0000=0, 0x0005=5, 0x0000=0, 0x06E4=1764
# 或者: 偏移表?
# 312 * 5 = 1560
# 37680 / 5 = 7536
# 796可能是帧数?
# 尝试: 每条目312字节, 共120条目? 37680/312=120.77 不整除
# 每条目47字节? 37680/47=801.7 不整除
# 37680/16 = 2355
# 尝试另一个角度: 这是1bpp位图
# 37680*8 = 301440像素
# 如果宽312: 301440/312=966.15 不整除
# 如果宽320: 301440/320=942 不整除
# 如果宽408: 301440/408=739

# 也许是: 312个条目的索引 + 数据?
# 前20字节=5个uint32: 312, 796, 5, 1764, ...
# 看更多偏移
off_values = []
for i in range(20):
    if i*4+4 <= 80:
        val = struct.unpack_from('<I', res2, i*4)[0]
        off_values.append(val)
print(f"\n资源2 前20个uint32值: {off_values}")

# 检查是否是递增偏移(像DAT索引)
is_index = all(off_values[i] <= off_values[i+1] for i in range(len(off_values)-1) if off_values[i+1] > 0)
print(f"是否递增偏移: {is_index}")

# 或者: 这些是不同大小/偏移的子数据块
# 让我看看如果作为4字节索引表解析
sub_offsets = [v for v in off_values if 0 < v < len(res2)]
print(f"有效偏移值: {sub_offsets}")
