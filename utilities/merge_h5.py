#!/usr/bin/env python3

from pathlib import Path
import sys
import h5py

input_dir = Path(sys.argv[1])
output_path = Path(sys.argv[2])
inputs = sorted(input_dir.glob("*.h5"))

with h5py.File(output_path, "w") as fout:
    for path in inputs:
        with h5py.File(path, "r") as fin:
            g = fout.create_group(path.stem)

            for name in fin:
                fin.copy(name, g)
