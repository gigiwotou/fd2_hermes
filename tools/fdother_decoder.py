#!/usr/bin/env python3
"""
FDOTHER.DAT 完整解码工具 v4.0

基于游戏反编译代码 sub_4E98D (0x4e98d) 的算法重写：
  - 逐行独立压缩
  - 4种操作: SKIP(≥0xC0), RLE(0x80-0xBF), INTERLEAVED(0x40-0x7F), COPY(0x00-0x3F)
  - 低6位 + 1 = 操作数
  - makeBMP:      直接逐像素读取
  - makeFaceBMP:  FaceBMP RLE (b>192 重复次数)
  - makeFontBMP:   16x16 字体解码
  - Offset表:     多种子资源索引

6-bit VGA 调色板 (768字节), 256色

使用方法:
  python fdother_decoder.py                          # 解码所有资源
  python fdother_decoder.py 10                       # 解码索引10
  python fdother_decoder.py 11 69 74                 # 解码多个索引
  python fdother_decoder.py --analyze                # 仅分析不输出图像
  python fdother_decoder.py --palette 76             # 用指定调色板索引解码
"""

import struct
import sys
import os
from PIL import Image

# ============================================================
# 配置
# ============================================================
DAT_FILE = '/home/yinming/fd2_dat/game/FDOTHER.DAT'
OUTPUT_DIR = '/home/yinming/fd2_hermes/decoded_v3'
PALETTE_DIR = '/home/yinming/FD2ResViewer/resources'

DAT_MAGIC = b'LLLLLL'
DAT_MAGIC_LEN = 6
PALETTE_COLORS = 256
PALETTE_BYTES = PALETTE_COLORS * 3  # 768

# 索引总数 (FDOTHER.DAT 有 104 个资源)
RESOURCE_COUNT = 104


