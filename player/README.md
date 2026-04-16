# FD2 Animation Player

Rust 编写的 ANI.DAT 动画播放器，使用 minifb 库实现窗口显示。

## 功能

- 直接读取 ANI.DAT 文件
- 支持 9 个 AFM 动画
- 所有命令类型 (0x00-0x09)
- 正确的调色板渲染 (DOS 6-bit → 8-bit)
- 播放列表 UI 界面
- GIF 导出功能
- 分辨率缩放 (1x/2x/4x/自适应)

## 编译

```bash
cd player
cargo build --release
```

## 运行

```bash
# 默认 2x 缩放 (推荐)
./target/release/fd2_player

# 指定 ANI.DAT 路径
./target/release/fd2_player /path/to/ANI.DAT

# 不同缩放级别
./target/release/fd2_player --scale=1   # 原始 320x200
./target/release/fd2_player --scale=2   # 640x400 (默认)
./target/release/fd2_player --scale=4   # 1280x800
./target/release/fd2_player --scale=fit # 自适应屏幕

# 显示帮助
./target/release/fd2_player --help
```

## 控制

### 键盘
- **数字键 1-9**: 直接选择动画
- **上/下方向键**: 切换动画
- **左/右方向键**: 切换动画 (备用)
- **S**: 保存当前动画为 GIF
- **ESC**: 退出

## 输出文件

GIF 文件保存在当前目录，命名格式：`AFM_N.gif`

## 动画列表

| 编号 | 名称 | 描述 |
|------|------|------|
| 1 | Opening | 片头动画 |
| 2 | Battle | 战斗场景 |
| 3 | Character | 角色动作 |
| 4 | Effect | 特效动画 |
| 5 | Item | 物品动画 |
| 6 | Transition | 场景过渡 |
| 7 | Interface | 界面动画 |
| 8 | Title | 标题画面 |
| 9 | Ending | 结局动画 |

## 依赖

- [minifb](https://crates.io/crates/minifb) - 窗口渲染
- [image](https://crates.io/crates/image) - GIF 编码
