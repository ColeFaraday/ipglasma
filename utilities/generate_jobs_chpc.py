#!/usr/bin/env python3

import argparse
import shutil
from pathlib import Path
import sys

# Constants for temperature executable and EOS folder
TEMPERATURE_EXEC_PATH = Path("/home/cfaraday/HardSoftCorrelations/IPGlasma/IPGlasma_wrapper/temperature_profile").expanduser().resolve()
FRAGMENTATION_EXEC_PATH = Path("/home/cfaraday/HardSoftCorrelations/IPGlasma/simpleFragment/ipglasma_fragment_multiple").expanduser().resolve()
SIMPLE_FRAGMENTATION_EXEC_PATH = Path("/home/cfaraday/HardSoftCorrelations/IPGlasma/simpleFragment/simpleFragment.py").expanduser().resolve()
EOS_FOLDER_PATH = Path("/home/cfaraday/HardSoftCorrelations/IPGlasma/IPGlasma_wrapper/EOS").expanduser().resolve()

def generate_jobs(num_jobs, threads_per_job, events_per_job, results_folder, input_file, delete_patterns=None, fragmentation=False, temperature=False):
    walltime = "200:00:00"
    results_path = Path(results_folder).resolve()
    print(f"[DEBUG] Resolved results_path: {results_path}")
    
    # Set default delete patterns if none provided
    if delete_patterns is None:
        delete_patterns = ["epsilon*", "Jazma-*", "eccentricities*", "run.log"]
        print(f"[DEBUG] Using default file patterns to delete after ipglasma: {delete_patterns}")
    elif delete_patterns:
        print(f"[DEBUG] File patterns to delete after ipglasma: {delete_patterns}")
    else:
        print("[DEBUG] No file patterns will be deleted after ipglasma")

    # Confirm and clear existing results folder
    if results_path.exists():
        print(f"[DEBUG] Folder '{results_path}' already exists.")
        if not sys.stdin.isatty():
            print(f"[ERROR] Folder '{results_path}' exists. Aborting (non-interactive mode).")
            sys.exit(1)
        response = input(f"Folder '{results_path}' already exists. Delete it? [y/N]: ").strip().lower()
        if response == 'y':
            print(f"[DEBUG] Deleting existing folder: {results_path}")
            shutil.rmtree(results_path)
        else:
            print("[DEBUG] Aborting due to existing folder.")
            print("Aborting.")
            sys.exit(1)
    else:
        print(f"[DEBUG] Folder '{results_path}' does not exist and will be created.")

    # Ensure the results folder exists now
    try:
        results_path.mkdir(parents=True, exist_ok=True)
        print(f"[DEBUG] Created results folder: {results_path}")
    except Exception as e:
        print(f"[ERROR] Failed to create results folder '{results_path}': {e}")
        sys.exit(1)

    input_file_path = Path(input_file).resolve()
    print(f"[DEBUG] Resolved input_file_path: {input_file_path}")
    qs2_input = Path("qs2Adj_vs_Tp_vs_Y_200.in").resolve()
    print(f"[DEBUG] Resolved qs2_input: {qs2_input}")
    ipglasma_exec = Path("ipglasma").resolve()
    print(f"[DEBUG] Resolved ipglasma_exec: {ipglasma_exec}")
    
    if fragmentation:
        ipglasma_fragment_exec = FRAGMENTATION_EXEC_PATH
        simple_fragment_exec = SIMPLE_FRAGMENTATION_EXEC_PATH
        print(f"[DEBUG] Resolved ipglasma_fragment_exec: {ipglasma_fragment_exec}")
        print(f"[DEBUG] Resolved simple_fragment_exec: {simple_fragment_exec}")
        print(f"[DEBUG] Fragmentation mode enabled")
    if temperature:
        print(f"[DEBUG] Temperature mode enabled")
        print(f"[DEBUG] Resolved temperature_profile exec: {TEMPERATURE_EXEC_PATH}")
        print(f"[DEBUG] Resolved EOS folder: {EOS_FOLDER_PATH}")

    event_counter = 0
    for job_id in range(num_jobs):
        job_path = results_path / f"job_{job_id}"
        print(f"[DEBUG] Creating job folder: {job_path}")
        job_path.mkdir(parents=True, exist_ok=True)

        event_folders = []

        for _ in range(events_per_job):
            event_path = job_path / f"event_{event_counter}"
            print(f"[DEBUG] Creating event folder: {event_path}")
            event_path.mkdir()
            # Setup files and links
            ipglasma_link = event_path / "ipglasma"
            ipglasma_fragment_link = event_path / "ipglasma_fragment_multiple"
            simple_fragment_link = event_path / "simpleFragment.py"
            qs2_link = event_path / "qs2Adj_vs_Tp_vs_Y_200.in"
            print(f"[DEBUG] Symlinking ipglasma: {ipglasma_link} -> {ipglasma_exec}")
            ipglasma_link.symlink_to(ipglasma_exec)
            print(f"[DEBUG] Copying input file: {input_file_path} -> {event_path}")
            shutil.copy(input_file_path, event_path)
            print(f"[DEBUG] Symlinking qs2 input: {qs2_link} -> {qs2_input}")
            qs2_link.symlink_to(qs2_input)
            
            # Add fragmentation executable if needed
            if fragmentation:
                ipglasma_fragment_link = event_path / "ipglasma_fragment_multiple"
                simple_fragment_link = event_path / "simpleFragment.py"
                print(f"[DEBUG] Symlinking ipglasma_fragment: {ipglasma_fragment_link} -> {ipglasma_fragment_exec}")
                ipglasma_fragment_link.symlink_to(ipglasma_fragment_exec)
                simple_fragment_link.symlink_to(simple_fragment_exec)
            # Add temperature executable and EOS folder if needed
            if temperature:
                temperature_exec_link = event_path / "temperature_profile"
                eos_link = event_path / "EOS"
                print(f"[DEBUG] Symlinking temperature_profile: {temperature_exec_link} -> {TEMPERATURE_EXEC_PATH}")
                temperature_exec_link.symlink_to(TEMPERATURE_EXEC_PATH)
                if not eos_link.exists():
                    print(f"[DEBUG] Symlinking EOS folder: {eos_link} -> {EOS_FOLDER_PATH}")
                    eos_link.symlink_to(EOS_FOLDER_PATH)
                else:
                    print(f"[DEBUG] EOS symlink already exists: {eos_link}")
            # Create symlink to nucleusConfigurations in each event folder
            nucleus_src = Path("nucleusConfigurations").resolve()
            print("Nucleus src: ", nucleus_src)
            nucleus_dst = event_path / "nucleusConfigurations"
            if not nucleus_dst.exists():
                print(f"[DEBUG] Symlinking nucleusConfigurations: {nucleus_dst} -> {nucleus_src}")
                nucleus_dst.symlink_to(nucleus_src)
            else:
                print(f"[DEBUG] nucleusConfigurations symlink already exists: {nucleus_dst}")

            event_folders.append(event_path.name)
            event_counter += 1

        # Write one job script to run all events in this job folder
        script_path = job_path / "submit_job.script"
        print(f"[DEBUG] Writing job script: {script_path}")
        with open(script_path, "w") as script:
            script.write(f"""#!/usr/bin/env bash
#PBS -N job_{job_id}
#PBS -P PHYS0974
#PBS -l select=1:ncpus={threads_per_job}:mpiprocs=1
#PBS -l walltime={walltime}
#PBS -e job.err
#PBS -o job.log
#PBS -V

module load chpc/fftw/3.3.6-pl1/gcc-6.1.0
module load chpc/earth/GSL/2.7
export LD_LIBRARY_PATH=$FFTW_LIB_PATH:$GSL_LIB_PATH:$LD_LIBRARY_PATH
cd $PBS_O_WORKDIR
source activate iEBE-MUSIC

# export OMP_NUM_THREADS={threads_per_job}
""")
            for idx, event_name in enumerate(event_folders):
                evid = job_id * events_per_job + idx
                script.write(f"cd {event_name} && ./ipglasma {input_file_path.name} 1> run.log 2> run.err\n")
                
                # Add the renaming logic using mv
                script.write(f"\n# Rename output files for event {evid}\n")
                script.write(f"evid={evid}\n")
                script.write(f"for ifile in *.dat; do\n")
                script.write(f"    filename=$(echo ${{ifile}} | sed \"s/0.dat/${{evid}}.dat/\")\n")
                script.write(f"    mv \"${{ifile}}\" \"${{filename}}\"\n")
                script.write(f"done\n")
                
                # Add fragmentation step if enabled
                if fragmentation:
                    script.write(f"\n# Run fragmentation for event {evid}\n")
                    script.write(f"./ipglasma_fragment_multiple --ff MAPFF10NLOPIsum,MAPFF10NNLOPIsum,NNFF10_PIp_nlo,NNFF10_PIsum_lo,NNFF10_PIsum_nlo,NNFF10_PIsum_nnlo,NPC23_PIsum_nlo multiplicity-t0.4-{evid}.dat")

                # Compute temperature profiles
                if temperature:
                    script.write(f"\n# Compute temperature profile for event {evid}\n")
                    # Run for each epsilon-u-Hydro-t* file
                    for tfile in ["epsilon-u-Hydro-t0.004*.dat", "epsilon-u-Hydro-t0.1*.dat", "epsilon-u-Hydro-t0.2*.dat", "epsilon-u-Hydro-t0.4*.dat"]:
                        script.write(f"./temperature_profile {tfile} --condensed\n")

                # Add file deletion logic if patterns are specified
                if delete_patterns:
                    script.write(f"\n# Delete specified file patterns for event {evid}\n")
                    # Join all patterns into a single rm command with space separation
                    patterns_str = " ".join(delete_patterns)
                    script.write(f"rm -f {patterns_str}\n")

                
                script.write(f"cd ..\n\n")
            print(f"[DEBUG] Finished writing job script for job_{job_id}")

