#!/usr/bin/env python3
"""分析FDOTHER.DAT资源4 - 16x16位图字体"""

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
print(f"资源4: {len(res4)}字节")

# 每个字符32字节 (16行 x 2字节 = 16x16位图)
num_chars = len(res4) // 32
print(f"字符数: {num_chars} (如果16x16)")

# 显示前10个字符
for char_idx in range(min(10, num_chars)):
    offset = char_idx * 32
    print(f"\n字符{char_idx} (偏移{offset}):")
    for row in range(16):
        if offset + row*2 + 1 >= len(res4):
            break
        byte0 = res4[offset + row*2]
        byte1 = res4[offset + row*2+1]
        line = ''
        for bit in range(7, -1, -1):
            line += '#' if (byte0 >> bit) & 1 else '.'
        line += ' '
        for bit in range(7, -1, -1):
            line += '#' if (byte1 >> bit) & 1 else '.'
        print(f"  {line}")

# 也分析资源2
res2 = data[offsets[2]:offsets[3]]
print(f"\n\n资源2: {len(res2)}字节, 头部={res2[:16].hex()}")
# 头部uint32: 312, 796, 5, 1764
# 可能是312宽的某种动画/滚动数据
# 5帧 * 1764 = 8820 != 37680
# 37680 / 5 = 7536... 不太对
# 或者: 字体相关?
