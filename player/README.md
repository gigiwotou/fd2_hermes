# FD2 Animation Player

Rust 编写的 ANI.DAT 动画播放器，使用 minifb 库实现窗口显示。

## 功能

- 直接读取 ANI.DAT 文件
- 支持 9 个 AFM 动画
- 所有命令类型 (0x00-0x09)
- 正确的调色板渲染 (DOS 6-bit → 8-bit)
- 简单UI界面
- GIF 导出功能

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

### 键盘
- **数字键 1-9**: 选择动画
- **左/右方向键**: 切换动画
- **S**: 保存当前动画为 GIF
- **ESC**: 退出

### 鼠标
- **双击列表项**: 选择动画
- **点击 Save 按钮**: 保存对应动画为 GIF

## 输出文件

GIF 文件保存在当前目录，命名格式：`AFM_N.gif`

## 动画列表

| 编号 | 名称 | 描述 |
|------|------|------|
| AFM 0 | Opening | 片头动画 |
| AFM 1 | Battle | 战斗场景 |
| AFM 2 | Character | 角色动作 |
| AFM 3 | Effect | 特效动画 |
| AFM 4 | Item | 物品动画 |
| AFM 5 | Transition | 场景过渡 |
| AFM 6 | Interface | 界面动画 |
| AFM 7 | Title | 标题画面 |
| AFM 8 | Ending | 结局动画 |
