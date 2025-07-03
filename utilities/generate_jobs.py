#!/usr/bin/env python3

import argparse
import shutil
from pathlib import Path
import sys

def generate_jobs(num_jobs, threads_per_job, events_per_job, results_folder, input_file):
    walltime = "100:00"
    results_path = Path(results_folder).resolve()

    # Confirm and clear existing results folder
    if results_path.exists():
        response = input(f"Folder '{results_path}' already exists. Delete it? [y/N]: ").strip().lower()
        if response == 'y':
            shutil.rmtree(results_path)
        else:
            print("Aborting.")
            sys.exit(1)

    input_file_path = Path(input_file).resolve()
    qs2_input = Path("qs2Adj_vs_Tp_vs_Y_200.in").resolve()
    ipglasma_exec = Path("ipglasma").resolve()

    event_counter = 0
    for job_id in range(num_jobs):
        job_path = results_path / f"job_{job_id}"
        job_path.mkdir(parents=True, exist_ok=True)

        event_folders = []

        for _ in range(events_per_job):
            event_path = job_path / f"event_{event_counter}"
            event_path.mkdir()

            # Setup files and links
            (event_path / "ipglasma").symlink_to(ipglasma_exec)
            shutil.copy(input_file_path, event_path)
            (event_path / "qs2Adj_vs_Tp_vs_Y_200.in").symlink_to(qs2_input)

            event_folders.append(event_path.name)
            event_counter += 1

        # Write one job script to run all events in this job folder
        script_path = job_path / "submit_job.script"
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
            for event_name in event_folders:
                script.write(f"cd {event_name} && ./ipglasma {input_file_path.name} && cd ..\n")

def main():
    parser = argparse.ArgumentParser(description="Generate job/event structure for IP-Glasma submission.")
    parser.add_argument("--num-jobs", type=int, required=True, help="Number of job groups (folders with scripts)")
    parser.add_argument("--threads", type=int, required=True, help="Number of threads per job")
    parser.add_argument("--events", type=int, required=True, help="Number of events per job group")
    parser.add_argument("--results-folder", type=str, required=True, help="Top-level folder for jobs")
    parser.add_argument("--input-file", type=str, required=True, help="Path to ipglasma input file")

    args = parser.parse_args()

    generate_jobs(
        num_jobs=args.num_jobs,
        threads_per_job=args.threads,
        events_per_job=args.events,
        results_folder=args.results_folder,
        input_file=args.input_file
    )

if __name__ == "__main__":
    main()