#!/usr/bin/env python3
"""Deep analysis of FDOTHER.DAT file structure"""

import struct
import sys
import os

def analyze_fdother(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    
    print(f"=== FDOTHER.DAT Analysis ===")
    print(f"File size: {len(data):,} bytes ({len(data)/1024/1024:.2f} MB)")
    
    # Header
    header = data[:6]
    print(f"\nHeader: {header} (magic: 'LLLLLL')")
    
    # Parse index table
    # Format: 4 * index + 6 = offset to entry
    # Each entry: [start:DWORD, end:DWORD]
    
    entries = []
    index = 0
    
    while True:
        offset = 4 * index + 6
        if offset + 8 > len(data):
            break
        
        start = struct.unpack_from('<I', data, offset)[0]
        end = struct.unpack_from('<I', data, offset + 4)[0]
        
        if start == 0 and end == 0:
            break
        
        if start >= end or start >= len(data) or end > len(data):
            break
        
        entries.append({
            'index': index,
            'start': start,
            'end': end,
            'size': end - start
        })
        index += 1
    
    print(f"\nTotal valid entries: {len(entries)}")
    
    # Analyze resource types
    print("\n=== Resource Type Analysis ===")
    
    palettes = []  # 768 bytes = 256 colors * 3 RGB
    small_images = []  # < 10KB
    medium_images = []  # 10KB - 100KB
    large_images = []  # > 100KB
    sub_indexed = []  # Contains sub-index
    
    for e in entries:
        idx = e['index']
        size = e['size']
        start = e['start']
        block = data[start:start+min(256, size)]
        
        if size == 768:
            palettes.append(e)
            e['type'] = 'palette'
        elif size < 10000:
            small_images.append(e)
            e['type'] = 'small'
        elif size < 100000:
            medium_images.append(e)
            e['type'] = 'medium'
        else:
            large_images.append(e)
            e['type'] = 'large'
        
        # Check for sub-index structure
        if size > 10:
            first_word = struct.unpack_from('<H', block, 0)[0]
            if first_word > 1 and first_word < 1000:
                # Could be sub-index count
                e['possible_sub_index'] = first_word
                if first_word > 5:
                    sub_indexed.append(e)
    
    print(f"\nPalettes (768 bytes): {len(palettes)}")
    for p in palettes:
        print(f"  [{p['index']:3d}] offset=0x{p['start']:06X}")
    
    print(f"\nSmall resources (<10KB): {len(small_images)}")
    print(f"Medium resources (10KB-100KB): {len(medium_images)}")
    print(f"Large resources (>100KB): {len(large_images)}")
    
    print(f"\nResources with possible sub-index: {len(sub_indexed)}")
    for s in sub_indexed[:10]:
        print(f"  [{s['index']:3d}] size={s['size']:,}, sub_index_count={s.get('possible_sub_index', 'N/A')}")
    
    # Detailed analysis of first few resources
    print("\n=== Detailed Block Analysis ===")
    
    # Block 0: First palette
    print("\n--- Block 0: First Palette ---")
    e = entries[0]
    block = data[e['start']:e['end']]
    print(f"Size: {len(block)} bytes (expected 768 for 256-color palette)")
    
    # Convert DOS 6-bit palette to 8-bit
    print("First 5 colors (DOS 6-bit format, need ×4 for 8-bit):")
    for i in range(5):
        r, g, b = block[i*3], block[i*3+1], block[i*3+2]
        print(f"  Color {i}: RGB({r}, {g}, {b}) → RGB({r*4}, {g*4}, {b*4})")
    
    # Block 1: Small resource with sub-index
    print("\n--- Block 1: Icon/Sprite Index ---")
    e = entries[1]
    block = data[e['start']:e['end']]
    print(f"Size: {len(block)} bytes")
    print(f"First 64 bytes hex: {block[:64].hex()}")
    
    # Parse potential sub-index
    sub_count = struct.unpack_from('<H', block, 0)[0]
    print(f"Sub-index count word: {sub_count}")
    
    # Try to parse sub-entries
    print("Potential sub-entries:")
    for i in range(min(10, sub_count)):
        off = 2 + i * 4  # WORD count + array of DWORD offsets
        if off + 4 <= len(block):
            sub_off = struct.unpack_from('<I', block, off)[0]
            print(f"  [{i}]: offset=0x{sub_off:04X}")
    
    # Large blocks analysis
    print("\n--- Large Resources Analysis ---")
    for e in large_images[:3]:
        block = data[e['start']:e['end']]
        print(f"\n[{e['index']}] offset=0x{e['start']:06X}, size={e['size']:,} bytes")
        print(f"  First 32 bytes: {block[:32].hex()}")
        
        # Check for image dimensions
        # Try common sizes: 320x200, 640x400, etc.
        potential_sizes = [
            (320, 200, 1),  # 320x200 @ 1 byte/pixel = 64000
            (320, 200, 3),  # 320x200 RGB
            (640, 480, 1),
        ]
        for w, h, bpp in potential_sizes:
            expected = w * h * bpp
            if abs(e['size'] - expected) < 1000:
                print(f"  Possible: {w}x{h} @ {bpp} byte(s)/pixel = {expected} bytes")
    
    # Extract palette analysis
    print("\n=== Palette Comparison ===")
    if len(palettes) >= 3:
        for i, p in enumerate(palettes):
            block = data[p['start']:p['end']]
            # Check if identical
            if i > 0:
                prev = palettes[i-1]
                prev_block = data[prev['start']:prev['end']]
                if block == prev_block:
                    print(f"Palette {p['index']} identical to palette {prev['index']}")
                else:
                    # Count differences
                    diffs = sum(1 for a, b in zip(block, prev_block) if a != b)
                    print(f"Palette {p['index']} differs from {prev['index']} in {diffs} bytes")
    
    return entries, data

if __name__ == '__main__':
    filepath = sys.argv[1] if len(sys.argv) > 1 else '/home/yinming/fd2_dat/game/FDOTHER.DAT'
    entries, data = analyze_fdother(filepath)
