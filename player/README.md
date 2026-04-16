# FD2 Animation Player

Rust 编写的 ANI.DAT 动画播放器，使用 minifb 库实现窗口显示。

## 编译

```bash
cd player
cargo build --release
```

## 运行

```bash
# 默认读取 ../game/ANI.DAT
./target/release/fd2_player

# 或指定文件路径
./target/release/fd2_player /path/to/ANI.DAT
```

## 控制

- **数字键 1-9**: 选择动画
- **左/右方向键**: 切换动画
- **ESC**: 退出

## 功能

- 直接读取 ANI.DAT 文件
- 支持 9 个 AFM 动画
- 支持所有命令类型 (0x00-0x09)
- 正确的调色板渲染 (DOS 6-bit → 8-bit)
- 实时帧计数显示
