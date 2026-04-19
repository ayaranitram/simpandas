#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VDB Binary Format Diagnostic Script
====================================
Parses plot.bin and welist.bin from a VIP/Nexus .vdb folder to
reverse-engineer the record structure.

Usage:
    python scripts/vdb_diagnostic.py <path-to-.vdb-folder>
    python scripts/vdb_diagnostic.py D:\git\datafiletoolbox_samples\VIP\RKF.vdb
"""

import os
import re
import sys
import struct
import numpy as np
from pathlib import Path
from xml.etree import ElementTree


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_fortran_records(data, offset=0, max_records=5000):
    """Walk a byte buffer reading Fortran unformatted records.

    Each record is:  [4-byte LE length] [payload] [4-byte LE length]

    Returns list of (offset, length, payload_bytes).
    """
    records = []
    pos = offset
    while pos + 4 <= len(data) and len(records) < max_records:
        head = struct.unpack_from('<i', data, pos)[0]
        if head < 0 or head > 100_000_000:  # sanity check
            break
        if pos + 4 + head + 4 > len(data):
            break
        payload = data[pos + 4: pos + 4 + head]
        tail = struct.unpack_from('<i', data, pos + 4 + head)[0]
        if head != tail:
            # not a valid Fortran record pair – stop
            break
        records.append((pos, head, payload))
        pos += 4 + head + 4
    return records, pos


def printable_preview(payload, maxlen=80):
    """Return first *maxlen* bytes as a mix of ASCII + hex."""
    parts = []
    for b in payload[:maxlen]:
        if 32 <= b < 127:
            parts.append(chr(b))
        else:
            parts.append(f'\\x{b:02x}')
    return ''.join(parts)


def extract_ascii_labels(payload, minlen=2, maxlen=8):
    """Pull out space-padded ASCII labels from a binary payload."""
    labels = re.findall(rb'([A-Z][A-Z0-9_ ]{1,7})', payload)
    out = []
    for lbl in labels:
        s = lbl.decode('ascii').strip()
        if minlen <= len(s) <= maxlen:
            out.append(s)
    return out


def extract_8byte_names(payload):
    """Extract 8-byte padded well names / labels."""
    names = []
    for i in range(0, len(payload) - 7, 8):
        chunk = payload[i:i+8]
        try:
            name = chunk.decode('ascii').strip()
        except UnicodeDecodeError:
            continue
        if name and all(c.isalnum() or c in '-_.' for c in name):
            if len(name) >= 2:
                names.append(name)
    return names


# ---------------------------------------------------------------------------
# T32/DBF header parsing
# ---------------------------------------------------------------------------

def parse_t32_header(data):
    """Check for T32 magic and extract metadata block."""
    if data[:3] != b'T32':
        print("  WARNING: No T32 magic found at start of file")
        return None

    print(f"  Magic: T32")
    # After T32, typically a Fortran record containing a metadata int
    # then another record with section table
    records, end_pos = read_fortran_records(data, offset=3, max_records=20)
    return records, end_pos


# ---------------------------------------------------------------------------
# plot.bin analysis
# ---------------------------------------------------------------------------

def analyze_plot_bin(filepath):
    """Full diagnostic analysis of a plot.bin file."""
    print(f"\n{'='*70}")
    print(f"ANALYZING: {filepath}")
    print(f"{'='*70}")

    with open(filepath, 'rb') as f:
        data = f.read()

    filesize = len(data)
    print(f"  File size: {filesize:,} bytes ({filesize/1024:.1f} KB)")

    if filesize < 100:
        print("  File too small for useful data, skipping")
        return {}

    # --- T32 header ---
    header_records = None
    data_start = 0
    if data[:3] == b'T32':
        result = parse_t32_header(data)
        if result:
            header_records, data_start = result
            print(f"  Header records found: {len(header_records)}")
            for i, (off, length, payload) in enumerate(header_records):
                preview = printable_preview(payload)
                print(f"    Record {i}: offset={off}, len={length}, preview=[{preview}]")
    else:
        print("  No T32 header")

    # --- Scan for known section markers ---
    markers = [b'VARDESC', b'VARLONG', b'RECUR', b'MASTER', b'MISC',
               b'MAPREC', b'GRIDSTAT', b'LASTMOD', b'NT', b'PERFTS',
               b'DBF', b'TIME', b'DATE', b'WELIST', b'WELLNAME']
    print(f"\n  Known section markers found:")
    marker_positions = {}
    for marker in markers:
        positions = [m.start() for m in re.finditer(re.escape(marker), data)]
        if positions:
            marker_positions[marker.decode('ascii')] = positions
            print(f"    {marker.decode('ascii'):12s}: {len(positions)} occurrence(s) at offsets {positions[:10]}")

    # --- VARDESC extraction ---
    vardesc_keys = []
    for m in re.finditer(rb'VARDESC', data):
        beg = m.end()
        end = min(beg + 4096, len(data))
        block = data[beg:end]
        labels = re.findall(rb'([A-Z][A-Z0-9]{1,7})\s{1,8}', block)
        keys = [lbl.decode('ascii').strip() for lbl in labels]
        # Filter noise: keep only labels that look like VDB keys
        keys = [k for k in keys if 2 <= len(k) <= 8]
        if keys:
            vardesc_keys.append((m.start(), keys))
            print(f"\n  VARDESC at offset {m.start()}:")
            print(f"    Keys ({len(keys)}): {keys[:40]}")

    # --- Try reading as sequential Fortran records from start ---
    print(f"\n  Attempting full Fortran record walk from byte 0...")
    all_records, final_pos = read_fortran_records(data, offset=0, max_records=10000)
    if all_records:
        print(f"    Found {len(all_records)} records, covering bytes 0..{final_pos} of {filesize}")
        # Summarize record sizes
        sizes = [r[1] for r in all_records]
        unique_sizes = sorted(set(sizes))
        print(f"    Unique record sizes: {unique_sizes[:30]}")
        size_counts = {}
        for s in sizes:
            size_counts[s] = size_counts.get(s, 0) + 1
        print(f"    Size distribution (top 15):")
        for s, c in sorted(size_counts.items(), key=lambda x: -x[1])[:15]:
            print(f"      {s:8d} bytes: {c:4d} records  ({s//4} floats)")
    else:
        print(f"    No valid Fortran records from byte 0")

    # --- Try from byte 3 (after T32) ---
    if data[:3] == b'T32' and not all_records:
        print(f"\n  Attempting Fortran record walk from byte 3 (after T32)...")
        all_records, final_pos = read_fortran_records(data, offset=3, max_records=10000)
        if all_records:
            print(f"    Found {len(all_records)} records, covering bytes 3..{final_pos} of {filesize}")
            sizes = [r[1] for r in all_records]
            unique_sizes = sorted(set(sizes))
            print(f"    Unique record sizes: {unique_sizes[:30]}")

    # --- Analyze data records (non-header) ---
    if all_records:
        print(f"\n  First 30 records detail:")
        for i, (off, length, payload) in enumerate(all_records[:30]):
            preview = printable_preview(payload, maxlen=60)
            # Try interpreting as ints and floats
            int_vals = []
            float_vals = []
            if length >= 4:
                n = min(8, length // 4)
                int_vals = list(struct.unpack_from(f'<{n}i', payload))
                float_vals = list(struct.unpack_from(f'<{n}f', payload))
            print(f"    Rec {i:4d}: off={off:8d} len={length:6d}  "
                  f"ints={int_vals}  floats=[{', '.join(f'{v:.4g}' for v in float_vals)}]  "
                  f"ascii=[{preview}]")

        # --- Look for data pattern ---
        # If many records have the same size, that's likely the data stride
        if size_counts:
            most_common_size = max(size_counts, key=size_counts.get)
            most_common_count = size_counts[most_common_size]
            if most_common_count > 5:
                print(f"\n  Most common record size: {most_common_size} bytes "
                      f"({most_common_count} records, {most_common_size//4} floats each)")
                # How many keys * wells could this represent?
                nfloats = most_common_size // 4
                print(f"    Possible interpretations:")
                for nkeys in range(1, min(50, nfloats+1)):
                    if nfloats % nkeys == 0:
                        nwells = nfloats // nkeys
                        if 1 <= nwells <= 200:
                            print(f"      {nkeys} keys × {nwells} wells = {nfloats} floats")

        # --- Look at a sample of data records taking the most common size ---
        if size_counts:
            most_common_size = max(size_counts, key=size_counts.get)
            data_recs = [(off, l, p) for off, l, p in all_records if l == most_common_size]
            if len(data_recs) > 2:
                print(f"\n  Sample data records (size={most_common_size}):")
                for idx in [0, 1, len(data_recs)//2, -1]:
                    off, l, p = data_recs[idx]
                    floats = np.frombuffer(p, dtype='<f4')
                    nonzero = np.count_nonzero(floats)
                    print(f"    Record at offset {off}: {len(floats)} floats, "
                          f"{nonzero} nonzero, min={floats.min():.4g}, max={floats.max():.4g}, "
                          f"first5={floats[:5].tolist()}")

    # --- Summary ---
    info = {
        'filesize': filesize,
        'has_t32': data[:3] == b'T32',
        'n_records': len(all_records) if all_records else 0,
        'marker_positions': marker_positions,
        'vardesc_keys': vardesc_keys,
    }
    return info


# ---------------------------------------------------------------------------
# welist.bin analysis
# ---------------------------------------------------------------------------

def analyze_welist_bin(filepath):
    """Parse welist.bin to extract well names."""
    print(f"\n{'='*70}")
    print(f"ANALYZING: {filepath}")
    print(f"{'='*70}")

    with open(filepath, 'rb') as f:
        data = f.read()

    filesize = len(data)
    print(f"  File size: {filesize:,} bytes")

    # Try T32 header
    if data[:3] == b'T32':
        print(f"  Magic: T32")
        records, end_pos = read_fortran_records(data, offset=3, max_records=200)
        print(f"  {len(records)} Fortran records found")

        all_wells = []
        for i, (off, length, payload) in enumerate(records):
            preview = printable_preview(payload, maxlen=60)
            print(f"    Record {i}: offset={off}, len={length}, preview=[{preview}]")
            # Try extracting well names
            names = extract_8byte_names(payload)
            if names:
                print(f"      Well names: {names[:20]}")
                all_wells.extend(names)

        # Deduplicate while preserving order
        seen = set()
        unique_wells = []
        for w in all_wells:
            if w not in seen:
                seen.add(w)
                unique_wells.append(w)

        print(f"\n  Total unique wells found: {len(unique_wells)}")
        print(f"  Wells: {unique_wells}")
        return unique_wells
    else:
        # Try raw 8-byte name extraction
        names = extract_8byte_names(data)
        print(f"  No T32 header, raw name extraction: {names}")
        return names


# ---------------------------------------------------------------------------
# case.ctrl analysis
# ---------------------------------------------------------------------------

def analyze_case_ctrl(filepath):
    """Parse case.ctrl for metadata."""
    print(f"\n{'='*70}")
    print(f"ANALYZING: {filepath}")
    print(f"{'='*70}")

    with open(filepath, 'rb') as f:
        data = f.read()

    print(f"  File size: {len(data):,} bytes")

    if data[:3] == b'T32':
        print(f"  Magic: T32")
        records, end_pos = read_fortran_records(data, offset=3, max_records=200)
        print(f"  {len(records)} Fortran records found")

        for i, (off, length, payload) in enumerate(records):
            preview = printable_preview(payload, maxlen=80)
            # Try as ints
            int_vals = []
            if length >= 4:
                n = min(8, length // 4)
                int_vals = list(struct.unpack_from(f'<{n}i', payload))
            print(f"    Record {i}: offset={off}, len={length}, ints={int_vals}, ascii=[{preview}]")
            # Look for section names
            labels = extract_ascii_labels(payload)
            if labels:
                print(f"      Labels: {labels}")


# ---------------------------------------------------------------------------
# main.xml analysis
# ---------------------------------------------------------------------------

def analyze_main_xml(filepath):
    """Parse main.xml to understand case hierarchy."""
    print(f"\n{'='*70}")
    print(f"ANALYZING: {filepath}")
    print(f"{'='*70}")

    try:
        tree = ElementTree.parse(filepath)
        root = tree.getroot()

        def walk_node(node, depth=0):
            tag = node.tag
            attribs = dict(node.attrib)
            text = (node.text or '').strip()
            indent = '  ' + '    ' * depth
            line = f"{indent}<{tag}"
            if attribs:
                line += f" {attribs}"
            if text:
                line += f"> {text}"
            else:
                line += ">"
            print(line)
            for child in node:
                walk_node(child, depth + 1)

        walk_node(root)
    except Exception as e:
        print(f"  ERROR parsing XML: {e}")


# ---------------------------------------------------------------------------
# VDB folder walker
# ---------------------------------------------------------------------------

def find_all_bins(vdb_path):
    """Find all .bin files and key metadata files in a .vdb folder."""
    bins = []
    for root, dirs, files in os.walk(vdb_path):
        for f in files:
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, vdb_path)
            size = os.path.getsize(fp)
            bins.append((rel, size))
    return bins


def find_deepest_plot_bin(vdb_path):
    """Find all plot.bin files and return them sorted by path depth."""
    plots = []
    for root, dirs, files in os.walk(vdb_path):
        for f in files:
            if f.lower() == 'plot.bin':
                fp = os.path.join(root, f)
                depth = fp.count(os.sep)
                plots.append((fp, depth, os.path.getsize(fp)))
    plots.sort(key=lambda x: (-x[1], -x[2]))  # deepest and largest first
    return plots


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        vdb_path = r"D:\git\datafiletoolbox_samples\VIP\RKF.vdb"
    else:
        vdb_path = sys.argv[1]

    if not os.path.exists(vdb_path):
        print(f"ERROR: Path does not exist: {vdb_path}")
        sys.exit(1)

    print(f"VDB Diagnostic Tool")
    print(f"Analyzing: {vdb_path}")

    # --- List all files ---
    all_files = find_all_bins(vdb_path)
    print(f"\n{'='*70}")
    print(f"ALL FILES IN VDB ({len(all_files)} total)")
    print(f"{'='*70}")
    for rel, size in sorted(all_files):
        print(f"  {size:>10,} bytes  {rel}")

    # --- main.xml ---
    main_xml = os.path.join(vdb_path, 'main.xml')
    if os.path.isfile(main_xml):
        analyze_main_xml(main_xml)

    # --- Find all plot.bin files ---
    plot_bins = find_deepest_plot_bin(vdb_path)
    print(f"\n  plot.bin files found ({len(plot_bins)}):")
    for fp, depth, size in plot_bins:
        print(f"    depth={depth}, size={size:>10,}, path={fp}")

    # --- Analyze largest/deepest plot.bin ---
    if plot_bins:
        # Pick the largest non-trivial plot.bin
        best = None
        for fp, depth, size in plot_bins:
            if size > 500:  # skip empty ones
                best = fp
                break
        if best:
            plot_info = analyze_plot_bin(best)
        else:
            print("\n  No plot.bin larger than 500 bytes found")
            plot_info = {}

        # Also analyze smaller ones briefly
        for fp, depth, size in plot_bins:
            if fp != best and size > 100:
                print(f"\n  --- Quick scan of {fp} (size={size}) ---")
                analyze_plot_bin(fp)

    # --- Find and analyze welist.bin files ---
    for root, dirs, files in os.walk(vdb_path):
        for f in files:
            if f.lower() == 'welist.bin':
                analyze_welist_bin(os.path.join(root, f))

    # --- Find and analyze case.ctrl files ---
    for root, dirs, files in os.walk(vdb_path):
        for f in files:
            if f.lower() == 'case.ctrl':
                analyze_case_ctrl(os.path.join(root, f))

    print(f"\n{'='*70}")
    print(f"DIAGNOSTIC COMPLETE")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
