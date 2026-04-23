#!/usr/bin/env python3
"""
扫描FDOTHER所有索引，找出有有效RLE头的位置
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def check_data_at(data, offset):
    """检查offset处是否有有效的RLE头"""
    if offset + 4 > len(data):
        return None

    w = struct.unpack('<H', data[offset:offset+2])[0]
    h = struct.unpack('<H', data[offset+2:offset+4])[0]

    if w == 0 or h == 0 or w > 400 or h > 300:
        return None

    # 检查RLE数据是否看起来有效
    rle_data = data[offset+4:offset+24]
    # RLE数据通常有一些非零值
    nonzero_ratio = sum(1 for b in rle_data if b != 0) / len(rle_data)

    return (w, h, nonzero_ratio)

def main():
    with open(DAT_FILE, 'rb') as f:
        # 读取索引表
        for idx in range(50):
            start, size = read_index(f, idx)
            if size < 10:
                continue

            f.seek(start)
            data = f.read(min(size, 200))

            # 检查字节0处
            r0 = check_data_at(data, 0)

            # 检查字节4处（可能的RLE开始位置）
            r4 = check_data_at(data, 4)

            # 检查字节6处（offset表后的数据）
            r6 = check_data_at(data, 6)

            flag = ""
            if r0 and r0[2] > 0.3:
                flag = f"0:{r0[0]}x{r0[1]}"
            if r4 and r4[2] > 0.3:
                flag += f" 4:{r4[0]}x{r4[1]}"
            if r6 and r6[2] > 0.3:
                flag += f" 6:{r6[0]}x{r6[1]}"

            if flag:
                print(f"索引{idx:2d}: size={size:5d} {flag}")

            # 也检查一些特定位置的offset指向
            if size > 10 and idx in [0, 1, 9, 15, 18, 22, 32, 33]:
                sub_count = struct.unpack('<H', data[4:6])[0]
                print(f"       sub_count={sub_count}")
                # 如果sub_count>0，检查offset表
                if sub_count > 0 and size > 6 + sub_count * 4:
                    print(f"       offset表:")
                    for i in range(min(sub_count, 5)):
                        off = 6 + i * 4
                        if off + 4 <= len(data):
                            ov = struct.unpack('<I', data[off:off+4])[0]
                            # 检查offset处的数据
                            if ov < size and ov + 4 <= size:
                                w = struct.unpack('<H', data[ov:ov+2])[0]
                                h = struct.unpack('<H', data[ov+2:ov+4])[0]
                                print(f"         [{i}] 0x{ov:04x}: {w}x{h}")

if __name__ == '__main__':
    main()