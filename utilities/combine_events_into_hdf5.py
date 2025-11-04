#!/usr/bin/env python
"""
     This script combines pre-generated IP-Glasma events into a hdf5 database.
"""

import sys
import h5py
from os import path, remove, system
from glob import glob
from multiprocessing import Pool
import argparse

import numpy as np

def print_help():
    """This function prints out help message"""
    print("{0} results_folder".format(sys.argv[0]))

def collect_one_IPGlasma_event(event_folder, event_id, hf, deleteFlag=False, include_patterns=None):
    """This function collects one IPGlasma event from a given event folder"""
    print(f"[DEBUG] Processing event_id={event_id} in folder={event_folder}")
    # Always include usedParameters file as attributes
    file_name = f"usedParameters{event_id}.dat"
    parafilename = path.join(event_folder, file_name)
    print(f"[DEBUG] Looking for parameter file: {parafilename}")
    if not path.exists(parafilename):
        print(f"Error: can not find file : {parafilename}")
        exit(1)

    group_name = f"event-{event_id}"
    print(f"[DEBUG] Attempting to create group: {group_name}")
    try:
        gtemp = hf.create_group(group_name)
        print(f"[DEBUG] Group created: {group_name}")
    except Exception as e:
        print(f"[ERROR] Could not create group '{group_name}': {e}")
        if group_name in hf:
            print(f"[DEBUG] Group '{group_name}' already exists in HDF5 file.")
        raise
    with open(parafilename) as parafile:
        for iline, rawline in enumerate(parafile.readlines()):
            paraline = rawline.strip('\n')
            gtemp.attrs.create(f"{iline}", np.bytes_(paraline))
    if deleteFlag: remove(parafilename)

    # Default patterns if not provided
    if include_patterns is None:
        include_patterns = [
            f"NcollList{event_id}.dat",
            f"NpartList{event_id}.dat",
            f"NpartdNdy-t*-{event_id}.dat",
            f"NgluonEstimators{event_id}.dat", 
            f"meanpt{event_id}.dat",
            f"multiplicity-t*-{event_id}.dat",
            f"multiplicityHadrons{event_id}.dat",
            f"hadron_spectrum_hessian_*.dat",
            # f"epsilon-u-Hydro-t*-{event_id}.dat",
            # f"Tmunu-t*-{event_id}.dat"
        ]

    # Loop over all patterns
    for pattern in include_patterns:
        filelist = glob(path.join(event_folder, pattern))
        for filepath in filelist:
            filename = filepath.split("/")[-1]
            if filename in gtemp:
                print(f"[DEBUG] Dataset '{filename}' already exists in group '{group_name}', skipping.")
                continue
            print(f"[DEBUG] Creating dataset for: {filename}")
            try:
                # Custom logic for each file type
                if filename.startswith("NcollList"):
                    dtemp = np.loadtxt(filepath)
                    dtemp = np.nan_to_num(dtemp).reshape(-1, 2)
                    dset = gtemp.create_dataset(filename, data=dtemp, compression="gzip", compression_opts=9)
                elif filename.startswith("NpartList"):
                    dtemp = np.loadtxt(filepath)
                    dtemp = np.nan_to_num(dtemp).reshape(-1, 4)
                    dset = gtemp.create_dataset(filename, data=dtemp, compression="gzip", compression_opts=9)
                elif filename.startswith("NpartdNdyHadrons-t") or filename.startswith("NpartdNdy-t"):
                    dtemp = np.genfromtxt(filepath, dtype='str')
                    data = np.zeros(len(dtemp))
                    for idx in range(len(dtemp)):
                        try:
                            data[idx] = float(dtemp[idx])
                        except Exception:
                            data[idx] = 0.0
                    dset = gtemp.create_dataset(filename, data=data, compression="gzip", compression_opts=9)
                elif filename.startswith("epsilon-u-Hydro-t"):
                    dtemp = np.loadtxt(filepath)
                    dtemp = np.nan_to_num(dtemp)
                    x_size = abs(dtemp[0, 1])*2.
                    y_size = abs(dtemp[0, 2])*2.
                    data_cut = dtemp[:, 3:]
                    dset = gtemp.create_dataset(filename, data=data_cut, compression="gzip", compression_opts=9)
                    with open(filepath) as f:
                        header = f.readline().strip('\n')
                    dset.attrs.create("header", np.bytes_(header))
                    tmp = header.split()
                    try:
                        dx = float(tmp[12])
                        dy = float(tmp[14])
                        nx = int(tmp[6])
                        ny = int(tmp[8])
                        dset.attrs.create("x_size", x_size)
                        dset.attrs.create("y_size", y_size)
                        dset.attrs.create("dx", dx)
                        dset.attrs.create("dy", dy)
                        dset.attrs.create("nx", nx)
                        dset.attrs.create("ny", ny)
                    except Exception:
                        pass
                elif filename.startswith("Tmunu-t"):
                    dtemp = np.loadtxt(filepath)
                    dtemp = np.nan_to_num(dtemp)
                    x_size = abs(dtemp[0, 1])*2.
                    y_size = abs(dtemp[0, 2])*2.
                    data_cut = dtemp[:, 2:]
                    dset = gtemp.create_dataset(filename, data=data_cut, compression="gzip", compression_opts=9)
                    with open(filepath) as f:
                        header = f.readline().strip('\n')
                    dset.attrs.create("header", np.bytes_(header))
                    tmp = header.split()
                    try:
                        dx = float(tmp[12])
                        dy = float(tmp[14])
                        nx = int(tmp[6])
                        ny = int(tmp[8])
                        dset.attrs.create("x_size", x_size)
                        dset.attrs.create("y_size", y_size)
                        dset.attrs.create("dx", dx)
                        dset.attrs.create("dy", dy)
                        dset.attrs.create("nx", nx)
                        dset.attrs.create("ny", ny)
                    except Exception:
                        pass
                elif filename.startswith("multiplicity-t") or filename.startswith("meanpt") or filename.startswith("nkxky-t") or filename.startswith("eccentricities") or filename.startswith("NgluonEstimators"):
                    dtemp = np.loadtxt(filepath)
                    dtemp = np.nan_to_num(dtemp)
                    dset = gtemp.create_dataset(filename, data=dtemp, compression="gzip", compression_opts=9)
                else:
                    # Try to load as float, fallback to string
                    try:
                        dtemp = np.loadtxt(filepath)
                        dtemp = np.nan_to_num(dtemp)
                        dset = gtemp.create_dataset(filename, data=dtemp, compression="gzip", compression_opts=9)
                    except Exception:
                        with open(filepath) as f:
                            content = f.read()
                        dset = gtemp.create_dataset(filename, data=np.string_(content), compression="gzip", compression_opts=9)
                print(f"[DEBUG] Dataset created: {filename}")
            except Exception as e:
                print(f"[ERROR] Could not create dataset '{filename}': {e}")
                if filename in gtemp:
                    print(f"[DEBUG] Dataset '{filename}' already exists in group '{group_name}'.")
                raise
            if deleteFlag: remove(filepath)


