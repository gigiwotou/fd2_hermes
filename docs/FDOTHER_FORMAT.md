# FDOTHER.DAT 格式分析报告

## 文件结构

```
偏移      大小      说明
────────────────────────────────
0x00      6字节    头部标识 "LLLLLL"
0x06      4字节    索引数量 (uint32, 小端)
0x0A      N*8字节  索引表 (每项8字节)
...       ...      资源数据
```

## 索引表结构

每项8字节:
```
偏移0: uint32 资源起始位置
偏移4: uint32 资源结束位置
大小 = end - start
```

索引公式 (来自 sub_111BA):
```c
fseek(file, 4 * index + 6, SEEK_SET);
fread(&idx, 1, 8, file);
start = idx[0];
end = idx[1];
size = end - start;
```

## 资源类型

### 1. 图像资源 (RLE压缩)

头部结构:
```
偏移0: uint16 宽度
偏移2: uint16 高度
偏移4+: RLE压缩数据
```

### 2. 调色板资源

- 大小: 768字节 (256色 × 3字节RGB)
- 格式: DOS 6-bit格式 (需要 ×4 转换为8-bit)
- 资源: #28, #49, #50

### 3. 多帧图标

- 头部包含帧索引表
- 每帧独立RLE压缩

### 4. LMI1 格式

LMI1 是按列存储的动画格式,每帧存储一列数据:

```
偏移0-3: "LMI1" 标识
偏移4-5: 宽度 (uint16)
偏移6-7: 高度 (uint16)
偏移8+: 帧偏移表
```

帧偏移表格式:
```
[00 00][偏移1:2][00 00][偏移2:2][00 00][偏移3:2]...
```

每帧数据:
- RLE压缩
- 解压后高度=图像高度
- 帧数=图像宽度

解码步骤:
1. 读取宽度和高度
2. 解析帧偏移表
3. 逐帧RLE解码
4. 按列合成完整图像 (列优先转行优先)

## RLE压缩算法

来自 sub_4E98D (地址 0x4E98D):

```python
def decode_rle(data):
    width = read_uint16(data[0:2])
    height = read_uint16(data[2:4])
    output = []
    src = 4
    
    for line in range(height):
        line_data = [0] * width
        pos = 0
        
        while pos < width:
            value = data[src]
            src += 1
            count = (value & 0x3F) + 1
            
            if value >= 0xC0:      # 跳过
                pos += count       # 保持原值
            elif value >= 0x80:    # 复制
                for _ in range(count):
                    line_data[pos] = data[src]
                    src += 1
                    pos += 1
            elif value >= 0x40:    # RLE填充
                fill = data[src]
                src += 1
                for _ in range(count):
                    line_data[pos] = fill
                    pos += 1
            else:                  # 交错写入
                fill = data[src]
                src += 1
                for _ in range(count):
                    line_data[pos] = fill
                    pos += 1
                    if pos < width:
                        pos += 1  # 跳过一格
        
        output.extend(line_data)
    
    return output, width, height
```

### RLE 编码范围

| 值范围 | 说明 |
|--------|------|
| 0x00-0x3F | 交错写入: 填充值,隔一格写一格 |
| 0x40-0x7F | RLE填充: 后跟1字节填充值,连续写入 |
| 0x80-0xBF | 复制模式: 后跟n字节直接复制 |
| 0xC0-0xFF | 跳过模式: 跳过n像素 (保持原值) |

## 资源统计

- 总索引数: 422
- 有效资源: 51
- 图像资源: 28
- 调色板: 3
- LMI1格式: 5
- 多帧图标: 1
- 未知类型: 14

## 已提取资源列表

| 索引 | 尺寸 | 类型 | 说明 |
|------|------|------|------|
| 0 | 24x24 | 多帧 | 20帧图标 |
| 5 | 320x200 | 图像 | 全屏画面 |
| 7 | 320x200 | 图像 | 全屏画面 |
| 8 | 462x113 | 图像 | 宽幅画面 |
| 28 | 768 | 调色板 | 游戏调色板 |
| 29 | 320x200 | 图像 | 全屏画面 (小文件) |
| 30 | 320x200 | 图像 | 全屏画面 |
| 48 | 320x200 | 图像 | 全屏画面 |

## 工具

- `/home/yinming/fd2_hermes/tools/fdother_extract.py` - 提取和导出工具
- 用法:
  - `python3 fdother_extract.py extract 5` - 提取资源5
  - `python3 fdother_extract.py export 5` - 导出PNG
  - `python3 fdother_extract.py export-all` - 批量导出

## 相关函数

| 地址 | 函数 | 说明 |
|------|------|------|
| 0x111BA | sub_111BA | DAT文件加载 |
| 0x4E98D | sub_4E98D | RLE解压 |
| 0x2EB9F | sub_2EB9F | 资源渲染调度 |
| 0x2D80D | sub_2D80D | 场景加载 (引用FDOTHER.DAT) |

## 提取结果

提取目录: `/home/yinming/fd2_hermes/extracted/fdother/`

提取文件:
- 29个PNG图像文件
- 3个调色板文件 (.pal)
- 多个RAW数据文件
