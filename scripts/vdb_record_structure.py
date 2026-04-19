#!/usr/bin/env python
"""Find the record structure in VDB plot.bin data section."""
import struct
import numpy as np
import os

path = r'D:\git\datafiletoolbox_samples\VIP\RKF.vdb\DNr\PLOT\plot.bin'
filesize = os.path.getsize(path)

# Read a chunk from the data area where we know the pattern exists
# At offset 5,000,000 we found: 55, -1, 55, [data...]
# Let's find ALL occurrences of this count/-1/count pattern

print(f'File size: {filesize:,} bytes ({filesize // 4:,} int32s)')

# Read a moderate chunk to analyze
with open(path, 'rb') as f:
    f.seek(4_900_000)
    chunk = f.read(200_000)

ile = np.frombuffer(chunk, dtype='<i4')
fle = np.frombuffer(chunk, dtype='<f4')

# Find all positions where we have: N, -1, N (same N)
# This is the record boundary pattern
records = []
i = 0
while i < len(ile) - 2:
    if ile[i] > 0 and ile[i] < 100000 and ile[i + 1] == -1 and ile[i + 2] == ile[i]:
        count = ile[i]
        records.append((i, count))
        # Skip past this record
        i += 3 + count  # 3 for (count, -1, count) + count data items
    else:
        i += 1

print(f'\nRecords found in 200KB chunk at offset 4.9M:')
print(f'  Total records: {len(records)}')
if records:
    counts = [r[1] for r in records]
    unique_counts = sorted(set(counts))
    print(f'  Unique record sizes: {unique_counts}')
    for uc in unique_counts:
        n = counts.count(uc)
        print(f'    count={uc}: {n} records ({uc} floats = {uc * 4} bytes)')
    
    # Show first 5 records with data preview
    for idx, (pos, count) in enumerate(records[:10]):
        data_start = pos + 3
        data_end = data_start + count
        if data_end <= len(fle):
            data = fle[data_start:data_end]
            nonzero = np.count_nonzero(data)
            print(f'\n  Record #{idx}: pos={pos} (byte={4900000 + pos*4}), count={count}, '
                  f'nonzero={nonzero}/{count}')
            print(f'    First 15 values: {data[:15].tolist()}')
            if count > 15:
                print(f'    Last 5 values: {data[-5:].tolist()}')

# Now let's find the VERY FIRST record boundary in the file
print(f'\n{"="*70}')
print('SCANNING FOR FIRST DATA RECORD')
print(f'{"="*70}')

# Read first 2MB to find where records start
with open(path, 'rb') as f:
    early = f.read(2_000_000)
ile_early = np.frombuffer(early, dtype='<i4')

first_records = []
i = 0
while i < len(ile_early) - 2 and len(first_records) < 30:
    if ile_early[i] > 10 and ile_early[i] < 100000 and ile_early[i + 1] == -1 and ile_early[i + 2] == ile_early[i]:
        count = ile_early[i]
        # Verify: after data, should be another count, -1, count or end
        end_of_data = i + 3 + count
        is_valid = True
        if end_of_data + 2 < len(ile_early):
            next_count = ile_early[end_of_data]
            # The next value should be another count (trailer of this record or start of next)
            # In Fortran format: count | data | count
            # But our pattern is: count | -1 | count | data
            # So after data, we expect count (trailer)
            # then -1 (separator)
            # then count (next header)
            pass
        first_records.append((i, count, i * 4))
        i = end_of_data
    else:
        i += 1

print(f'First record boundaries found:')
for idx, (pos, count, byte_off) in enumerate(first_records[:20]):
    fle_early = np.frombuffer(early, dtype='<f4')
    data_start = pos + 3
    data = fle_early[data_start:data_start + min(count, 10)]
    print(f'  #{idx}: int_pos={pos}, byte_offset={byte_off}, count={count}, '
          f'first_values={data.tolist()}')

# Let's also check: is the count actually byte count or item count?
# If item count: record = count(4) + sentinel(4) + count(4) + data(count*4) 
# If byte count: record = count(4) + sentinel(4) + count(4) + data(count bytes)
# count=55: 55*4=220 bytes vs 55 bytes (not 4-aligned)
# count=55 must be item count

print(f'\n{"="*70}')
print('CHECKING RECORD ALIGNMENT')
print(f'{"="*70}')
# Read a larger chunk around the 5M area and verify records are contiguous
with open(path, 'rb') as f:
    f.seek(4_999_000)
    big = f.read(1_000_000)
ile_big = np.frombuffer(big, dtype='<i4')
fle_big = np.frombuffer(big, dtype='<f4')

# Find consecutive records to verify format
recs = []
i = 0
while i < len(ile_big) - 2 and len(recs) < 100:
    if ile_big[i] > 0 and ile_big[i] < 100000 and ile_big[i + 1] == -1 and ile_big[i + 2] == ile_big[i]:
        count = ile_big[i]
        recs.append((i, count))
        i += 3 + count
    else:
        i += 1

if len(recs) >= 2:
    print(f'Found {len(recs)} consecutive records')
    # Check if records are contiguous (no gaps between them)
    for j in range(min(20, len(recs) - 1)):
        pos1, c1 = recs[j]
        pos2, c2 = recs[j + 1]
        expected_next = pos1 + 3 + c1  # right after this record's data
        gap = pos2 - expected_next
        print(f'  Rec {j}: pos={pos1}, count={c1}, end_at={expected_next}, '
              f'next_at={pos2}, gap={gap}')

# Now let's understand what each record represents
# If we know the well count and variable count, we can map the structure
print(f'\n{"="*70}')
print('IDENTIFYING RECORD MEANING')
print(f'{"="*70}')

# Read welist.bin to count wells
welist_path = r'D:\git\datafiletoolbox_samples\VIP\RKF.vdb\DNr\WELIST\welist.bin'
import re

with open(welist_path, 'rb') as f:
    wdata = f.read()

# Extract well names (8-byte padded ASCII)
well_names = []
for m in re.finditer(rb'[A-Z][A-Z0-9\-]{2,7}', wdata):
    name = m.group().decode('ascii').strip()
    if name not in well_names and len(name) >= 3:
        well_names.append(name)

print(f'Wells from welist.bin: {len(well_names)}')
print(f'First 20: {well_names[:20]}')

# From the VARDESC analysis, table #0 has ~53 variables per well
# Let's check: does any record count match n_wells * n_vars?
n_wells = len(well_names)
for count_val in sorted(set(r[1] for r in recs)):
    print(f'\n  Record count={count_val}:')
    for nv in range(1, 100):
        if count_val % nv == 0:
            nw = count_val // nv
            if 1 <= nw <= 200:
                match_w = ' <-- MATCHES WELL COUNT!' if nw == n_wells else ''
                print(f'    {nv} vars x {nw} entities = {count_val}{match_w}')
