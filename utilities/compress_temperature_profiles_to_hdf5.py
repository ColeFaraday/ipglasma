#!/usr/bin/env python3
"""
This script compresses temperature profile files from a parent folder structure
into a single HDF5 file.

Expected structure: parent_folder/job_n/event_m/temperature_profile_file.dat
Output: parent_folder.h5 with groups job_n/event_m/{x, y, epsilon, temperature, pressure}

Usage:
    python compress_temperature_profiles_to_hdf5.py parent_folder [--output output.h5] [--pattern "*.dat"]
"""

import argparse
import os
import sys
from pathlib import Path
import numpy as np
import h5py
from glob import glob


def find_temperature_files(parent_folder, pattern="epsilon-u-Hydro*.dat"):
    """
    Find all temperature profile files in the parent_folder/job_*/event_* structure.
    
    Returns:
        dict: {(job_n, event_m): filepath, ...}
    """
    files_dict = {}
    parent_path = Path(parent_folder)
    
    # Search for job_* directories
    for job_dir in sorted(parent_path.glob("job_*")):
        if not job_dir.is_dir():
            continue
        
        job_name = job_dir.name
        
        # Search for event_* directories within each job_*
        for event_dir in sorted(job_dir.glob("event_*")):
            if not event_dir.is_dir():
                continue
            
            event_name = event_dir.name
            
            # Find temperature profile files
            temp_files = list(event_dir.glob(pattern))
            if temp_files:
                # Take the first matching file
                files_dict[(job_name, event_name)] = temp_files[0]
    
    return files_dict


def parse_temperature_file(filepath):
    """
    Parse temperature profile file and return data arrays.
    
    Expected columns:
    0: dummy (skip)
    1: x
    2: y
    3: epsilon (GeV/fm^3)
    4: temperature (MeV)
    5: temperature_freezeout (MeV) - skip
    6: pressure (GeV/fm^3)
    
    Returns:
        dict: {'x': array, 'y': array, 'epsilon': array, 'temperature': array, 'pressure': array}
    """
    # Read the data, skipping comment lines
    try:
        data = np.loadtxt(filepath, comments='#', dtype=np.float32)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None
    
    if data.size == 0:
        print(f"Warning: {filepath} is empty")
        return None
    
    # Extract columns (skip dummy and temperature_freezeout)
    result = {
        'x': data[:, 1],
        'y': data[:, 2],
        'epsilon': data[:, 3],
        'temperature': data[:, 4],
        'pressure': data[:, 6]
    }
    
    return result


def compress_to_hdf5(parent_folder, output_file, pattern="epsilon-u-Hydro*.dat"):
    """
    Main function to compress all temperature profile files into a single HDF5 file.
    """
    print(f"Searching for temperature files in: {parent_folder}")
    print(f"Pattern: {pattern}")
    
    # Find all temperature files
    files_dict = find_temperature_files(parent_folder, pattern)
    
    if not files_dict:
        print("Error: No temperature files found!")
        print(f"Expected structure: {parent_folder}/job_*/event_*/{pattern}")
        return False
    
    print(f"Found {len(files_dict)} temperature profile files")
    
    # Create HDF5 file
    print(f"Creating HDF5 file: {output_file}")
    
    with h5py.File(output_file, 'w') as hf:
        processed = 0
        failed = 0
        
        for (job_name, event_name), filepath in sorted(files_dict.items()):
            group_path = f"{job_name}/{event_name}"
            
            # Parse the temperature file
            data = parse_temperature_file(filepath)
            
            if data is None:
                failed += 1
                continue
            
            # Create group and store datasets
            try:
                group = hf.create_group(group_path)
                
                for key, array in data.items():
                    group.create_dataset(key, data=array, dtype=np.float32, compression='gzip')
                
                # Store metadata
                group.attrs['source_file'] = str(filepath.name)
                group.attrs['n_points'] = len(data['x'])
                
                processed += 1
                
                if processed % 100 == 0:
                    print(f"Processed {processed}/{len(files_dict)} files...")
                    
            except Exception as e:
                print(f"Error processing {group_path}: {e}")
                failed += 1
    
    print(f"\nCompression complete!")
    print(f"Successfully processed: {processed}")
    print(f"Failed: {failed}")
    print(f"Output file: {output_file}")
    
    # Print file size info
    if os.path.exists(output_file):
        size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"Output file size: {size_mb:.2f} MB")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Compress temperature profile files into a single HDF5 file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /scratch/frdcol002/ipglasma/PbPb5020_bayesian_batch_1
  %(prog)s /scratch/frdcol002/ipglasma/PbPb5020_bayesian_batch_1 --output custom_name.h5
  %(prog)s parent_folder --pattern "temperature*.dat"
        """
    )
    
    parser.add_argument('parent_folder', type=str,
                        help='Parent folder containing job_*/event_* structure')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output HDF5 file (default: parent_folder.h5)')
    parser.add_argument('--pattern', '-p', type=str, default='epsilon-u-Hydro*.dat',
                        help='File pattern to match (default: epsilon-u-Hydro*.dat)')
    
    args = parser.parse_args()
    
    # Validate parent folder
    if not os.path.isdir(args.parent_folder):
        print(f"Error: '{args.parent_folder}' is not a valid directory")
        return 1
    
    # Determine output filename
    if args.output:
        output_file = args.output
    else:
        parent_name = Path(args.parent_folder).name
        output_file = f"{parent_name}.h5"
    
    # Run compression
    success = compress_to_hdf5(args.parent_folder, output_file, args.pattern)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
