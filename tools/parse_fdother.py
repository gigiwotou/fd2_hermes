#!/usr/bin/env python3
"""Parse FDOTHER.DAT using the correct index format from sub_111BA"""

import struct
import sys

def parse_fdother(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    
    # Header: 6 bytes
    header = data[:6]
    print(f"Header: {header}")
    
    # Index format from sub_111BA:
    # fseek(file, 4 * index + 6, 0)
    # read 8 bytes: [start:DWORD, end:DWORD]
    # size = end - start
    
    # Find how many entries by checking for valid ranges
    entries = []
    index = 0
    
    while True:
        offset = 4 * index + 6
        if offset + 8 > len(data):
            break
        
        start = struct.unpack_from('<I', data, offset)[0]
        end = struct.unpack_from('<I', data, offset + 4)[0]
        
        # Check if this looks like a valid entry
        # start should be < end, and both should be < file size
        if start == 0 and end == 0:
            # End marker
            print(f"\nEnd marker at index {index}")
            break
        
        if start >= end or start >= len(data) or end > len(data):
            # Invalid entry, likely end of index
            print(f"\nInvalid entry at index {index}: start=0x{start:X}, end=0x{end:X}")
            break
        
        entries.append((start, end, end - start))
        index += 1
    
    print(f"\nTotal valid entries: {len(entries)}")
    
    # Show first entries
    print("\nFirst 15 entries:")
    for i in range(min(15, len(entries))):
        start, end, size = entries[i]
        print(f"  [{i:3d}]: start=0x{start:06X}, end=0x{end:06X}, size={size}")
    
    # Show last entries
    print("\nLast 10 entries:")
    for i in range(max(0, len(entries)-10), len(entries)):
        start, end, size = entries[i]
        print(f"  [{i:3d}]: start=0x{start:06X}, end=0x{end:06X}, size={size}")
    
    # Analyze first data block
    print("\n--- First Data Block Analysis ---")
    start, end, size = entries[0]
    block = data[start:end]
    print(f"Block 0: offset=0x{start:X}, size={size}")
    print(f"First 64 bytes: {block[:64].hex()}")
    
    # Check if it looks like palette data (768 bytes for 256 colors)
    if size == 768:
        print("  -> Looks like a 256-color palette (768 bytes)")
    
    # Analyze block 1
    if len(entries) > 1:
        start, end, size = entries[1]
        block = data[start:end]
        print(f"\nBlock 1: offset=0x{start:X}, size={size}")
        print(f"First 64 bytes: {block[:64].hex()}")
        
        # Check for sub-index (like AFM structure)
        if size > 100:
            # Try to interpret as index table
            sub_index_count = struct.unpack_from('<H', block, 0)[0]
            print(f"  First word: {sub_index_count} (possible sub-index count)")
    
    # Analyze block 2
    if len(entries) > 2:
        start, end, size = entries[2]
        block = data[start:end]
        print(f"\nBlock 2: offset=0x{start:X}, size={size}")
        print(f"First 64 bytes: {block[:64].hex()}")
    
    return entries

if __name__ == '__main__':
    filepath = sys.argv[1] if len(sys.argv) > 1 else '/home/yinming/fd2_dat/game/FDOTHER.DAT'
    entries = parse_fdother(filepath)
