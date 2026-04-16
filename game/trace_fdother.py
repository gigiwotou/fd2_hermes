#!/usr/bin/env python3
"""
FD2 FDOTHER.DAT 动态跟踪脚本
通过监控 DOSBox-X 日志来跟踪文件操作
"""

import os
import time
import subprocess
import re
from datetime import datetime

# 配置
GAME_PATH = "/home/yinming/fd2_hermes/game"
TARGET_FILE = "FDOTHER.DAT"
LOG_FILE = "/tmp/fd2_trace.log"
DOSBOX_LOG = "/tmp/fd2_new.log"

def monitor_dosbox_log():
    """监控 DOSBox-X 日志文件"""
    print(f"开始监控 DOSBox-X 日志: {DOSBOX_LOG}")
    
    # 等待日志文件存在
    while not os.path.exists(DOSBOX_LOG):
        time.sleep(1)
    
    # 读取已有日志
    with open(DOSBOX_LOG, 'r', errors='ignore') as f:
        # 跳到文件末尾
        f.seek(0, 2)
        
        file_operations = []
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            
            # 检测文件操作
            if 'FILES:file' in line:
                # 解析文件操作
                # LOG: 3091537181 FILES:file open command 0 file DATO.DAT
                match = re.search(r'FILES:file (\w+) command (\d+) file (\S+)', line)
                if match:
                    op = match.group(1)
                    cmd = match.group(2)
                    filename = match.group(3)
                    
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    file_operations.append({
                        'time': timestamp,
                        'operation': op,
                        'command': cmd,
                        'filename': filename
                    })
                    
                    # 打印目标文件的操作
                    if TARGET_FILE in filename or 'FDOTHER' in filename.upper():
                        print(f"[{timestamp}] *** TARGET *** {op}: {filename}")
                    elif 'DAT' in filename:
                        print(f"[{timestamp}] {op}: {filename}")
            
            # 检测内存分配或数据加载
            if 'DEBUG' in line or 'alloc' in line.lower():
                pass  # 可以添加更多过滤条件

def analyze_file_structure():
    """分析 FDOTHER.DAT 文件结构"""
    print("\n" + "=" * 60)
    print(f"分析 {TARGET_FILE} 文件结构")
    print("=" * 60)
    
    filepath = os.path.join(GAME_PATH, TARGET_FILE)
    if not os.path.exists(filepath):
        print(f"错误: 文件不存在: {filepath}")
        return
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    print(f"\n文件大小: {len(data)} 字节 ({len(data)/1024:.1f} KB)")
    
    # 分析头部
    header = data[:256]
    print(f"\n头部签名: {header[:6]}")
    print(f"头部 hex: {header[:32].hex()}")
    
    # 查找索引表
    import struct
    
    # 尝试解析偏移表
    print("\n可能的偏移表条目:")
    for i in range(8, min(100, len(header)//4)):
        val = struct.unpack('<I', header[i*4:(i+1)*4])[0]
        if 0 < val < len(data):
            print(f"  偏移 {i*4:3d}: 0x{val:06X} ({val} bytes)")

def main():
    print("=" * 60)
    print("FD2 FDOTHER.DAT 动态跟踪")
    print("=" * 60)
    
    # 先分析文件结构
    analyze_file_structure()
    
    print("\n" + "=" * 60)
    print("开始监控 DOSBox-X 日志...")
    print("=" * 60 + "\n")
    
    # 监控日志
    try:
        monitor_dosbox_log()
    except KeyboardInterrupt:
        print("\n\n监控已停止")

if __name__ == '__main__':
    main()
