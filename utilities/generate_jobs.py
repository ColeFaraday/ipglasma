#!/usr/bin/env python3

import argparse
import shutil
from pathlib import Path
import sys

def generate_jobs(num_jobs, threads_per_job, events_per_job, results_folder, input_file, delete_patterns=None):
    walltime = "100:00:00"
    results_path = Path(results_folder).resolve()
    print(f"[DEBUG] Resolved results_path: {results_path}")
    
    # Set default delete patterns if none provided
    if delete_patterns is None:
        delete_patterns = ["epsilon*", "Jazma-*", "eccentricities*"]
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
            qs2_link = event_path / "qs2Adj_vs_Tp_vs_Y_200.in"
            print(f"[DEBUG] Symlinking ipglasma: {ipglasma_link} -> {ipglasma_exec}")
            ipglasma_link.symlink_to(ipglasma_exec)
            print(f"[DEBUG] Copying input file: {input_file_path} -> {event_path}")
            shutil.copy(input_file_path, event_path)
            print(f"[DEBUG] Symlinking qs2 input: {qs2_link} -> {qs2_input}")
            qs2_link.symlink_to(qs2_input)
            # Create symlink to nucleusConfigurations in each event folder
            nucleus_src = Path(__file__).parent.parent / "nucleusConfigurations"
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
#SBATCH --job-name=job_{job_id}
#SBATCH --account=physics
#SBATCH --partition=ada
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={threads_per_job}
#SBATCH -t {walltime}
#SBATCH -e job.err
#SBATCH -o job.log

module load python/miniconda3-py3.12
source activate iEBE-MUSIC

export OMP_NUM_THREADS={threads_per_job}
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
                
                # Add file deletion logic if patterns are specified
                if delete_patterns:
                    script.write(f"\n# Delete specified file patterns for event {evid}\n")
                    for pattern in delete_patterns:
                        script.write(f"rm -f {pattern}\n")
                
                script.write(f"cd ..\n\n")
            print(f"[DEBUG] Finished writing job script for job_{job_id}")

def main():
    parser = argparse.ArgumentParser(description="Generate job/event structure for IP-Glasma submission.")
    parser.add_argument("--num-jobs", type=int, required=True, help="Number of job groups (folders with scripts)")
    parser.add_argument("--threads", type=int, required=True, help="Number of threads per job")
    parser.add_argument("--events", type=int, required=True, help="Number of events per job group")
    parser.add_argument("--results-folder", type=str, required=True, help="Top-level folder for jobs")
    parser.add_argument("--input-file", type=str, required=True, help="Path to ipglasma input file")
    parser.add_argument("--delete-patterns", nargs="*", help="File patterns to delete after ipglasma finishes (e.g., '*.tmp' '*.log'). Default: epsilon*, Jazma-*, eccentricities*. Use --delete-patterns with no arguments to disable deletion.")

    args = parser.parse_args()
    print(f"[DEBUG] Parsed arguments: {args}")

    generate_jobs(
        num_jobs=args.num_jobs,
        threads_per_job=args.threads,
        events_per_job=args.events,
        results_folder=args.results_folder,
        input_file=args.input_file,
        delete_patterns=args.delete_patterns
    )

if __name__ == "__main__":
    main()