#!/usr/bin/env python
"""Detailed header analysis for VDB plot.bin"""
import struct
import re
import numpy as np

path = r'D:\git\datafiletoolbox_samples\VIP\RKF.vdb\DNr\PLOT\plot.bin'
with open(path, 'rb') as f:
    header = f.read(300000)

print('=== First 64 bytes hex ===')
print(' '.join(f'{b:02x}' for b in header[:64]))
print('ASCII:', ''.join(chr(b) if 32 <= b < 127 else '.' for b in header[:64]))

# Find all VARDESC positions
vardesc_pos = [m.start() for m in re.finditer(rb'VARDESC', header)]
print(f'\n=== {len(vardesc_pos)} VARDESC at:', vardesc_pos)

# For each VARDESC, find where it starts and what comes before it
for i, pos in enumerate(vardesc_pos):
    before = header[max(0, pos - 32):pos]
    ints_le = [struct.unpack_from('<i', before, j)[0] for j in range(0, len(before) - 3, 4)]
    print(f'\nVARDESC #{i} at {pos}:')
    print(f'  Before (LE ints): {ints_le}')
    print(f'  Before (hex): {before.hex(" ")}')
    
    after = header[pos:pos + 80]
    ascii_repr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in after)
    print(f'  After ASCII: {ascii_repr}')

# What sits between consecutive VARDESCs?
print('\n=== Gaps between VARDESCs ===')
for i in range(len(vardesc_pos) - 1):
    gap = vardesc_pos[i + 1] - vardesc_pos[i]
    print(f'  VARDESC#{i} to #{i+1}: {gap} bytes')

# Find VARLIST positions (they appear inside VARDESC blocks)
varlist_pos = [m.start() for m in re.finditer(rb'VARLIST', header)]
print(f'\n=== {len(varlist_pos)} VARLIST at:', varlist_pos)

# What comes after the LAST VARDESC block?
last_vd = vardesc_pos[-1]
print(f'\n=== Scanning past last VARDESC (at {last_vd}) ===')

# Read more to find where data starts
with open(path, 'rb') as f:
    f.seek(last_vd)
    post_data = f.read(200000)

# Find ascii runs in post-VARDESC area
for m in re.finditer(rb'[\x20-\x7e]{4,}', post_data[:50000]):
    print(f'  ASCII at +{m.start()}: {m.group().decode("ascii")[:80]}')

print('\n=== Detailed look at first 512 bytes of file ===')
for off in range(0, 512, 16):
    hexpart = ' '.join(f'{header[off + j]:02x}' for j in range(min(16, len(header) - off)))
    ascpart = ''.join(chr(header[off + j]) if 32 <= header[off + j] < 127 else '.'
                      for j in range(min(16, len(header) - off)))
    print(f'  {off:6d} ({off:#06x}): {hexpart:<48s}  {ascpart}')

# Look at structure between byte 0 and first VARDESC
print(f'\n=== Structure from byte 0 to first VARDESC ({vardesc_pos[0]}) ===')
chunk = header[:vardesc_pos[0]]
# Try reading as pairs of (4-byte int, 4-byte int)
print(f'  Length: {len(chunk)} bytes')
ints_le = [struct.unpack_from('<i', chunk, j)[0] for j in range(0, len(chunk) - 3, 4)]
print(f'  As LE ints: {ints_le[:40]}')

# Also look at what's right before the file data
# The data should start somewhere after the last metadata
# Let's look for the first DBF marker which was at 310
print('\n=== Around DBF marker at 310 ===')
region = header[300:400]
ascii_repr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in region)
print(f'  ASCII: {ascii_repr}')
print(f'  Hex: {region.hex(" ")}')

# Now let's try to understand the ACTUAL data format
# Read 1MB starting from 300KB into the file 
print('\n=== Data area analysis (300KB-1.3MB) ===')
with open(path, 'rb') as f:
    f.seek(300000)
    data_region = f.read(1000000)

# Check for timestamp/date patterns
# Read as float32 both endiannesses
fle = np.frombuffer(data_region, dtype='<f4')
fbe = np.frombuffer(data_region, dtype='>f4')

print(f'  LE floats - first 40: {fle[:40].tolist()}')
print(f'  BE floats - first 40: {fbe[:40].tolist()}')

# Find reasonable float values
le_mask = np.isfinite(fle) & (np.abs(fle) > 0.001) & (np.abs(fle) < 1e8)
be_mask = np.isfinite(fbe) & (np.abs(fbe) > 0.001) & (np.abs(fbe) < 1e8)
print(f'  LE: {le_mask.sum()} of {len(fle)} are reasonable floats')
print(f'  BE: {be_mask.sum()} of {len(fbe)} are reasonable floats')

# Try double (float64)
fle64 = np.frombuffer(data_region, dtype='<f8')
fbe64 = np.frombuffer(data_region, dtype='>f8')
le64_mask = np.isfinite(fle64) & (np.abs(fle64) > 0.001) & (np.abs(fle64) < 1e8)
be64_mask = np.isfinite(fbe64) & (np.abs(fbe64) > 0.001) & (np.abs(fbe64) < 1e8)
print(f'  LE float64: {le64_mask.sum()} of {len(fle64)} are reasonable')
print(f'  BE float64: {be64_mask.sum()} of {len(fbe64)} are reasonable')

# Check if there's a regular pattern in LE ints (maybe record markers)
ile = np.frombuffer(data_region, dtype='<i4')
print(f'\n  LE ints - first 40: {ile[:40].tolist()}')

# Look for small ints that could be record-length markers
small = np.where((ile > 0) & (ile < 100000))[0]
if len(small) > 0:
    print(f'  Small positive ints (possible record markers): found {len(small)} in first 250K ints')
    print(f'  First 30 positions and values: {list(zip(small[:30].tolist(), ile[small[:30]].tolist()))}')
