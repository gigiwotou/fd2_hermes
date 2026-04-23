#!/usr/bin/env python3
"""
分析 FDOTHER 资源的子结构
检查是否有偏移表
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def analyze_resource(f, idx):
    start, size = read_index(f, idx)
    f.seek(start)
    data = f.read(min(size, 500))

    print(f"=== 索引 {idx} (大小 {size}) ===")
    print(f"  头16字节: {data[:16].hex()}")

    w = struct.unpack('<H', data[0:2])[0]
    h = struct.unpack('<H', data[2:4])[0]
    print(f"  width={w}, height={h}")

    # 检查是否有偏移表 (在偏移6之后)
    if size > 10:
        # 读取4个可能的偏移值
        offsets = struct.unpack('<IIII', data[6:22]) if len(data) >= 22 else struct.unpack('<III', data[6:18])
        print(f"  偏移6后的值: {[hex(o) for o in offsets]}")

        # 检查这些偏移是否合理 (相对于start)
        for i, o in enumerate(offsets):
            if o < size:
                print(f"    偏移{i} ({hex(o)}) -> 数据: {data[o:o+4].hex() if o < len(data) else 'N/A'}")

    print()

def main():
    with open(DAT_FILE, 'rb') as f:
        # 分析多个资源
        for idx in [0, 1, 2, 3, 15, 16, 17, 18, 19, 22]:
            analyze_resource(f, idx)

if __name__ == '__main__':
    main()