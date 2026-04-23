# FDOTHER.DAT 子索引格式更新分析

## 实际观察到的数据结构

### 类型 A: 无子项 (sub_count = 0)
- 例如：索引 18 (16x16)
```
字节 0-1: width (little-endian)
字节 2-3: height (little-endian)
字节 4+:   RLE 数据流
```

### 类型 B: 有子项 (sub_count > 0)
- 例如：索引 1 (24x24, 20子项), 索引 19 (30x30, 30子项)
```
字节 0-1:   width (little-endian)
字节 2-3:   height (little-endian)
字节 4-5:   sub_count (little-endian, 子项数量)
字节 6+:    offset_table (每项4字节 DWORD, 相对偏移)
           - 偏移是相对于"子项数据块起始位置"或"主资源起始位置"
字节 N+:    RLE 数据流 (offset表结束后)
```

### 关键问题
offset 表指向的位置不是 RLE 图像数据，而是某种**中间格式**或**引用**。

从 offset 位置读取的前2字节通常是:
- 0x81XX 或其他 RLE 命令值
- 不是有效的 width 值

## 索引 18 详细分析

```
字节 0-1:   0x10 0x00 -> width = 16
字节 2-3:   0x10 0x00 -> height = 16
字节 4-7:   0x00 0x00 0x00 0x00 -> offset[0] = 0?
字节 8-11:  0x48 0x00 0x00 0x00 -> offset[1] = 0x48 = 72
字节 12-15: 0x6D 0x00 0x00 0x00 -> offset[2] = 0x6D = 109
...
```

字节 72 处的数据: `0A 00 00 00 00 00 00 00 01 00 0C 00 80 97...`
- 如果这是 RLE 头: width = 10, height = 0 (无效)

## 可能的解释

1. **offset 表可能指向嵌套的子资源**
2. **真正的 RLE 数据在 offset 表之后**（字节86开始），offset 表只是提供随机访问能力
3. **FDOTHER 资源可能有多种变体格式**

## 索引 1 的 offset 表分析

| Index | Offset (hex) | 指向的数据 |
|-------|--------------|-----------|
| 0 | 0x56 | 8160be04bd82... |
| 1 | 0x133 | 8160be04bd88... |
| 2 | 0x22e | 8160be04bd88... |
| ... | ... | ... |

所有 offset 处的数据都以 `81` 或 `82` 等 RLE 命令字节开头。

## 下一步

1. 确认 offset 表的实际含义
2. 验证 RLE 数据是否从 offset 表结束后连续存放
3. 找出为什么 offset 值不能直接用于定位 RLE 头