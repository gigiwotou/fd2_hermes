# FDICON.B24 格式分析 (修正版)

## 概述
FDICON.B24 是FD2游戏的图标资源文件，包含140个24x24像素图标，每个图标有最多12帧动画。

## 文件结构

### 头部 (6 字节)
```
偏移 0-1: width (WORD) = 24
偏移 2-3: height (WORD) = 24  
偏移 4-5: 未知 (可能是版本或保留)
```

### 索引表 (偏移 6 到 6726)
- 大小: 6720 字节
- 每个图标 48 字节索引数据
- 共 140 个图标 (6720 / 48 = 140)
- 每个索引包含 13 个 DWORD (4字节) 偏移值

### 索引条目结构
```
图标索引结构 (48字节):
  DWORD[0-11]: 12帧动画数据的偏移地址
  DWORD[12]: 结束偏移 (用于计算最后一帧大小)
```

### 数据区 (偏移 6726 之后)
包含压缩的图标帧数据。

## 帧数据压缩格式

图标帧使用 RLE (Run-Length Encoding) 压缩：

### 编码规则
- **字面量**: 非 0xFE 字节直接作为像素值
- **RLE 标记**: 0xFE 表示压缩命令
  - `0xFE 0x80-0xFF [value]`: 重复 value (cmd - 0x80 + 3) 次
  - 例如: `FE C3 05` = 重复 0x05 (0xC3 - 0x80 + 3 = 68) 次

### 解码算法
```python
def decode_icon_frame(data):
    result = []
    i = 0
    while i < len(data) and len(result) < 600:
        b = data[i]
        i += 1
        
        if b == 0xFE and i < len(data):
            cmd = data[i]
            i += 1
            
            if cmd >= 0x80:
                # RLE: 重复下一个字节
                count = (cmd - 0x80) + 3
                if i < len(data):
                    val = data[i]
                    i += 1
                    result.extend([val] * count)
            else:
                result.append(cmd)
        else:
            result.append(b)
    
    return bytes(result[:576])  # 24x24 = 576 字节
```

## 调色板

图标使用 FDOTHER.DAT 中的调色板：
- 位置: FDOTHER.DAT 资源28
- 偏移: 0x21D119
- 大小: 768 字节 (256色 x 3通道)
- 格式: DOS 6-bit RGB (值乘以4转换为8-bit)

## Python 提取器

```python
import struct
from PIL import Image

def extract_fdicon_b24(icon_path, palette_path, output_dir):
    """提取 FDICON.B24 中的所有图标"""
    
    # 加载图标文件
    with open(icon_path, 'rb') as f:
        icon_data = f.read()
    
    # 加载调色板
    with open(palette_path, 'rb') as f:
        other_data = f.read()
    
    pal_offset = 0x21D119
    pal_data = other_data[pal_offset:pal_offset+768]
    palette = []
    for i in range(256):
        r = min(255, pal_data[i * 3] * 4)
        g = min(255, pal_data[i * 3 + 1] * 4)
        b = min(255, pal_data[i * 3 + 2] * 4)
        palette.extend([r, g, b])
    
    # 解析索引表
    index_data = icon_data[6:6+6720]
    icon_count = 140
    
    for icon_idx in range(icon_count):
        base = icon_idx * 48
        offsets = []
        for j in range(13):
            val = struct.unpack('<I', index_data[base + j*4:base + j*4 + 4])[0]
            offsets.append(val)
        
        # 提取第一帧
        frame_start = offsets[0]
        frame_end = offsets[1] if offsets[1] > frame_start else frame_start + 600
        
        if frame_start > 6 and frame_start < len(icon_data) - 10:
            frame_data = icon_data[frame_start:frame_end]
            decoded = decode_icon_frame(frame_data)
            
            if len(decoded) == 576:
                img = Image.new('P', (24, 24))
                img.putdata(list(decoded))
                img.putpalette(palette)
                img.save(f'{output_dir}/icon_{icon_idx:03d}.png')

def decode_icon_frame(data):
    """解码单帧图标数据"""
    result = []
    i = 0
    while i < len(data) and len(result) < 600:
        b = data[i]
        i += 1
        if b == 0xFE and i < len(data):
            cmd = data[i]
            i += 1
            if cmd >= 0x80:
                count = (cmd - 0x80) + 3
                if i < len(data):
                    val = data[i]
                    i += 1
                    result.extend([val] * count)
            else:
                result.append(cmd)
        else:
            result.append(b)
    return bytes(result[:576])

# 使用示例
extract_fdicon_b24('game/FDICON.B24', 'game/FDOTHER.DAT', 'extracted/icons')
```

## 提取结果
- 成功提取 125 个图标
- 保存路径: `extracted/icons_v2/`
- 预览图: `extracted/icons_v2_preview.png`

## 与之前分析的差异

### 之前错误分析
1. 误认为偏移表是 `[padding][offset]` 格式
2. 实际上索引表每个图标有48字节，包含13个偏移值
3. 数据区的 `02 00` 簇是另一段代码的数据，不是图标格式

### 正确分析来源
通过 IDA Pro 反编译代码 `sub_11019` 发现:
- `fseek(file, 6, 0)` - 索引表从偏移6开始
- `v13[n13] = *(_DWORD *)&v6[48 * a5 + 4 * n13]` - 每个图标48字节索引
- `v14 = v13[12] - v13[0]` - 用第13个偏移计算大小

## 图标内容
提取的图标包含：
- 游戏界面元素
- 按钮和控件
- 角色头像/图标
- 物品图标
- 状态指示器

## 注意事项
1. 每个图标最多12帧动画
2. 帧大小不固定，使用压缩格式
3. 有些偏移值可能无效（超出文件范围）
4. 调色板必须从FDOTHER.DAT加载