def collect_IPGlasma_events(results_folder, include_patterns=None):
    """This function collects IPGlasma events in results_folder (recursive for job/event structure)"""
    import glob as _glob
    results_name = results_folder.split("/")[-1]
    if results_name == "":
        results_name = results_folder.split("/")[-2]
    results_path = path.abspath(path.join(".", results_folder))
    # Recursively find all usedParameters*.dat files in job_*/event_*/
    event_param_files = _glob.glob(path.join(results_path, "job_*/event_*/usedParameters*.dat"), recursive=True)
    nev = len(event_param_files)

    print("collect {0} to {1}.h5 ... ".format(results_folder, results_name))
    hf = h5py.File("{0}.h5".format(results_name), "w")

    for ievent, event_param_path in enumerate(event_param_files):
        print("processing {0:d}/{1:d} ... ".format(ievent+1, nev))
        event_folder = path.dirname(event_param_path)
        event_id = event_param_path.split("usedParameters")[-1].split(".dat")[0]
        collect_one_IPGlasma_event(event_folder, event_id, hf, include_patterns=include_patterns)


def collect_IPGlasma_events_MPI(results_folder, include_patterns=None):
    """This function collects IPGlasma events in results_folder with MPI"""
    from mpi4py import MPI
    mpi_comm = MPI.COMM_WORLD
    mpi_rank = mpi_comm.Get_rank()
    mpi_size = mpi_comm.Get_size()

    if mpi_rank == 0:
        print("MPI using {} threads ...".format(mpi_size))

    results_name = results_folder.split("/")[-1]
    if results_name == "":
        results_name = results_folder.split("/")[-2]
    results_path = path.abspath(path.join(".", results_folder))
    event_list = glob(path.join(results_path, "usedParameters*.dat"))
    nev = len(event_list)

    h5filename = "{0}_rank{1}.h5".format(results_name, mpi_rank)
    print("MPI rank {0}: collect {1} to {2} ... ".format(
        mpi_rank, results_folder, h5filename))
    hf = h5py.File(h5filename, "w")
    mpi_comm.Barrier()
    for ievent in range(nev):
        if mpi_rank == ievent%mpi_size:
            event_path = event_list[ievent]
            print("MPI rank {0:d} processing {1:d}/{2:d} ... ".format(
                mpi_rank, ievent, nev))
            event_id = (
                event_path.split("/")[-1].split("Parameters")[-1].split(".dat")[0]
            )
            collect_one_IPGlasma_event(path.dirname(event_path), event_id, hf, include_patterns=include_patterns)
    hf.close()
    mpi_comm.Barrier()

    # now combine all the hdf5 files into one using rank 0
    if mpi_rank == 0:
        combine_hdf5_files_into_one(".", results_name)


