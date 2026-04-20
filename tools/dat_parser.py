#!/usr/bin/env python3
"""
FD2 DAT 文件通用解析器
基于反编译代码 sub_111BA 的索引格式分析
"""

import struct
import os
import sys

def read_dat_index(filepath, index):
    """
    读取 DAT 文件中指定索引的数据
    索引格式: fseek(file, 4 * index + 6, 0) 然后读取 8 字节 [start, end]
    """
    with open(filepath, 'rb') as f:
        # 跳过文件头 (通常是 6 字节)
        f.seek(0)
        header = f.read(6)
        
        # 读取索引表项
        f.seek(4 * index + 6)
        data = f.read(8)
        if len(data) < 8:
            return None, 0
        
        start, end = struct.unpack('<II', data)
        size = end - start
        
        if size == 0:
            return None, 0
            
        # 读取数据
        f.seek(start)
        data = f.read(size)
        
        return data, size

def get_dat_info(filepath):
    """获取 DAT 文件基本信息"""
    with open(filepath, 'rb') as f:
        header = f.read(6)
        file_size = os.path.getsize(filepath)
        
        # 计算最大索引
        f.seek(6)
        max_index = 0
        while True:
            data = f.read(8)
            if len(data) < 8:
                break
            start, end = struct.unpack('<II', data)
            if start >= file_size or end > file_size:
                break
            max_index += 1
            
        return {
            'header': header,
            'file_size': file_size,
            'max_index': max_index
        }

def analyze_all_entries(filepath):
    """分析所有条目"""
    info = get_dat_info(filepath)
    entries = []
    
    for i in range(info['max_index']):
        data, size = read_dat_index(filepath, i)
        entry = {
            'index': i,
            'size': size,
            'is_palette': size == 768,
            'is_subindexed': False
        }
        
        if data and len(data) > 4:
            # 检查是否有子索引
            first_dword = struct.unpack('<I', data[:4])[0]
            if first_dword < len(data) and first_dword < 1000:
                entry['is_subindexed'] = True
                entry['sub_index_count'] = first_dword
                
        entries.append(entry)
        
    return entries

def main():
    dat_dir = '/home/yinming/fd2_dat/game'
    
    dat_files = [
        'ANI.DAT', 'BG.DAT', 'FDOTHER.DAT', 'FIGANI.DAT',
        'FDSHAP.DAT', 'FDFIELD.DAT', 'FDTXT.DAT', 'TAI.DAT',
        'FDMUS.DAT', 'DATO.DAT'
    ]
    
    print("=" * 70)
    print("FD2 DAT 文件分析")
    print("=" * 70)
    
    for dat_file in dat_files:
        filepath = os.path.join(dat_dir, dat_file)
        if not os.path.exists(filepath):
            continue
            
        info = get_dat_info(filepath)
        print(f"\n{dat_file}:")
        print(f"  文件头: {info['header'][:6]}")
        print(f"  文件大小: {info['file_size']:,} 字节")
        print(f"  条目数: {info['max_index']}")
        
        # 分析条目
        if dat_file in ['FDOTHER.DAT', 'ANI.DAT', 'FIGANI.DAT']:
            entries = analyze_all_entries(filepath)
            palettes = [e for e in entries if e['is_palette']]
            subindexed = [e for e in entries if e['is_subindexed']]
            
            if palettes:
                print(f"  调色板条目: {[e['index'] for e in palettes]}")
            if subindexed:
                print(f"  子索引条目: {[(e['index'], e.get('sub_index_count', 0)) for e in subindexed[:5]]}")

if __name__ == '__main__':
    main()
