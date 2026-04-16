# DOSBox-X 调试器操作指南

## 当前状态

DOSBox-X 正在运行，游戏已经加载。窗口 ID: `0xa00687`

## 进入调试器的方法

### 方法1: 使用 Alt+Pause
1. 点击 DOSBox-X 窗口使其获得焦点
2. 按 `Alt + Pause` 键
3. 游戏会暂停，出现调试器提示符 `>`

### 方法2: 使用 xdotool
```bash
# 激活窗口
DISPLAY=:0 xdotool windowactivate 0xa00687

# 发送 Alt+Pause
DISPLAY=:0 xdotool key Alt+Pause
```

### 方法3: 从启动时进入调试器
```bash
# 杀掉当前进程
pkill -9 dosbox

# 使用 -startdebug 启动（直接进入调试器）
DISPLAY=:0 dosbox-x -startdebug -debug \
  -c "MOUNT C /home/yinming/fd2_hermes/game" \
  -c "C:" \
  -c "FD2.EXE"
```

## 调试器命令

### 基本命令
| 命令 | 说明 |
|------|------|
| `G` | 继续执行 (Go) |
| `T` | 单步执行 (Trace) |
| `P` | 单步执行（跳过调用） |
| `Q` | 退出调试器 |
| `H` | 显示帮助 |

### 断点命令
| 命令 | 说明 |
|------|------|
| `BP 地址` | 设置断点，如 `BP 0000:111BA` |
| `BPLIST` | 列出所有断点 |
| `BC 编号` | 清除断点，如 `BC 0` |
| `BPE 地址` | 启用断点 |
| `BPD 地址` | 禁用断点 |

### 查看命令
| 命令 | 说明 |
|------|------|
| `CPU` | 显示 CPU 寄存器 |
| `R` | 显示/修改寄存器 |
| `D 地址` | 显示内存，如 `D DS:0` |
| `U 地址` | 反汇编，如 `U CS:IP` |

## 跟踪 FDOTHER.DAT 加载

### 目标断点
- `0x111BA` - DAT 文件加载函数

### 操作步骤
1. 进入调试器后：
   ```
   BP 0000:111BA
   BPLIST
   G
   ```

2. 当断点触发时：
   ```
   CPU                    ; 查看寄存器
   D SS:SP               ; 查看栈参数
   D DS:SI               ; 查看文件名（如果在 SI 中）
   ```

3. 单步跟踪：
   ```
   T                     ; 执行一条指令
   T 10                  ; 执行10条指令
   ```

### 关键信息
当在 0x111BA 处断点触发时，注意观察：
- **AX**: 可能是资源索引
- **BX/CX/DX**: 其他参数
- **栈**: 可能包含文件句柄或参数
- **返回地址**: 在栈顶，显示调用来源

## 从日志分析加载模式

当前游戏正在运行，FDOTHER.DAT 已被打开多次。

查看最新日志：
```bash
tail -f /tmp/fd2_debugger_live.log | grep FDOTHER
```

分析文件加载频率：
```bash
grep "FDOTHER.DAT" /tmp/fd2_debugger_live.log | wc -l
```

## 调试器截图位置

如果需要记录调试状态，可以在触发断点后：
1. 使用 `CPU` 命令查看寄存器
2. 使用 `D` 命令查看内存
3. 手动记录或截图关键信息

## 常见问题

**Q: Alt+Pause 不起作用？**
- 尝试使用 Pause 键单独
- 或使用 Ctrl+Pause
- 检查窗口是否获得焦点

**Q: 找不到断点？**
- 确保地址格式正确：`段:偏移`
- 使用 `0000:111BA` 格式

**Q: 游戏运行太快？**
- 使用 `BP` 设置断点会暂停执行
- 使用 `-break-start` 启动参数在开始时暂停
