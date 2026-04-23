#!/usr/bin/env python3
"""
验证 FDOTHER 索引1的偏移表位置
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def main():
    with open(DAT_FILE, 'rb') as f:
        start, size = read_index(f, 1)
        f.seek(start)
        data = f.read(size)

        print(f"索引1: {size} 字节")

        # 分析偏移表 - 在字节6之后 (按照 sub_111BA 的格式)
        print("\n偏移表 (从字节6开始):")
        for i in range(10):
            off = 6 + i * 4
            if off + 4 <= size:
                val = struct.unpack('<I', data[off:off+4])[0]
                print(f"  表项{i} 偏移{off}: 0x{val:x} ({val})")

                # 检查该偏移处是否是RLE头
                if val < size and val > 0:
                    sub_data = data[val:val+4]
                    sub_w = struct.unpack('<H', sub_data[0:2])[0] if val + 2 <= size else 0
                    sub_h = struct.unpack('<H', sub_data[2:4])[0] if val + 4 <= size else 0
                    print(f"    -> 偏移处: width={sub_w}, height={sub_h}")

        # 现在让我们直接用偏移表0x56作为子图像偏移来解码
        print("\n\n尝试从偏移0x56解码:")
        sub_off = 0x56
        if sub_off + 4 <= size:
            sub_data = data[sub_off:]
            print(f"  前16字节: {sub_data[:16].hex()}")
            sub_w = struct.unpack('<H', sub_data[0:2])[0]
            sub_h = struct.unpack('<H', sub_data[2:4])[0]
            print(f"  尺寸: {sub_w}x{sub_h}")

            # 检查是否是 LMI1
            if sub_data[4:6] == b'LM':
                print(f"  LMI1 标记!")
            if sub_data[4:8] == b'LMI1':
                frame_count = struct.unpack('<H', sub_data[8:10])[0]
                print(f"  LMI1 动画: {frame_count} 帧")

if __name__ == '__main__':
    main()