#!/usr/bin/env python3
"""
检查offset处的LMI1标记
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def main():
    with open(DAT_FILE, 'rb') as f:
        start, size = read_index(f, 18)
        f.seek(start)
        data = f.read(size)

        print("索引18 offset表分析:\n")
        print(f"{'Index':<6} {'Offset':<10} {'数据前8字节':<20} {'检查'}")
        print("-" * 60)

        for i in range(10):
            off = 4 + i * 4
            if off + 4 > len(data):
                break

            offset_val = struct.unpack('<I', data[off:off+4])[0]
            target = offset_val  # 相对偏移

            if target < size and target + 8 <= size:
                chunk = data[target:target+8]
                header = chunk.hex()

                # 检查LMI1
                is_lmi1 = chunk[:4] == b'LMI1'
                is_ll = chunk[:4] == b'LLLL'

                check = ""
                if is_lmi1:
                    frames = struct.unpack('<H', chunk[4:6])[0]
                    check = f"LMI1 {frames}帧"
                elif is_ll:
                    check = "LLLL嵌套"
                else:
                    w = struct.unpack('<H', chunk[0:2])[0]
                    h = struct.unpack('<H', chunk[2:4])[0]
                    if 8 <= w <= 64 and 8 <= h <= 64:
                        check = f"RLE {w}x{h}"
                    else:
                        check = f"未知 w={w} h={h}"
            else:
                header = "越界"
                check = "-"

            print(f"{i:<6} 0x{offset_val:04x} ({offset_val:<6}) {header:<20} {check}")

if __name__ == '__main__':
    main()