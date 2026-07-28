#!/usr/bin/env python3

import re
import sys
from pathlib import Path

import h5py
import numpy as np


pattern = re.compile(r"nkxky-t0\.4-(\d+)\.dat$")

# output file from first CLI argument
if len(sys.argv) < 2:
    raise SystemExit("Usage: python compress_nkxky.py output.h5")

output_file = Path(sys.argv[1])

# input directory = script directory
input_dir = Path(sys.argv[2])


with h5py.File(output_file, "a") as h5:
    for f in sorted(input_dir.glob("nkxky-t0.4-*.dat")):
        m = pattern.match(f.name)
        if not m:
            continue

        nnn = m.group(1)
        group_name = f"event-{nnn}"

        print(f"Processing {f} -> {group_name}")

        data = np.loadtxt(f)

        if group_name in h5:
            del h5[group_name]

        grp = h5.create_group(group_name)
        grp.create_dataset(
            "data",
            data=data,
            compression="gzip",
            compression_opts=9,
            shuffle=True,
        )

        grp.attrs["source_file"] = f.name
        grp.attrs["event_number"] = int(nnn)

        f.unlink()
        print(f"Deleted {f}")

print(f"Done: wrote {output_file}")
