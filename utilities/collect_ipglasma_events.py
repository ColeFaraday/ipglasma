#!/usr/bin/env python3
"""Script to collect IP-Glasma event outputs into a single HDF5 file"""

import os
import sys
import h5py
import numpy as np
from glob import glob

# output files from ipglasma to save
EXPECTED_PATTERNS = [
    "NgluonEstimators0.dat",
    "NcollList0.dat",
    "NpartList0.dat",
    "usedParameters0.dat",
    "multiplicity-*.dat",
    "epsilon-u-Hydro-*.dat",
    "nkxky-*.dat"
]

def print_usage():
    print(f"Usage: {sys.argv[0]} <base_folder> <output_filename.h5>")

def collect_files(event_path):
    """Collect matching files from event folder"""
    matched_files = []
    for pattern in EXPECTED_PATTERNS:
        matched_files.extend(glob(os.path.join(event_path, pattern)))
    return matched_files

def event_name_from_path(event_path):
    """Extract 'event_N' from the full path"""
    return os.path.basename(event_path)

def save_event_to_hdf5(event_path, h5_group):
    """Save all files from event_path into h5_group"""
    files = collect_files(event_path)
    if not files:
        print(f"[WARN] No expected files found in {event_path}, skipping.")
        return

    event_name = event_name_from_path(event_path)
    g_event = h5_group.create_group(event_name)

    for file_path in files:
        file_name = os.path.basename(file_path)
        try:
            data = np.loadtxt(file_path)
        except Exception as e:
            print(f"[ERROR] Failed to read {file_path}: {e}")
            continue

        dset = g_event.create_dataset(file_name, data=data, compression="gzip", compression_opts=9)
        with open(file_path, "r") as f:
            header = f.readline()
        dset.attrs.create("header", np.bytes_(header))

def main(base_folder, output_h5_file):
    with h5py.File(output_h5_file, "w") as h5f:
        for job_folder in sorted(glob(os.path.join(base_folder, "job_*"))):
            for event_folder in sorted(glob(os.path.join(job_folder, "event_*"))):
                save_event_to_hdf5(event_folder, h5f)

    print(f"[DONE] All valid events saved to {output_h5_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    base_folder = sys.argv[1]
    output_h5 = sys.argv[2]
    main(base_folder, output_h5)