# ============================================================
# 调色板
# ============================================================
class ColorPanel:
    """调色板类，6-bit VGA → 8-bit RGB 转换"""

    def __init__(self, palette_id=1, custom_data=None):
        self.colors = [(0, 0, 0)] * 256
        self.raw_6bit = bytearray(768)

        if custom_data is not None and len(custom_data) >= 768:
            self.raw_6bit = bytearray(custom_data[:768])
        else:
            # 从资源文件加载
            name_map = {1: 'colorPanel', 2: 'colornew2', 3: 'colornew'}
            fname = name_map.get(palette_id, 'colorPanel')
            fpath = os.path.join(PALETTE_DIR, fname)
            try:
                with open(fpath, 'rb') as f:
                    self.raw_6bit = bytearray(f.read()[:768])
            except FileNotFoundError:
                print(f"  警告: 调色板文件 {fpath} 未找到，使用默认灰度")
                self.raw_6bit = bytearray([i // 3 for i in range(768)])

        # 6-bit → 8-bit 转换
        for i in range(256):
            r6 = self.raw_6bit[i * 3] & 0x3F
            g6 = self.raw_6bit[i * 3 + 1] & 0x3F
            b6 = self.raw_6bit[i * 3 + 2] & 0x3F
            r8 = (r6 << 2) | (r6 >> 4)
            g8 = (g6 << 2) | (g6 >> 4)
            b8 = (b6 << 2) | (b6 >> 4)
            self.colors[i] = (r8, g8, b8)

    def this_color(self, index):
        if 0 <= index < 256:
            return self.colors[index]
        return (0, 0, 0)

    def get_rgb_array(self):
        """返回完整的 RGB 调色板数组 (256 * 3 bytes, 8-bit)"""
        result = bytearray(768)
        for i in range(256):
            r, g, b = self.colors[i]
            result[i * 3] = r
            result[i * 3 + 1] = g
            result[i * 3 + 2] = b
        return bytes(result)


# ============================================================
# DAT 文件加载
# ============================================================
class DatFile:
    """FD2 DAT 文件加载器"""

    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.data = f.read()
        self.file_size = len(self.data)

        # 验证 magic
        if self.data[:DAT_MAGIC_LEN] != DAT_MAGIC:
            raise ValueError(f"无效的 DAT 文件 magic: {self.data[:6]}")

        # 读取资源计数 (偏移6, 4字节 uint32)
        self.resource_count = struct.unpack('<I', self.data[6:10])[0]

        # 读取偏移表 (偏移6开始, 每个资源4字节 uint32)
        # 注意: FD2ResViewer 的 analysis() 方法: array[index] = data[6 + index*4]
        # 偏移表紧跟在6字节magic之后, count也在偏移表内(第一个4字节=offset[0])
        # 实际上: 位置6..9 = offset[0] (也就是资源0的起始偏移)
        #         位置10..13 = offset[1]
        # count 存储在偏移表之前，但从FD2ResViewer代码看，count = 422 实际上
        # 包含了自身在偏移表中的位置
        self.offsets = []
        for i in range(self.resource_count):
            off = 6 + i * 4
            if off + 4 <= self.file_size:
                self.offsets.append(struct.unpack('<I', self.data[off:off + 4])[0])
            else:
                self.offsets.append(0)

        # 构建资源块列表: (start, size)
        self.resources = []
        for i in range(self.resource_count):
            start = self.offsets[i]
            if i + 1 < self.resource_count:
                end = self.offsets[i + 1]
            else:
                end = self.file_size
            size = end - start if end > start else 0
            self.resources.append((start, size))

    def get_resource(self, index):
        """获取指定索引的资源数据"""
        if index < 0 or index >= self.resource_count:
            return None, 0
        start, size = self.resources[index]
        if start + size > self.file_size:
            return None, 0
        return self.data[start:start + size], size

    def get_resource_offset(self, index):
        """获取指定索引的资源在文件中的偏移"""
        if index < 0 or index >= self.resource_count:
            return 0, 0
        return self.resources[index]


# ============================================================
# 解码方法 - 基于 FD2ResViewer BMPMaker
# ============================================================

def makeBMP(file_data, start_offset, length, width, height, colorpanel):
    """
    直接逐像素读取 - 每个字节是调色板索引
    对应 FD2ResViewer BMPMaker.makeBMP
    """
    img = Image.new('RGB', (width, height), (0, 0, 0))
    pixels = img.load()

    x, y = 0, 0
    for i in range(length):
        if y >= height:
            break
        if x >= width:
            x = 0
            y += 1
            if y >= height:
                break

        pos = start_offset + i
        if pos < len(file_data):
            idx = file_data[pos]
            pixels[x, y] = colorpanel.this_color(idx)
        x += 1
        if x == width:
            x = 0
            y += 1

    return img


def makeFaceBMP(file_data, start_offset, length, colorpanel):
    """
    FaceBMP RLE 解码 - b > 192 表示重复次数, 否则是颜色值
    头部4字节: width(uint16) + height(uint16)
    对应 FD2ResViewer BMPMaker.makeFaceBMP
    """
    width = struct.unpack('<h', file_data[start_offset:start_offset + 2])[0]
    height = struct.unpack('<h', file_data[start_offset + 2:start_offset + 4])[0]

    if width <= 0 or height <= 0 or width > 1000 or height > 1000:
        return None

    img = Image.new('RGB', (width, height), (0, 0, 0))
    pixels = img.load()

    num2 = 1  # 重复次数，默认1
    flag = True
    x, y = 0, 0

    for pos in range(start_offset + 4, start_offset + length):
        if y >= height:
            break
        b = file_data[pos]

        if b > 192 and flag:
            num2 = b - 192
            flag = False
        else:
            flag = True
            for _ in range(num2):
                if y >= height:
                    break
                pixels[x, y] = colorpanel.this_color(b)
                x += 1
                if x == width:
                    x = 0
                    y += 1
            num2 = 1

    return img


# ============================================================
# sub_4E98D 图像解码 (游戏原版算法)
# ============================================================
# 反编译自 FD2.EXE 地址 0x4E98D
# 数据结构: [int16 width, int16 height] + 逐行压缩数据
# 4种控制字节操作:
#   >= 0xC0: SKIP    n = (b & 0x3F) + 1, dst跳过n字节
#   0x80-0xBF: RLE   n = (b & 0x3F) + 1, 读颜色索引, memset填充n次
#   0x40-0x7F: INT   n = (b & 0x3F) + 1, 读颜色索引, 隔1像素写n次
#   0x00-0x3F: COPY  n = (b & 0x3F) + 1, qmemcpy n字节原始数据

def sub_4E98D_transparent(data_ptr, dst_buf, dst_stride, colorpanel):
    """
    value_1 == -1 模式: 直接写颜色索引到目标缓冲区
    
    data_ptr: 指向 [width:int16, height:int16, compressed_data...]
    dst_buf:  目标字节数组 (颜色索引, 非RGB)
    dst_stride: 目标行宽
    colorpanel: 调色板 (用于最终RGB转换)
    
    返回: PIL Image 或 None
    """
    width = struct.unpack('<h', data_ptr[0:2])[0]
    height = struct.unpack('<h', data_ptr[2:4])[0]
    
    if width <= 0 or height <= 0 or width > 2000 or height > 2000:
        return None
    
    # 初始化目标行为黑色(索引0)
    row = bytearray(dst_stride)
    
    img = Image.new('RGB', (width, height), (0, 0, 0))
    src_pos = 4  # 跳过 [width, height] 头
    data_len = len(data_ptr)
    
    for y in range(height):
        row[:] = b'\x00' * dst_stride  # 每行重设
        dst_pos = 0
        count = width  # 本行剩余像素
        
        while count > 0 and src_pos < data_len:
            b = data_ptr[src_pos]
            src_pos += 1
            
            n = (b & 0x3F) + 1
            
            if b >= 0xC0:          # SKIP: 跳过n像素
                if dst_pos + n > dst_stride:
                    n = dst_stride - dst_pos
                dst_pos += n
                count -= n  # 注意: count跟踪图像宽度, dst_pos跟踪缓冲区位置
                
            elif b >= 0x80:        # RLE: 填充n个相同颜色
                if src_pos >= data_len:
                    break
                color = data_ptr[src_pos]
                src_pos += 1
                actual = min(n, dst_stride - dst_pos, count)
                row[dst_pos:dst_pos + actual] = bytes([color]) * actual
                dst_pos += actual
                count -= actual
                
            elif b >= 0x40:        # INTERLEAVED: 隔1像素写颜色
                if src_pos >= data_len:
                    break
                color = data_ptr[src_pos]
                src_pos += 1
                # 跳过 dst[0], 写 dst[1], 跳到 dst[2], 写 dst[3], ...
                for i in range(n):
                    dst_pos += 1  # 跳过1字节 (间隔)
                    if dst_pos >= dst_stride or count <= 0:
                        break
                    row[dst_pos] = color
                    dst_pos += 1  # 再前进1字节到下一个间隔位置
                    count -= 2    # 每个操作消费2个count (跳过的+写的)
                    if count <= 0:
                        break
                    
            else:                  # COPY: 复制原始字节
                actual = min(n, dst_stride - dst_pos, count)
                end = min(src_pos + actual, data_len)
                chunk = data_ptr[src_pos:end]
                row[dst_pos:dst_pos + len(chunk)] = chunk
                src_pos += len(chunk)
                dst_pos += len(chunk)
                count -= len(chunk)
        
        # 将索引转换为RGB并写入图像
        for x in range(width):
            color = colorpanel.this_color(row[x])
            img.putpixel((x, y), color)
    
    return img


def makeShapBMP(file_data, start_offset, length, width, height, colorpanel):
    """
    ShapBMP 解码 - 基于 sub_4E98D 逐行压缩算法
    数据头从 file_data[start_offset] 开始
    """
    if width <= 0 or height <= 0 or width > 2000 or height > 2000:
        return None
    
    data_ptr = file_data[start_offset:start_offset + length]
    return sub_4E98D_transparent(data_ptr, None, width, colorpanel)


def makeBgBMP(file_data, start_offset, length, colorpanel):
    """
    背景图像解码 - 4字节宽高头 + sub_4E98D 逐行压缩
    头格式: [int16 width, int16 height]
    """
    width = struct.unpack('<h', file_data[start_offset:start_offset + 2])[0]
    height = struct.unpack('<h', file_data[start_offset + 2:start_offset + 4])[0]
    
    if width <= 0 or height <= 0 or width > 1000 or height > 1000:
        return None
    
    data_ptr = file_data[start_offset:start_offset + length]
    return sub_4E98D_transparent(data_ptr, None, width, colorpanel)


def makeFightBMP(file_data, start_offset, length, colorpanel):
    """
    战斗图像解码 - 宽高在 offset+9/+11 + sub_4E98D 逐行压缩
    注意: 这里数据在start_offset处就开始了
    """
    width = struct.unpack('<h', file_data[start_offset + 9:start_offset + 11])[0]
    height = struct.unpack('<h', file_data[start_offset + 11:start_offset + 13])[0]
    
    width = max(1, min(width, 1000))
    height = max(1, min(height, 1000))
    
    # 数据从 start_offset+13 开始, 但头部的宽度高度可能不同
    data_ptr = file_data[start_offset:start_offset + length]
    # 构造sub_4E98D需要的数据格式: [w,h, data from +13]
    header = struct.pack('<hh', width, height)
    fake_data = header + data_ptr[13:13 + (length - 13)]
    return sub_4E98D_transparent(fake_data, None, width, colorpanel)


def makeFontBMP(file_data, start_offset, length):
    """
    字体图像解码 - 每2字节包含一个像素位数据
    需要 SingleBitBMPHeader 资源文件
    对应 FD2ResViewer BMPMaker.makeFontBMP
    """
    # 加载 BMP 头
    header_path = os.path.join(PALETTE_DIR, 'SingleBitBMPHeader')
    try:
        with open(header_path, 'rb') as f:
            bmp_header = bytearray(f.read())
    except FileNotFoundError:
        print("  警告: SingleBitBMPHeader 未找到，使用默认")
        bmp_header = bytearray(62)

    # 构造 1-bit 位图数据
    bmp_data = bytearray(64)
    num = length - 1
    num2 = 0
    while num2 <= num:
        idx = 60 - num2 * 2
        if idx >= 0 and idx + 1 < 64:
            if start_offset + num2 < len(file_data):
                bmp_data[idx] = file_data[start_offset + num2]
            if start_offset + num2 + 1 < len(file_data):
                bmp_data[idx + 1] = file_data[start_offset + num2 + 1]
            bmp_data[idx + 2] = 0
            bmp_data[idx + 3] = 0
        num2 += 2

    # 组合 BMP
    full_bmp = bytearray(bmp_header)
    full_bmp.extend(bmp_data)

    try:
        from io import BytesIO
        stream = BytesIO(bytes(full_bmp))
        img = Image.open(stream)
        return img
    except Exception as e:
        print(f"  字体BMP解析失败: {e}")
        return None


# ============================================================
# 子资源索引解析
# ============================================================
def parse_subs_offsets_type1(dat, index):
    """
    索引1, 14: 子图形指针表
    头部: sWidth(2) + sHeight(2) + num44(2) + offset表(num44 * 4字节)
    """
    res_data, res_size = dat.get_resource(index)
    if not res_data or res_size < 6:
        return [], 0, 0

    sWidth = struct.unpack('<h', res_data[0:2])[0]
    sHeight = struct.unpack('<h', res_data[2:4])[0]
    num44 = struct.unpack('<h', res_data[4:6])[0]

    if num44 <= 0 or num44 > 10000:
        return [], sWidth, sHeight

    offsets = []
    for i in range(num44):
        pos = 6 + i * 4
        if pos + 4 <= res_size:
            off = struct.unpack('<I', res_data[pos:pos + 4])[0]
            offsets.append(off)

    # 构建子资源块
    subs = []
    for i in range(len(offsets)):
        start = offsets[i]
        if i + 1 < len(offsets):
            end = offsets[i + 1]
        else:
            end = res_size
        size = end - start if end > start else 0
        subs.append((start, size))

    return subs, sWidth, sHeight


def parse_subs_offsets_type2(dat, index):
    """
    索引2: 纯 offset 表
    第一个 uint32 / 4 = 子资源数, 后续是 offset 数组
    """
    res_data, res_size = dat.get_resource(index)
    if not res_data or res_size < 4:
        return []

    num34 = struct.unpack('<I', res_data[0:4])[0] // 4
    if num34 <= 0 or num34 > 10000:
        return []

    offsets = []
    for i in range(num34):
        pos = i * 4
        if pos + 4 <= res_size:
            off = struct.unpack('<I', res_data[pos:pos + 4])[0]
            offsets.append(off)

    subs = []
    for i in range(len(offsets)):
        start = offsets[i]
        if i + 1 < len(offsets):
            end = offsets[i + 1]
        else:
            end = res_size
        size = end - start if end > start else 0
        subs.append((start, size))

    return subs


def parse_subs_fixed_blocks(dat, index, block_size=32):
    """
    索引4: 固定32字节分块
    """
    res_data, res_size = dat.get_resource(index)
    if not res_data or res_size == 0:
        return []

    count = res_size // block_size
    subs = []
    for i in range(count):
        subs.append((i * block_size, block_size))
    return subs


def parse_subs_offsets_type5(dat, index):
    """
    索引5, 6, 9, 96: offset表从 startOffset+4 读取 num4, 然后读取 offset 数组
    offset 值是相对于资源起始的偏移
    """
    res_data, res_size = dat.get_resource(index)
    if not res_data or res_size < 6:
        return []

    num4 = struct.unpack('<h', res_data[4:6])[0]
    if num4 <= 0 or num4 > 10000:
        return []

    offsets = []
    for i in range(num4):
        pos = 6 + i * 4
        if pos + 4 <= res_size:
            off = struct.unpack('<I', res_data[pos:pos + 4])[0]
            offsets.append(off)

    subs = []
    for i in range(len(offsets)):
        start = offsets[i]
        if i + 1 < len(offsets):
            end = offsets[i + 1]
        else:
            end = res_size
        size = end - start if end > start else 0
        subs.append((start, size))

    return subs


def parse_subs_offsets_type7(dat, index):
    """
    索引7, 12, 13, 63: 从 offset+6 读取 short_value,
    num25 = round((short_value - 6) / 4.0 - 1.0), 然后读取 offset 数组
    """
    res_data, res_size = dat.get_resource(index)
    if not res_data or res_size < 8:
        return []

    short_value = struct.unpack('<h', res_data[6:8])[0]
    num25 = int(round((short_value - 6) / 4.0 - 1.0))
    num25 = max(0, num25)

    if num25 > 10000:
        return []

    offsets = []
    for i in range(num25):
        pos = 6 + i * 4
        if pos + 4 <= res_size:
            off = struct.unpack('<I', res_data[pos:pos + 4])[0]
            offsets.append(off)

    subs = []
    for i in range(len(offsets)):
        start = offsets[i]
        if i + 1 < len(offsets):
            end = offsets[i + 1]
        else:
            end = res_size
        size = end - start if end > start else 0
        subs.append((start, size))

    return subs


def parse_subs_offsets_type79(dat, index):
    """
    索引79: 从 offset+2 开始, num4 从 +4位置读, offset表从 +6+4*num4 开始
    """
    res_data, res_size = dat.get_resource(index)
    if not res_data or res_size < 10:
        return []

    num3_offset = 2
    num4 = struct.unpack('<h', res_data[num3_offset:num3_offset + 2])[0]
    if num4 <= 0 or num4 > 10000:
        return []

    offsets = []
    for i in range(num4):
        pos = num3_offset + 6 + i * 4
        if pos + 4 <= res_size:
            off = struct.unpack('<I', res_data[pos:pos + 4])[0]
            offsets.append(off)

    subs = []
    for i in range(len(offsets)):
        start = offsets[i]
        if i + 1 < len(offsets):
            end = offsets[i + 1]
        else:
            end = res_size
        size = end - start if end > start else 0
        subs.append((start, size))

    return subs


# ============================================================
# 主解码器 - 资源分类与调度
# ============================================================
class FdOtherDecoder:
    """FDOTHER.DAT 完整解码器"""

    def __init__(self, dat_path=DAT_FILE):
        self.dat = DatFile(dat_path)
        self.colorpanel1 = ColorPanel(1)  # 默认灰色调色板
        self.colorpanel2 = ColorPanel(2)  # 蓝色调色板 (用于索引74,75等)
        self.colorpanel3 = ColorPanel(3)  # 红色调色板
        self.output_dir = OUTPUT_DIR

        # 尝试从 FDOTHER 自身提取调色板
        self._load_palettes_from_dat()

    def _load_palettes_from_dat(self):
        """从 FDOTHER.DAT 中提取调色板资源"""
        # FDOTHER 中的调色板索引: 76, 99, 101 等 (768字节资源)
        for idx in [76, 99, 101]:
            res_data, res_size = self.dat.get_resource(idx)
            if res_data and res_size == PALETTE_BYTES:
                pal = ColorPanel(custom_data=res_data)
                if idx == 76:
                    self.colorpanel_idx76 = pal
                elif idx == 99:
                    self.colorpanel_idx99 = pal
                elif idx == 101:
                    self.colorpanel_idx101 = pal

    def _get_colorpanel(self, index):
        """根据资源索引选择合适的调色板"""
        # 索引74,75 用调色板2 (colornew2)
        if index in (74, 75):
            return self.colorpanel2
        # 其余用默认调色板1
        return self.colorpanel1

    def classify_resource(self, index):
        """分类资源类型，返回 (type, info)"""
        res_data, res_size = self.dat.get_resource(index)
        if not res_data or res_size == 0:
            return 'empty', {}

        info = {'size': res_size}

        # 检查是否是调色板
        if res_size == PALETTE_BYTES:
            return 'palette', info

        # 检查 LLLLLL 嵌套 DAT
        if res_data[:DAT_MAGIC_LEN] == DAT_MAGIC:
            inner_count = struct.unpack('<I', res_data[6:10])[0]
            info['inner_count'] = inner_count
            return 'nested_dat', info

        # 检查 LMI1 类型
        if res_data[:4] == b'LMI1':
            return 'lmi1', info

        # 检查宽高头
        if res_size >= 4:
            w = struct.unpack('<H', res_data[0:2])[0]
            h = struct.unpack('<H', res_data[2:4])[0]
            if 0 < w <= 640 and 0 < h <= 480:
                info['width'] = w
                info['height'] = h

        # 根据 FD2ResViewer 的索引分类表判断
        shap_indices = {11, 16, 17, 46, 47, 56, 59, 60, 61, 62,
                        69, 70, 71, 72, 73, 74, 75, 97, 98, 100}
        face_indices = {10, 15}

        if index in shap_indices:
            return 'shap', info
        if index in face_indices:
            return 'face', info
        if index == 4:
            return 'font', info
        if index == 55:
            return 'direct_bmp', info
        if index in (1, 14):
            return 'sub_offsets_1', info
        if index == 2:
            return 'sub_offsets_2', info
        if index in (5, 6, 9, 96):
            return 'sub_offsets_5', info
        if index in (7, 12, 13, 63):
            return 'sub_offsets_7', info
        if index == 79:
            return 'sub_offsets_79', info

        # 通用判断: 有合法宽高头的是 RLE 图像
        if 'width' in info and 'height' in info:
            return 'rle_image', info

        return 'raw', info

    def decode_resource(self, index, use_palette=None):
        """
        解码单个资源，返回 (images_list, status)
        images_list: [(Image, name), ...]
        status: 描述字符串
        """
        res_data, res_size = self.dat.get_resource(index)
        if not res_data or res_size == 0:
            return [], '空资源'

        res_type, info = self.classify_resource(index)
        cp = use_palette or self._get_colorpanel(index)

        if res_type == 'palette':
            # 调色板资源 - 生成调色板预览图
            pal = ColorPanel(custom_data=res_data)
            img = self._render_palette_preview(pal)
            return [(img, f'idx_{index:03d}_palette')], f'调色板 ({res_size}B)'

        if res_type == 'face':
            img = makeFaceBMP(self.dat.data,
                             self.dat.resources[index][0], res_size, cp)
            if img:
                return [(img, f'idx_{index:03d}_face')], f'FaceBMP {img.size[0]}x{img.size[1]}'
            return [], 'FaceBMP 解码失败'

        if res_type == 'shap':
            w = info.get('width', 0)
            h = info.get('height', 0)
            if w <= 0 or h <= 0:
                if res_size >= 4:
                    w = struct.unpack('<H', res_data[0:2])[0]
                    h = struct.unpack('<H', res_data[2:4])[0]
            if w <= 0 or h <= 0:
                return [], f'ShapBMP 无效尺寸 {w}x{h}'
            img = makeShapBMP(self.dat.data,
                              self.dat.resources[index][0], res_size,
                              w, h, cp)
            if img:
                return [(img, f'idx_{index:03d}_shap')], f'ShapBMP {w}x{h}'
            return [], 'ShapBMP 解码失败'

        if res_type == 'font':
            subs = parse_subs_fixed_blocks(self.dat, index)
            images = []
            for i, (sub_start, sub_size) in enumerate(subs):
                abs_start = self.dat.resources[index][0] + sub_start
                img = makeFontBMP(self.dat.data, abs_start, sub_size)
                if img:
                    images.append((img, f'idx_{index:03d}_font_{i:03d}'))
            return images, f'Font {len(images)} 个字形'

        if res_type == 'direct_bmp':
            w = info.get('width', 0)
            h = info.get('height', 0)
            if w > 0 and h > 0:
                img = makeBMP(self.dat.data,
                              self.dat.resources[index][0] + 4, res_size - 4,
                              w, h, cp)
                if img:
                    return [(img, f'idx_{index:03d}_bmp')], f'BMP {w}x{h}'
            return [], 'BMP 解码失败'

        if res_type == 'sub_offsets_1':
            return self._decode_sub_offsets1(index, cp)

        if res_type == 'sub_offsets_2':
            return self._decode_sub_offsets2(index, cp)

        if res_type == 'sub_offsets_5':
            return self._decode_sub_offsets5(index, cp)

        if res_type == 'sub_offsets_7':
            return self._decode_sub_offsets7(index, cp)

        if res_type == 'sub_offsets_79':
            return self._decode_sub_offsets79(index, cp)

        if res_type == 'nested_dat':
            inner_count = info.get('inner_count', 0)
            return self._decode_nested_dat(index, cp)

        if res_type == 'lmi1':
            return [], 'LMI1 类型 (需特殊处理)'

        if res_type == 'rle_image':
            w = info.get('width', 0)
            h = info.get('height', 0)
            # 尝试 ShapBMP 解码 (最常用的格式)
            img = makeShapBMP(self.dat.data,
                              self.dat.resources[index][0], res_size,
                              w, h, cp)
            if img and self._check_image_not_empty(img):
                return [(img, f'idx_{index:03d}_shap')], f'ShapBMP {w}x{h}'

            # 尝试 FaceBMP 解码
            img = makeFaceBMP(self.dat.data,
                              self.dat.resources[index][0], res_size, cp)
            if img and self._check_image_not_empty(img):
                return [(img, f'idx_{index:03d}_face')], f'FaceBMP {img.size[0]}x{img.size[1]}'

            # 尝试直接像素
            img = makeBMP(self.dat.data,
                          self.dat.resources[index][0] + 4, res_size - 4,
                          w, h, cp)
            if img and self._check_image_not_empty(img):
                return [(img, f'idx_{index:03d}_bmp')], f'BMP {w}x{h}'

            return [], f'RLE图像 {w}x{h} (解码失败)'

        if res_type == 'raw':
            # 尝试 dump 前64字节
            hex_str = res_data[:64].hex()
            return [], f'原始数据 ({res_size}B) {hex_str[:40]}...'

        return [], f'未知类型: {res_type}'

    def _check_image_not_empty(self, img):
        """检查图像是否不全黑"""
        if img is None:
            return False
        # 采样检查
        w, h = img.size
        if w == 0 or h == 0:
            return False
        for y in range(0, h, max(1, h // 10)):
            for x in range(0, w, max(1, w // 10)):
                if img.getpixel((x, y)) != (0, 0, 0):
                    return True
        return False

    def _render_palette_preview(self, colorpanel, cols=16, rows=16, cell_size=8):
        """渲染调色板预览图"""
        w = cols * cell_size
        h = rows * cell_size
        img = Image.new('RGB', (w, h), (0, 0, 0))
        pixels = img.load()
        for i in range(256):
            row = i // cols
            col = i % cols
            color = colorpanel.this_color(i)
            for dy in range(cell_size):
                for dx in range(cell_size):
                    px = col * cell_size + dx
                    py = row * cell_size + dy
                    if px < w and py < h:
                        pixels[px, py] = color
        return img

    def _decode_sub_offsets1(self, index, cp):
        """解码索引1, 14的子资源"""
        subs, sWidth, sHeight = parse_subs_offsets_type1(self.dat, index)
        if not subs:
            return [], '子资源解析失败'

        images = []
        res_abs_start = self.dat.resources[index][0]

        for i, (sub_start, sub_size) in enumerate(subs):
            abs_start = res_abs_start + sub_start
            img = makeShapBMP(self.dat.data, abs_start, sub_size,
                              sWidth, sHeight, cp)
            if img:
                images.append((img, f'idx_{index:03d}_sub_{i:03d}'))

        return images, f'子资源 {len(images)}/{len(subs)} 解码成功 (ShapBMP {sWidth}x{sHeight})'

    def _decode_sub_offsets2(self, index, cp):
        """解码索引2的子资源"""
        subs = parse_subs_offsets_type2(self.dat, index)
        if not subs:
            return [], '子资源解析失败'

        images = []
        res_abs_start = self.dat.resources[index][0]
        res_data, res_size = self.dat.get_resource(index)

        for i, (sub_start, sub_size) in enumerate(subs):
            abs_start = res_abs_start + sub_start
            # 每个子资源有宽高头
            if sub_size >= 4 and abs_start + 4 <= len(self.dat.data):
                w = struct.unpack('<h', self.dat.data[abs_start:abs_start + 2])[0]
                h = struct.unpack('<h', self.dat.data[abs_start + 2:abs_start + 4])[0]
                if 0 < w <= 640 and 0 < h <= 480:
                    img = makeBMP(self.dat.data, abs_start + 4, sub_size - 4,
                                  w, h, cp)
                    if img:
                        images.append((img, f'idx_{index:03d}_sub_{i:03d}'))

        return images, f'子资源 {len(images)}/{len(subs)} 解码成功 (BMP)'

    def _decode_sub_offsets5(self, index, cp):
        """解码索引5, 6, 9, 96的子资源"""
        subs = parse_subs_offsets_type5(self.dat, index)
        if not subs:
            return [], '子资源解析失败'

        images = []
        res_abs_start = self.dat.resources[index][0]
        res_data, res_size = self.dat.get_resource(index)

        for i, (sub_start, sub_size) in enumerate(subs):
            abs_start = res_abs_start + sub_start
            if sub_size < 4 or abs_start + 4 > len(self.dat.data):
                continue

            w = struct.unpack('<h', self.dat.data[abs_start:abs_start + 2])[0]
            h = struct.unpack('<h', self.dat.data[abs_start + 2:abs_start + 4])[0]

            if index == 5:
                # 索引5 的子资源有复杂的分段处理
                img = self._decode_sub5_item(i, abs_start, sub_size, w, h, cp, index)
            elif index in (1, 96):
                img = makeShapBMP(self.dat.data, abs_start, sub_size,
                                  24, 24, cp)
            else:
                if 0 < w <= 640 and 0 < h <= 480:
                    img = makeBMP(self.dat.data, abs_start + 4, sub_size - 4,
                                  w, h, cp)
                else:
                    img = None

            if img:
                images.append((img, f'idx_{index:03d}_sub_{i:03d}'))

        return images, f'子资源 {len(images)}/{len(subs)} 解码成功'

    def _decode_sub5_item(self, sub_idx, abs_start, sub_size, w, h, cp, parent_index):
        """索引5的子资源分段解码逻辑 (来自 FD2ResViewer analysis_subs_image)"""
        if sub_idx < 20:
            # makeBMP
            if 0 < w <= 640 and 0 < h <= 480:
                return makeBMP(self.dat.data, abs_start + 4, sub_size - 4,
                               w, h, cp)
        elif sub_idx < 23:
            # makeFaceBMP
            return makeFaceBMP(self.dat.data, abs_start, sub_size, cp)
        elif sub_idx < 31:
            # makeBMP
            if 0 < w <= 640 and 0 < h <= 480:
                return makeBMP(self.dat.data, abs_start + 4, sub_size - 4,
                               w, h, cp)
        elif sub_idx < 53:
            # makeShapBMP
            if 0 < w <= 640 and 0 < h <= 480:
                return makeShapBMP(self.dat.data, abs_start + 4, sub_size - 4,
                                   w, h, cp)
        elif sub_idx < 64 and sub_idx != 59:
            # makeBMP
            if 0 < w <= 640 and 0 < h <= 480:
                return makeBMP(self.dat.data, abs_start + 4, sub_size - 4,
                               w, h, cp)
        elif sub_idx != 59:
            if sub_idx < 119 and sub_idx != 93:
                # makeFaceBMP
                return makeFaceBMP(self.dat.data, abs_start, sub_size, cp)

        return None

    def _decode_sub_offsets7(self, index, cp):
        """解码索引7, 12, 13, 63的子资源"""
        subs = parse_subs_offsets_type7(self.dat, index)
        if not subs:
            return [], '子资源解析失败'

        images = []
        res_abs_start = self.dat.resources[index][0]

        for i, (sub_start, sub_size) in enumerate(subs):
            abs_start = res_abs_start + sub_start
            if sub_size >= 4 and abs_start + 4 <= len(self.dat.data):
                w = struct.unpack('<h', self.dat.data[abs_start:abs_start + 2])[0]
                h = struct.unpack('<h', self.dat.data[abs_start + 2:abs_start + 4])[0]
                if 0 < w <= 640 and 0 < h <= 480:
                    img = makeFaceBMP(self.dat.data, abs_start, sub_size, cp)
                    if img and self._check_image_not_empty(img):
                        images.append((img, f'idx_{index:03d}_sub_{i:03d}'))
                        continue
                    # 尝试 ShapBMP
                    img = makeShapBMP(self.dat.data, abs_start, sub_size,
                                      w, h, cp)
                    if img and self._check_image_not_empty(img):
                        images.append((img, f'idx_{index:03d}_sub_{i:03d}'))

        return images, f'子资源 {len(images)}/{len(subs)} 解码成功'

    def _decode_sub_offsets79(self, index, cp):
        """解码索引79的子资源"""
        subs = parse_subs_offsets_type79(self.dat, index)
        if not subs:
            return [], '子资源解析失败'

        images = []
        res_abs_start = self.dat.resources[index][0]

        for i, (sub_start, sub_size) in enumerate(subs):
            abs_start = res_abs_start + sub_start
            if sub_size >= 4 and abs_start + 4 <= len(self.dat.data):
                w = struct.unpack('<h', self.dat.data[abs_start:abs_start + 2])[0]
                h = struct.unpack('<h', self.dat.data[abs_start + 2:abs_start + 4])[0]
                if 0 < w <= 640 and 0 < h <= 480:
                    img = makeBMP(self.dat.data, abs_start + 4, sub_size - 4,
                                  w, h, cp)
                    if img:
                        images.append((img, f'idx_{index:03d}_sub_{i:03d}'))

        return images, f'子资源 {len(images)}/{len(subs)} 解码成功'

    def decode_all(self, indices=None):
        """解码所有或指定资源"""
        os.makedirs(self.output_dir, exist_ok=True)

        if indices is None:
            indices = list(range(min(self.dat.resource_count, RESOURCE_COUNT)))

        total_images = 0
        results = []

        for idx in indices:
            images, status = self.decode_resource(idx)
            results.append((idx, status, len(images)))

            for img, name in images:
                path = os.path.join(self.output_dir, f'{name}.png')
                img.save(path)
                total_images += 1

            # 进度输出
            img_count = len(images)
            if img_count > 0:
                print(f"  索引 {idx:3d}: {status} → {img_count} 张图片")
            else:
                print(f"  索引 {idx:3d}: {status}")

        print(f"\n总计: {total_images} 张图片 → {self.output_dir}")
        return results

    def analyze(self):
        """分析所有资源类型，不输出图像"""
        print(f"FDOTHER.DAT 分析: {self.dat.resource_count} 个资源\n")
        print(f"{'索引':>4} {'大小':>10} {'类型':<15} {'详情'}")
        print("-" * 60)

        for idx in range(min(self.dat.resource_count, RESOURCE_COUNT)):
            res_data, res_size = self.dat.get_resource(idx)
            if not res_data:
                print(f"{idx:4d} {'N/A':>10} {'empty':<15}")
                continue

            res_type, info = self.classify_resource(idx)
            detail = ""
            if 'width' in info and 'height' in info:
                detail = f"{info['width']}x{info['height']}"
            elif 'inner_count' in info:
                detail = f"内部{info['inner_count']}个资源"

            print(f"{idx:4d} {res_size:>10} {res_type:<15} {detail}")


# ============================================================
# 主程序入口
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='FDOTHER.DAT 解码工具 v3.0')
    parser.add_argument('indices', nargs='*', type=int, help='要解码的索引列表')
    parser.add_argument('--analyze', action='store_true', help='仅分析不输出图像')
    parser.add_argument('--dat', default=DAT_FILE, help='DAT文件路径')
    parser.add_argument('--output', default=OUTPUT_DIR, help='输出目录')
    parser.add_argument('--palette', type=int, default=None,
                        help='使用FDOTHER.DAT中的调色板索引 (如76, 99, 101)')
    args = parser.parse_args()

    decoder = FdOtherDecoder(args.dat)
    decoder.output_dir = args.output

    if args.analyze:
        decoder.analyze()
        return

    # 调色板选择
    custom_palette = None
    if args.palette is not None:
        pal_data, pal_size = decoder.dat.get_resource(args.palette)
        if pal_data and pal_size == PALETTE_BYTES:
            custom_palette = ColorPanel(custom_data=pal_data)
            print(f"使用调色板索引 {args.palette}")
        else:
            print(f"警告: 索引 {args.palette} 不是有效的调色板")

    if args.indices:
        # 解码指定索引
        for idx in args.indices:
            images, status = decoder.decode_resource(idx, use_palette=custom_palette)
            os.makedirs(args.output, exist_ok=True)
            for img, name in images:
                path = os.path.join(args.output, f'{name}.png')
                img.save(path)
            img_count = len(images)
            if img_count > 0:
                print(f"索引 {idx}: {status} → {img_count} 张图片")
            else:
                print(f"索引 {idx}: {status}")
    else:
        # 解码所有
        decoder.decode_all()


if __name__ == '__main__':
    main()
