# FD2 DAT 文件系统分析报告

## 概述
FD2 游戏使用统一的 DAT 文件格式存储所有资源，所有文件都以 "LLLLLL" 作为魔数头。

## 通用索引格式
从反编译函数 `sub_111BA` (地址 0x111BA) 分析得出：

```c
// DAT 文件加载函数
// 参数: filename, old_buffer_ptr, index
BYTE* load_dat_entry(const char* filename, BYTE* old_ptr, int index) {
    if (old_ptr) free(old_ptr);
    
    FILE* f = fopen(filename, "rb");
    if (!f) {
        printf("\n\n File not found %s!!! \n\n", filename);
        exit(1);
    }
    
    // 读取索引表项
    fseek(f, 4 * index + 6, SEEK_SET);  // 跳过 6 字节头
    DWORD start, end;
    fread(&start, 4, 1, f);
    fread(&end, 4, 1, f);
    
    DWORD size = end - start;
    BYTE* buffer = malloc(size);
    if (!buffer) {
        printf("Out of Memory at Load %s Number:%d!!\n", filename, index);
        exit(1);
    }
    
    fseek(f, start, SEEK_SET);
    fread(buffer, 1, size, f);
    fclose(f);
    
    return buffer;
}
```

## 文件列表

| 文件 | 大小 | 条目数 | 主要用途 |
|------|------|--------|----------|
| FIGANI.DAT | 15.3 MB | 204 | 角色/物体动画 |
| FDSHAP.DAT | 3.56 MB | 33 | 形状/精灵数据 |
| FDOTHER.DAT | 3.23 MB | 52+ | 其他资源(调色板/图标等) |
| ANI.DAT | 2.44 MB | 5 | 场景动画 |
| DATO.DAT | 1.98 MB | 68 | 游戏界面元素 |
| BG.DAT | 624 KB | 28 | 背景图像 |
| FDFIELD.DAT | 243 KB | 50 | 场地/关卡数据 |
| TAI.DAT | 94.9 KB | 28 | 图块集 |
| FDTXT.DAT | 120 KB | 17 | 文本数据 |
| FDMUS.DAT | 80.4 KB | 10 | 音乐数据 |

## FDOTHER.DAT 详细分析

### 使用索引统计 (来自反编译代码)
| 索引 | 调用函数 | 用途推测 |
|------|----------|----------|
| 0 | sub_10010 | 主调色板 |
| 1 | - | 图标索引表 (24 子项) |
| 15 | sub_10652 | 场景 9, 24, 25 资源 |
| 16-17 | sub_10652 | 场景 21, 22, 27 精灵 |
| 42 | sub_10652 | 场景 23 背景 |
| 55 | sub_10652 | 场景 28, 29 资源 |
| 56 | sub_31C49 | 游戏界面 |
| 64 | sub_1A7BD | - |
| 80 | sub_1D4CB | - |
| 95-102 | 多函数 | 游戏结束画面 |

### 调色板条目 (768 字节 = 256 色 × 3)
- 条目 0: 主调色板 (游戏启动加载)
- 条目 8: 场景调色板
- 条目 57, 76, 99, 101, 102: 各场景调色板

### DOS 调色板格式转换
```python
def convert_dos_palette(data):
    """将 DOS 6-bit 调色板转换为 8-bit RGB"""
    colors = []
    for i in range(0, len(data), 3):
        r = data[i] * 4    # 0-63 -> 0-252
        g = data[i+1] * 4
        b = data[i+2] * 4
        colors.append((r, g, b))
    return colors
```

## RLE 解码格式

函数 `sub_4E98D` 实现了 RLE 解码：

### 数据头
```
struct RLEHeader {
    WORD width;      // 宽度 (像素)
    WORD height;     // 高度 (行数)
    BYTE data[];     // RLE 编码数据
};
```

### 控制字节编码
| 字节范围 | 操作 | 参数解析 |
|----------|------|----------|
| 0x00-0x3F | 跳过像素 | count = (byte >> 2) + 1 |
| 0x40-0x7F | 复制字节 | count = (byte >> 2) + 1, 从源读取 |
| 0x80-0xBF | 填充像素 | count = (byte >> 2) + 1, 用下一字节填充 |
| 0xC0-0xFF | 交替填充 | count = (byte >> 2) + 1, 像素对交替 |

### 解码伪代码
```c
void decode_rle(BYTE* src, BYTE* dst, int width, int height) {
    int remaining = width;
    while (height > 0) {
        BYTE ctrl = *src++;
        int count = (ctrl >> 2) + 1;
        
        if (ctrl & 0x80) {        // 0x80-0xFF
            if (ctrl & 0x40) {    // 0xC0-0xFF: 交替填充
                BYTE val = *src++;
                for (int i = 0; i < count; i++) {
                    dst[0] = val;
                    dst[1] = val;
                    dst += 2;
                }
            } else {              // 0x80-0xBF: 单色填充
                BYTE val = *src++;
                memset(dst, val, count);
                dst += count;
            }
        } else if (ctrl & 0x40) { // 0x40-0x7F: 跳过
            dst += count;
        } else {                  // 0x00-0x3F: 复制
            memcpy(dst, src, count);
            src += count;
            dst += count;
        }
        
        remaining -= count;
        if (remaining <= 0) {
            remaining = width;
            height--;
        }
    }
}
```

## 场景加载流程

从 `sub_2CF30` 分析的场景加载：

1. **加载背景 (BG.DAT)** - 根据场景号加载对应索引
2. **加载图块 (TAI.DAT)** - 同一索引
3. **加载动画 (FIGANI.DAT)** - 角色动画帧
4. **解码渲染** - 使用 RLE 解码到缓冲区

### 场景索引映射
```c
switch (scene_id) {
    case 24: bg_index = 15; break;
    case 28: bg_index = 20; break;
    case 29: bg_index = 13; break;
    default: bg_index = 18; break;
}
```

## 关键函数地址表

| 地址 | 名称 | 功能 |
|------|------|------|
| 0x111BA | load_dat_entry | DAT 文件通用加载 |
| 0x4E98D | decode_rle | RLE 解码 |
| 0x10652 | load_scene_resources | 场景资源加载 |
| 0x2CF30 | init_scene | 场景初始化 |
| 0x31C49 | game_loop_init | 游戏主循环初始化 |
| 0x10010 | load_savegame | 加载存档 |
| 0x25977 | render_sprite | 精灵渲染 |

## 下一步工作

1. **提取所有调色板** - 转换为标准格式
2. **解码子索引资源** - 分析条目 1, 96 的子结构
3. **建立资源映射表** - 场景索引与文件索引对应
4. **实现图像导出** - PNG/BMP 格式转换器

## 参考文件

- 反编译代码: `/home/yinming/fd2_dat2/tools/export-for-ai/decompile/`
- 函数索引: `/home/yinming/fd2_dat2/tools/export-for-ai/function_index.txt`
- 字符串表: `/home/yinming/fd2_dat2/tools/export-for-ai/strings.txt`