def combine_hdf5_files_into_one(results_path, results_name):
    print("combining to one hdf5 file {}.h5 ...".format(results_name))
    h5_filelist = (
            glob(path.join(results_path, "{}_rank*.h5".format(results_name))))
    for filename in h5_filelist:
        print("processing {0} ... ".format(filename))
        hftemp = h5py.File(filename, "r")
        glist = list(hftemp.keys())
        hftemp.close()
        for gtemp in glist:
            system('h5copy -i {0} -o {1}.h5 -s {2} -d {2}'.format(
                   filename, results_name, gtemp))
        remove(filename)


def collect_one_event_to_h5database(results_folder, event_id, database_name,
                                    deleteFlag=False, include_patterns=None):
    results_path = path.abspath(path.join(".", results_folder))
    print("collecting event {} from {} to {}.h5  ... ".format(
                                    event_id, results_folder, database_name))
    hf = h5py.File("{}.h5".format(database_name), "a")
    collect_one_IPGlasma_event(results_path, event_id, hf, deleteFlag, include_patterns)
    hf.close()


def main():
    """This is the main funciton"""
    parser = argparse.ArgumentParser(
            description='\U0000269B IPGlasma Output Collector',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('results_folder_name',
                        type=str,
                        help='results folder path')

    parser.add_argument('-MPI', '--MPI_flag', action='store_true',
                        help='enable MPI')

    parser.add_argument('--output_filename',
                        type=str, default="RESULTS",
                        help="output file name")

    parser.add_argument('--event_id',
                        type=int, default=-1,
                        help="collect event id")

    parser.add_argument('--combine_hdf5_files_only', action='store_true',
                        help='flag to combine hdf5 files under results_folder')

    parser.add_argument('--include_files', type=str, default=None,
                        help='Comma-separated list of file patterns to include (e.g. "NpartdNdyHadrons*,multiplicity*,meanpt*,nkxky*,eccentricities*,NgluonEstimators*")')

    args = parser.parse_args()

    include_patterns = None
    if args.include_files:
        include_patterns = [pat.strip() for pat in args.include_files.split(",") if pat.strip()]

    if args.combine_hdf5_files_only:
        combine_hdf5_files_into_one(args.results_folder_name,
                                    args.output_filename)
        return

    if args.event_id >= 0:
        deleteFlag = True
        collect_one_event_to_h5database(
                args.results_folder_name, args.event_id, args.output_filename,
                deleteFlag, include_patterns)
    else:
        if args.MPI_flag:
            collect_IPGlasma_events_MPI(args.results_folder_name, include_patterns)
        else:
            collect_IPGlasma_events(args.results_folder_name, include_patterns)


if __name__ == "__main__":
    main()
