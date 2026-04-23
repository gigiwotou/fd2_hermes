#!/usr/bin/env python3
"""
验证每个子项前9字节是否是width/height等信息
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def main():
    with open(DAT_FILE, 'rb') as f:
        # 索引18的数据
        start, size = read_index(f, 18)
        f.seek(start)
        data = f.read(size)

        print("索引18数据解析:\n")
        print(f"总大小: {size} 字节\n")

        # 字节0-3: width=16, height=16
        w0 = struct.unpack('<H', data[0:2])[0]
        h0 = struct.unpack('<H', data[2:4])[0]
        print(f"字节0: width={w0}, height={h0}")

        # 字节4: sub_count
        sub_count = struct.unpack('<H', data[4:6])[0]
        print(f"字节4: sub_count={sub_count}")

        # offset表从字节6开始
        print(f"\nOffset表 (从字节6开始，每项4字节):")
        for i in range(min(sub_count, 17)):
            off = 6 + i * 4
            if off + 4 > len(data):
                break
            offset = struct.unpack('<I', data[off:off+4])[0]
            target = offset  # 相对偏移

            # 检查目标位置的数据
            if target + 9 <= size:
                # 前9字节
                header9 = data[target:target+9]
                w = struct.unpack('<H', data[target:target+2])[0]
                h = struct.unpack('<H', data[target+2:target+4])[0]

                # 检查是否有意义
                flag = ""
                if w > 0 and h > 0 and w <= 320 and h <= 256:
                    flag = f"✓ {w}x{h}"
                elif w == 0 and h == 0:
                    flag = "全0"
                elif w <= 256 and h == 0:
                    flag = "可疑"
                else:
                    flag = f"异常 w={w} h={h}"

                print(f"  [{i:2d}] 偏移0x{target:04x} ({target:5d}): 前9字节={header9.hex()} {flag}")
            else:
                print(f"  [{i:2d}] 偏移0x{target:04x}: 越界")

        # 关键：检查offset=0的位置（第一个子项）
        print(f"\n=== 检查offset=0处的完整数据 ===")
        if len(data) >= 26:
            print(f"字节0-25: {data[0:26].hex()}")

        # 既然v9+9是数据指针，v9就是从offset指向的位置开始
        # 那v9的前9字节是什么？让我检查offset=0+9的位置
        print(f"\noffset=0+9处开始的数据:")
        if 9 + 64 <= size:
            print(f"字节9-72: {data[9:73].hex()}")

if __name__ == '__main__':
    main()