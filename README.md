# FD2 逆向工程项目

## 目录结构

```
fd2_hermes/
├── docs/
│   ├── AFM_FORMAT.md          # AFM 格式分析文档
│   └── afm_animations/        # 解码的动画文件
│       ├── afm_0.gif
│       ├── afm_1.gif
│       └── ...
├── tools/
│   └── decode_afm_fixed.py    # AFM 解码工具
├── game/
│   └── ANI.DAT                # 游戏数据
└── README.md
```

## 已完成工作

### ANI.DAT AFM 解码

- 分析了 ANI.DAT 文件结构
- 理解了 AFM 索引和帧格式
- 解码了 10 种命令类型 (0x00-0x09)
- 成功导出 9 个 AFM 动画为 GIF

### 关键发现

1. **索引格式**: 4 字节偏移，从文件偏移 6 开始
2. **帧数据是命令流**: 不是直接像素数据，而是命令序列
3. **命令 0x09**: 从帧数据复制到像素缓冲区，不是缓冲区内部复制
4. **调色板**: DOS 6-bit 格式，需要 ×4 转换

## 工具使用

```bash
cd /home/yinming/fd2_hermes/tools
python3 decode_afm_fixed.py
```

输出目录: `docs/afm_animations/`

## 下一步

- 分析 BG.DAT (背景图像)
- 分析 FIGANI.DAT (角色动画)
- 分析 TAI.DAT (图块数据)