def main():
    parser = argparse.ArgumentParser(description="Generate job/event structure for IP-Glasma submission (PBSPro version).")
    parser.add_argument("--num-jobs", type=int, required=True, help="Number of job groups (folders with scripts)")
    parser.add_argument("--threads", type=int, required=True, help="Number of threads per job")
    parser.add_argument("--events", type=int, required=True, help="Number of events per job group")
    parser.add_argument("--results-folder", type=str, required=True, help="Top-level folder for jobs")
    parser.add_argument("--input-file", type=str, required=True, help="Path to ipglasma input file")
    parser.add_argument("--delete-patterns", nargs="*", help="File patterns to delete after ipglasma finishes (e.g., '*.tmp' '*.log'). Default: --delete-patterns: 'epsilon*' 'Jazma-*' 'eccentricities*'. Use --delete-patterns with no arguments to disable deletion.")
    parser.add_argument("--fragmentation", action="store_true", help="Run ipglasma_fragment after ipglasma using multiplicity-t0.4-{evid}.dat")
    parser.add_argument("--temperature", action="store_true", help="Symlink temperature_profile and EOS folder into each event folder")

    args = parser.parse_args()
    print(f"[DEBUG] Parsed arguments: {args}")

    generate_jobs(
        num_jobs=args.num_jobs,
        threads_per_job=args.threads,
        events_per_job=args.events,
        results_folder=args.results_folder,
        input_file=args.input_file,
        delete_patterns=args.delete_patterns,
        fragmentation=args.fragmentation,
        temperature=args.temperature
    )

if __name__ == "__main__":
    main()
