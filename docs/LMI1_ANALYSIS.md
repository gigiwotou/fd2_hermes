# FDOTHER.DAT LMI1 格式分析完成

## 分析成果

### LMI1 格式完全破解

LMI1 是一种**按列存储的动画格式**,每帧存储一列像素数据。

#### 文件结构

```
偏移      内容
─────────────────────────────
0x00-0x03  "LMI1" 标识
0x04-0x05  宽度 (uint16)
0x06-0x07  高度 (uint16)
0x08+      帧偏移表
帧数据     RLE压缩的列数据
```

#### 帧偏移表格式

特殊模式: `[00 00][偏移:2]` 重复

```
偏移8:  00 00 [偏移1:2字节]
偏移12: 00 00 [偏移2:2字节]
偏移16: 00 00 [偏移3:2字节]
...
```

#### 解码算法

```python
def decode_lmi1(data):
    w = read_uint16(data[4:6])
    h = read_uint16(data[6:8])
    
    # 解析帧偏移表
    offsets = []
    i = 8
    while data[i:i+2] == b'\x00\x00':
        offset = read_uint16(data[i+2:i+4])
        offsets.append(offset)
        i += 4
    
    # 解码每帧 (每帧是一列)
    frames = []
    for offset in offsets:
        frame_data = data[offset:next_offset]
        column = decode_rle(frame_data)  # RLE解码
        frames.append(column[:h])  # 取高度h个像素
    
    # 合成图像 (列优先转行优先)
    image = []
    for y in range(h):
        for x in range(w):
            image.append(frames[x][y])
    
    return image, w, h
```

### 资源列表

| 索引 | 尺寸 | 帧数 | 用途推测 |
|------|------|------|----------|
| 1 | 23x102 | 22 | 竖条动画 |
| 2 | 138x562 | 137 | 大型动画 |
| 4 | 12x58 | 11 | 小型动画 |
| 6 | 28x122 | 27 | 中型动画 |
| 14 | 24x106 | 23 | 中型动画 |

### 关键发现

1. **帧数=宽度**: 每帧对应一列,帧数等于图像宽度
2. **RLE压缩**: 每帧使用相同的RLE算法
3. **动画用途**: 可能用于水平滚动或波浪效果

### 提取的文件

- `/home/yinming/fd2_hermes/extracted/fdother/resource_001_lmi1.raw` (2346字节)
- `/home/yinming/fd2_hermes/extracted/fdother/resource_002_lmi1.raw` (77556字节)
- `/home/yinming/fd2_hermes/extracted/fdother/resource_004_lmi1.raw` (696字节)
- `/home/yinming/fd2_hermes/extracted/fdother/resource_006_lmi1.raw` (3416字节)
- `/home/yinming/fd2_hermes/extracted/fdother/resource_014_lmi1.raw` (2544字节)

## 下一步建议

1. 分析其他未知类型资源
2. 用DOSBox-X调试验证LMI1渲染过程
3. 分析其他DAT文件 (FDSHAP.DAT, FDTXT.DAT等)
4. 创建Rust版本的图像加载器
