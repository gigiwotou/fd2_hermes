#!/usr/bin/env python3
"""
比较索引18和索引1的结构
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def main():
    with open(DAT_FILE, 'rb') as f:
        # 索引18
        start, size = read_index(f, 18)
        f.seek(start)
        data18 = f.read(min(size, 150))

        w18 = struct.unpack('<H', data18[0:2])[0]
        h18 = struct.unpack('<H', data18[2:4])[0]
        sub_count18 = struct.unpack('<H', data18[4:6])[0]

        print(f"索引18: {size} 字节")
        print(f"  width={w18}, height={h18}")
        print(f"  字节4-5 (sub_count?): {sub_count18}")
        print(f"  字节6-9: {struct.unpack('<I', data18[6:10])[0]}")
        print(f"  字节10-13: {struct.unpack('<I', data18[10:14])[0]}")

        print(f"\n索引18 前100字节:")
        for i in range(0, 100, 20):
            print(f"  {i:04x}: {data18[i:i+20].hex()}")

        # 索引1
        f.seek(0, 0)
        start, size = read_index(f, 1)
        f.seek(start)
        data1 = f.read(min(size, 150))

        w1 = struct.unpack('<H', data1[0:2])[0]
        h1 = struct.unpack('<H', data1[2:4])[0]
        sub_count1 = struct.unpack('<H', data1[4:6])[0]

        print(f"\n索引1: {size} 字节")
        print(f"  width={w1}, height={h1}")
        print(f"  字节4-5 (sub_count): {sub_count1}")

        # 索引1的offset表
        print(f"\n索引1 offset表:")
        for i in range(5):
            off = struct.unpack('<I', data1[6+i*4:10+i*4])[0]
            print(f"  [{i}]: 0x{off:x}")

        print(f"\n索引1 offset表后 (字节86+):")
        print(f"  {data1[86:106].hex()}")

        # 关键区别
        print("\n=== 关键区别 ===")
        print(f"索引18: sub_count=0, offset表为空, RLE数据从字节4开始")
        print(f"索引1: sub_count=20, offset表占86字节, RLE数据从字节86开始")

if __name__ == '__main__':
    main()