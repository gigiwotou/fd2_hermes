#!/usr/bin/env python3
"""
详细追踪字节72处的RLE命令执行
"""
import struct

DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'

def read_index(file, index):
    file.seek(4 * index + 6)
    start, end = struct.unpack('<II', file.read(8))
    return start, end - start

def trace_rle(data, start_offset, width, height, screen_width=320):
    """追踪RLE解码过程"""
    if start_offset + 4 > len(data):
        print("数据不足")
        return None

    # 检查给定的width/height
    w = struct.unpack('<H', data[start_offset:start_offset+2])[0]
    h = struct.unpack('<H', data[start_offset+2:start_offset+4])[0]
    print(f"位置{start_offset}的头: width={w}, height={h}")
    print(f"实际参数: width={width}, height={height}")

    # 如果给定width!=头width，说明数据格式不同
    actual_w = width if width else w
    actual_h = height if height else h

    src = data[start_offset + 4:]
    src_idx = 0
    dst = bytearray()
    row_remain = actual_w
    v8 = screen_width - actual_w

    print(f"\n前20个命令:")
    x = 0
    cmd_count = 0

    h_remain = actual_h
    while h_remain > 0 and cmd_count < 50:
        c = row_remain
        while c > 0 and cmd_count < 50:
            if src_idx >= len(src):
                print(f"  src越界 at cmd {cmd_count}")
                return None

            value = src[src_idx]
            src_idx += 1

            count_1 = ((value * 4) & 0xFF) >> 2
            if count_1 == 0:
                count_1 = 1
            count_1 += 1

            bit7 = (value >> 7) & 1
            bit6 = (value >> 6) & 1

            cmd_type = ""
            detail = ""

            if not bit7:
                if not bit6:
                    cmd_type = "COPY"
                    detail = f"data=[{','.join(hex(src[src_idx+j]) for j in range(min(count_1,5)))}]"
                    if src_idx + count_1 <= len(src):
                        dst.extend(src[src_idx:src_idx + count_1])
                        src_idx += count_1
                else:
                    cmd_type = "FILL"
                    if src_idx < len(src):
                        byte = src[src_idx]
                        detail = f"byte=0x{byte:02x}"
                        src_idx += 1
                        dst.extend([byte] * count_1)
                c -= count_1
            else:
                if not bit6:
                    cmd_type = "SKIP"
                    detail = f"skip={count_1}"
                    dst.extend([0] * count_1)
                else:
                    cmd_type = "INTER"
                    if src_idx < len(src):
                        byte = src[src_idx]
                        detail = f"byte=0x{byte:02x}"
                        src_idx += 1
                        dst.extend([byte] * count_1)
                c -= count_1

            x += count_1
            cmd_count += 1
            print(f"  [{cmd_count}] 0x{value:02x} bit7={bit7} bit6={bit6} {cmd_type} count={count_1} {detail} (x={x})")

            if cmd_count >= 20:
                break

        if cmd_count >= 20:
            break

        dst.extend([0] * v8)
        h_remain -= 1
        print(f"  --- 行结束, 剩余{len(dst)}字节 ---")

    return bytes(dst[:100])  # 只返回前100字节用于检查

def main():
    with open(DAT_FILE, 'rb') as f:
        start, size = read_index(f, 18)
        f.seek(start)
        data = f.read(size)

        print("=== 追踪索引18从字节72的RLE解码 ===\n")
        trace_rle(data, 72, 10, 16, 320)

if __name__ == '__main__':
    main()