#!/usr/bin/env python3
"""Extract resources from FDOTHER.DAT"""

import struct
import sys
import os

def parse_index(data):
    """Parse FDOTHER.DAT index table"""
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
    
    return entries

def save_palette(data, entry, output_path):
    """Save palette as PAL file (RGB triplets)"""
    block = data[entry['start']:entry['end']]
    
    with open(output_path, 'wb') as f:
        # Write as 8-bit RGB (multiply DOS 6-bit by 4)
        for i in range(256):
            r = block[i*3] * 4
            g = block[i*3+1] * 4
            b = block[i*3+2] * 4
            f.write(bytes([r, g, b]))
    
    print(f"Saved palette: {output_path}")

def save_raw_resource(data, entry, output_path):
    """Save raw resource data"""
    block = data[entry['start']:entry['end']]
    
    with open(output_path, 'wb') as f:
        f.write(block)
    
    print(f"Saved raw: {output_path} ({len(block)} bytes)")

def analyze_sub_indexed(data, entry, output_dir):
    """Analyze resources with sub-index"""
    block = data[entry['start']:entry['end']]
    size = len(block)
    
    # Try to parse sub-index
    if size < 4:
        return
    
    count = struct.unpack_from('<H', block, 0)[0]
    
    # Sanity check
    if count < 2 or count > 500:
        return
    
    # Try to parse offset array
    offsets = []
    for i in range(count):
        off = 2 + i * 4
        if off + 4 > size:
            break
        offset = struct.unpack_from('<I', block, off)[0]
        if offset < size:
            offsets.append(offset)
    
    if len(offsets) < 2:
        return
    
    # Analyze sub-resources
    print(f"\n  Entry {entry['index']}: {count} sub-resources")
    
    sub_sizes = []
    for i in range(len(offsets) - 1):
        sub_size = offsets[i+1] - offsets[i]
        sub_sizes.append(sub_size)
    sub_sizes.append(size - offsets[-1])
    
    print(f"    Sub-resource sizes: min={min(sub_sizes)}, max={max(sub_sizes)}, avg={sum(sub_sizes)//len(sub_sizes)}")
    
    # Save analysis
    analysis_path = os.path.join(output_dir, f"entry_{entry['index']:03d}_analysis.txt")
    with open(analysis_path, 'w') as f:
        f.write(f"Entry {entry['index']}\n")
        f.write(f"Total size: {size}\n")
        f.write(f"Sub-index count: {count}\n")
        f.write(f"\nOffset table:\n")
        for i, off in enumerate(offsets[:20]):
            f.write(f"  [{i:3d}]: 0x{off:04X}\n")
        if len(offsets) > 20:
            f.write(f"  ... ({len(offsets) - 20} more)\n")
        f.write(f"\nSub-resource sizes:\n")
        for i, sz in enumerate(sub_sizes[:20]):
            f.write(f"  [{i:3d}]: {sz} bytes\n")
    
    return {
        'count': count,
        'offsets': offsets,
        'sizes': sub_sizes
    }

def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else '/home/yinming/fd2_dat/game/FDOTHER.DAT'
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '/home/yinming/fd2_hermes/docs/fdother_extracted'
    
    os.makedirs(output_dir, exist_ok=True)
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    print(f"=== FDOTHER.DAT Resource Extraction ===")
    print(f"Input: {filepath}")
    print(f"Output: {output_dir}")
    
    entries = parse_index(data)
    print(f"\nTotal entries: {len(entries)}")
    
    # Categorize
    palettes = [e for e in entries if e['size'] == 768]
    small = [e for e in entries if e['size'] < 10000 and e['size'] != 768]
    medium = [e for e in entries if 10000 <= e['size'] < 100000]
    large = [e for e in entries if e['size'] >= 100000]
    
    print(f"\nCategories:")
    print(f"  Palettes (768 bytes): {len(palettes)}")
    print(f"  Small (<10KB): {len(small)}")
    print(f"  Medium (10-100KB): {len(medium)}")
    print(f"  Large (>100KB): {len(large)}")
    
    # Extract palettes
    print("\n--- Extracting Palettes ---")
    for p in palettes:
        output_path = os.path.join(output_dir, f"palette_{p['index']:03d}.pal")
        save_palette(data, p, output_path)
    
    # Analyze sub-indexed resources
    print("\n--- Analyzing Sub-Indexed Resources ---")
    sub_index_dir = os.path.join(output_dir, 'sub_indexed')
    os.makedirs(sub_index_dir, exist_ok=True)
    
    for e in entries:
        block = data[e['start']:e['end']]
        if e['size'] > 10:
            count = struct.unpack_from('<H', block, 0)[0]
            if 2 <= count <= 500:
                analyze_sub_indexed(data, e, sub_index_dir)
    
    # Create summary
    summary_path = os.path.join(output_dir, 'summary.txt')
    with open(summary_path, 'w') as f:
        f.write("FDOTHER.DAT Resource Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total entries: {len(entries)}\n\n")
        
        f.write("All Entries:\n")
        f.write("-" * 60 + "\n")
        for e in entries:
            f.write(f"[{e['index']:3d}] offset=0x{e['start']:06X} size={e['size']:,} bytes\n")
        
        f.write("\n\nPalette Entries:\n")
        f.write("-" * 60 + "\n")
        for p in palettes:
            f.write(f"[{p['index']:3d}] offset=0x{p['start']:06X}\n")
    
    print(f"\nSummary saved: {summary_path}")
    print("\nExtraction complete!")

if __name__ == '__main__':
    main()
