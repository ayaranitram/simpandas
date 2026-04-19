#!/usr/bin/env python
"""Extract all VARDESC table structures and find where data starts."""
import struct
import re
import numpy as np
import os

path = r'D:\git\datafiletoolbox_samples\VIP\RKF.vdb\DNr\PLOT\plot.bin'
filesize = os.path.getsize(path)

with open(path, 'rb') as f:
    # Read first 500KB for full header analysis
    header = f.read(500000)

# ---- Parse the file structure: each VARDESC has a table of keys/units ----
vardesc_pos = [m.start() for m in re.finditer(rb'VARDESC', header)]

print(f'File: {path}')
print(f'Size: {filesize:,} bytes')
print(f'VARDESC count: {len(vardesc_pos)}')

# Each VARDESC block is followed by VARLIST and ITEMS, then:
# - A list of 8-byte entity names (wells, groups, regions, etc.)
# - Then a list of 8-byte variable names
# After ALL VARDESC blocks, there's a detailed description section with units.

# Let's carefully parse each VARDESC block
for vi, vpos in enumerate(vardesc_pos):
    # Read from VARDESC to next VARDESC (or +50KB if last)
    if vi < len(vardesc_pos) - 1:
        block_end = vardesc_pos[vi + 1]
    else:
        block_end = min(vpos + 100000, len(header))
    
    block = header[vpos:block_end]
    
    # Find VARLIST and ITEMS markers
    varlist_off = block.find(b'VARLIST')
    items_off = block.find(b'ITEMS')
    
    print(f'\n{"="*70}')
    print(f'VARDESC #{vi} at offset {vpos}')
    print(f'  VARLIST at +{varlist_off}, ITEMS at +{items_off}')
    
    # The block between ITEMS+8 and the next section marker contains
    # 8-byte padded names (entities then variables)
    if items_off >= 0:
        names_start = items_off + 8  # skip "ITEMS   "
        # Scan for 8-byte padded ASCII names
        names = []
        pos = names_start
        while pos + 8 <= len(block):
            chunk = block[pos:pos + 8]
            # Check if it looks like an 8-byte padded name
            try:
                name = chunk.decode('ascii').strip()
            except UnicodeDecodeError:
                break
            if not name or not all(c.isalnum() or c in '-_. ' for c in name):
                break
            names.append(name)
            pos += 8
        
        print(f'  Names extracted: {len(names)}')
        if len(names) <= 60:
            print(f'  Names: {names}')
        else:
            print(f'  First 30: {names[:30]}')
            print(f'  Last 10: {names[-10:]}')
        
        # After the names block, look for the variable descriptions
        # (KEY     (UNITS)          DESCRIPTION)
        # Each is ~78 bytes: 8 + 16 + ~46
        desc_pattern = rb'([A-Z0-9_]{1,8}\s{0,7})\(([^)]{1,30})\)\s{0,8}(.{10,50})'
        descs = []
        for m in re.finditer(desc_pattern, block):
            key = m.group(1).decode('ascii', errors='replace').strip()
            unit = m.group(2).decode('ascii', errors='replace').strip()
            desc = m.group(3).decode('ascii', errors='replace').strip()
            descs.append((key, unit, desc))
        
        if descs:
            print(f'  Variable descriptions ({len(descs)}):')
            for key, unit, desc in descs[:20]:
                safe_desc = desc.encode('ascii', errors='replace').decode('ascii')
                print(f'    {key:8s} [{unit:20s}] {safe_desc}')
            if len(descs) > 20:
                print(f'    ... and {len(descs) - 20} more')

# ---- Now find where the LAST description section ends and data begins ----
print(f'\n{"="*70}')
print('LOOKING FOR DATA START')
print(f'{"="*70}')

# After the last VARDESC + descriptions, the data section starts
# Let's look for patterns that indicate start of numerical data
last_vd = vardesc_pos[-1]

# Read a big chunk starting from 200KB into the file
with open(path, 'rb') as f:
    f.seek(200000)
    scan = f.read(500000)  # 200KB-700KB

# Find last ASCII run >= 10 chars (end of description area)
last_ascii_end = 0
for m in re.finditer(rb'[\x20-\x7e]{10,}', scan):
    last_ascii_end = 200000 + m.end()

print(f'Last substantial ASCII ends at byte ~{last_ascii_end}')

# Look at the bytes right after the last ASCII section  
with open(path, 'rb') as f:
    f.seek(last_ascii_end - 20)
    transition = f.read(200)

print(f'\nTransition area (last ASCII to data):')
for off in range(0, len(transition), 16):
    actual_off = last_ascii_end - 20 + off
    hexpart = ' '.join(f'{transition[off + j]:02x}' for j in range(min(16, len(transition) - off)))
    ascpart = ''.join(chr(transition[off + j]) if 32 <= transition[off + j] < 127 else '.'
                      for j in range(min(16, len(transition) - off)))
    print(f'  {actual_off:8d}: {hexpart:<48s}  {ascpart}')

# ---- Now look for internal "markers" / "record boundaries" in the data ----
# Read chunks from well inside the data area 
print(f'\n{"="*70}')
print('DATA STRUCTURE ANALYSIS')
print(f'{"="*70}')

# Scan different spots in the file for patterns
for scan_start in [300000, 1000000, 5000000, 50000000]:
    if scan_start >= filesize:
        break
    with open(path, 'rb') as f:
        f.seek(scan_start)
        chunk = f.read(4000)
    
    fle = np.frombuffer(chunk, dtype='<f4')
    ile = np.frombuffer(chunk, dtype='<i4')
    
    print(f'\n--- Offset {scan_start:,} ---')
    # Show first 50 values as both floats and ints
    for i in range(min(50, len(fle))):
        flag = ''
        if ile[i] == -1 or ile[i] == -2:
            flag = ' <-- SENTINEL'
        elif 0 < ile[i] < 200 and (i == 0 or ile[i-1] < 0 or ile[i-1] > 100000):
            flag = ' <-- possible record count/marker?'
        print(f'  [{i:3d}] int={ile[i]:12d}  float={fle[i]:15.6g}  hex={chunk[i*4:i*4+4].hex()}{flag}')

# ---- Look for timestep/date markers ----
print(f'\n{"="*70}')
print('SEARCH FOR DATE/TIME VALUES')
print(f'{"="*70}')

# In the header we saw dates 8,3,2017 (March 8, 2017)
# Look for similar date patterns in the data
with open(path, 'rb') as f:
    big_chunk = f.read(min(filesize, 20000000))

ile_big = np.frombuffer(big_chunk, dtype='<i4')
# Search for patterns like [day, month, year] where year=2017-2020
for year in [2017, 2018, 2019, 2020]:
    year_pos = np.where(ile_big == year)[0]
    for pos in year_pos[:5]:
        if pos >= 2:
            day = ile_big[pos - 2]
            month = ile_big[pos - 1]
            if 1 <= day <= 31 and 1 <= month <= 12:
                print(f'  Date found: {day}/{month}/{year} at float index {pos-2} (byte {(pos-2)*4})')

# Also search for common VIP time markers
# VIP often stores days-since-start as float
fle_big = np.frombuffer(big_chunk, dtype='<f4')
# Common first timestep values: 1.0, 30.0, 30.4375, etc.
for val in [0.0, 1.0, 30.0, 30.4375, 365.0, 365.25]:
    count = np.sum(np.isfinite(fle_big) & (np.abs(fle_big - val) < 0.01))
    if count > 0 and count < 1000:
        print(f'  Float value ~{val}: found {count} times')
