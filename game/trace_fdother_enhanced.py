#!/usr/bin/env python3
"""
FD2 FDOTHER.DAT 增强版跟踪脚本
结合日志分析和调试器断点，跟踪完整的加载过程
"""

import os
import re
import subprocess
import time
from datetime import datetime

# 配置
GAME_PATH = "/home/yinming/fd2_hermes/game"
LOG_FILE = "/tmp/fd2_fdother_trace.log"

# 已知的关键地址（来自之前的IDA分析）
KEY_ADDRESSES = {
    'dat_load': 0x111BA,      # DAT文件通用加载函数
    'main': 0x25BF4,          # 主函数入口
    'file_open': 0x117E7,     # 文件打开相关
}

def analyze_fdother_structure():
    """分析 FDOTHER.DAT 文件结构"""
    filepath = os.path.join(GAME_PATH, "FDOTHER.DAT")
    
    print("\n" + "="*70)
    print("FDOTHER.DAT 文件结构分析")
    print("="*70)
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    print(f"\n文件大小: {len(data):,} 字节 ({len(data)/1024:.1f} KB)")
    
    # 验证魔数
    magic = data[:6]
    print(f"魔数: {magic} (预期: LLLLLL)")
    
    import struct
    
    # 读取索引条目数
    index_count = struct.unpack('<I', data[6:10])[0]
    print(f"索引条目数: {index_count}")
    
    # 分析前几个资源
    print(f"\n前10个资源索引:")
    print(f"{'索引':<6} {'起始偏移':<12} {'结束偏移':<12} {'大小':<10} {'说明'}")
    print("-" * 60)
    
    for i in range(min(10, index_count)):
        offset = 10 + i * 8
        start = struct.unpack('<I', data[offset:offset+4])[0]
        end = struct.unpack('<I', data[offset+4:offset+8])[0]
        size = end - start
        
        # 根据之前的分析给出说明
        descriptions = {
            0: "调色板 (256×3=768字节)",
            1: "图像资源",
            2: "图像资源",
            4: "字体数据",
        }
        desc = descriptions.get(i, "")
        
        print(f"{i:<6} 0x{start:08X}    0x{end:08X}    {size:>8,}  {desc}")
    
    return {
        'index_count': index_count,
        'size': len(data),
        'first_resource_offset': struct.unpack('<I', data[10:14])[0]
    }

def create_debug_script():
    """创建DOSBox调试脚本"""
    script_content = """# FDOTHER.DAT 加载跟踪脚本
# 在DOSBox-X调试器中运行

# 设置日志
LOG TO /tmp/fd2_debug_trace.txt

# 断点：DAT文件加载函数入口
BP 0000:111BA

# 断点：文件打开检测
# BPINT 21 AH=3D

# 显示初始CPU状态
CPU

# 继续执行到第一个断点
G

# 到达断点后的分析步骤
# 1. 查看当前函数参数
# 2. 单步执行查看文件名
# 3. 跟踪返回值

# 内存转储示例
# D DS:SI

# 单步执行
# T

# 继续执行
# G
"""
    
    script_path = os.path.join(GAME_PATH, "fdother_debug.txt")
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    return script_path

def monitor_file_operations():
    """监控文件操作日志"""
    print("\n" + "="*70)
    print("启动文件操作监控")
    print("="*70)
    
    # 启动DOSBox-X并监控日志
    log_file = "/tmp/fd2_monitor.log"
    
    cmd = f"""DISPLAY=:0 dosbox-x -debug \\
     -c "MOUNT C {GAME_PATH}" \\
     -c "C:" \\
     -c "FD2.EXE" \\
     > {log_file} 2>&1 &
    """
    
    print(f"\n执行命令: {cmd}")
    print(f"日志文件: {log_file}")
    print("\n请在另一个终端运行以下命令来监控:")
    print(f"  tail -f {log_file} | grep -E '(FILES|FDOTHER|breakpoint)'")
    
    return log_file

def summarize_findings():
    """总结发现"""
    print("\n" + "="*70)
    print("FDOTHER.DAT 加载分析总结")
    print("="*70)
    
    print("""
根据日志分析，FDOTHER.DAT 的加载模式：

1. **首次加载时机**: 游戏启动后最先加载的DAT文件之一
   - 在 DOS4GW 加载后
   - 在音频驱动初始化后
   - 在其他DAT文件之前

2. **加载频率**: 
   - 游戏启动阶段: 连续打开3-5次
   - 场景切换时: 每次场景加载都会打开
   - 总计: 游戏运行期间约35-100次

3. **加载的资源类型** (根据索引):
   - 资源0: 调色板数据 (768字节, 256色×3)
   - 资源1-2: 图像资源
   - 资源4: 字体数据
   - 其他: 混合资源

4. **关键函数地址**:
   - 0x111BA: DAT文件通用加载函数
   - 调用方式: sub_111BA(fileHandle, resourceIndex)
   - 索引计算: offset = 4 * resourceIndex + 6

5. **调试建议**:
   - 在 0x111BA 设置断点
   - 观察 DS:SI 寄存器（文件名指针）
   - 跟踪 DX 寄存器（资源索引）
""")

def main():
    print("="*70)
    print("FD2 FDOTHER.DAT 动态跟踪工具")
    print("Enhanced File Loading Tracer")
    print("="*70)
    
    # 1. 分析文件结构
    structure = analyze_fdother_structure()
    
    # 2. 创建调试脚本
    debug_script = create_debug_script()
    print(f"\n调试脚本已创建: {debug_script}")
    
    # 3. 总结发现
    summarize_findings()
    
    print("\n" + "="*70)
    print("下一步操作建议")
    print("="*70)
    print("""
方法A: 使用DOSBox-X调试器手动跟踪
  1. 启动: DISPLAY=:0 dosbox-x -debug -break-start
  2. 在调试器中输入: BP 0000:111BA
  3. 输入 G 继续执行
  4. 当断点触发时，使用 T 单步执行

方法B: 使用日志监控
  1. 运行游戏并记录日志
  2. 分析 FILES:file open 记录
  3. 关联时间戳找到加载模式

方法C: 使用IDA Pro + MCP
  1. 分析 0x111BA 函数的详细逻辑
  2. 理解参数传递方式
  3. 重建加载算法
""")

if __name__ == '__main__':
    main()
