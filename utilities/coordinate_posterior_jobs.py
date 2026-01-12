#!/usr/bin/env python3
"""
Coordinator script to sequentially submit and monitor posterior sample jobs.
Submits one posterior_sample_XXX folder at a time, waits for completion, then moves to the next.
"""

import argparse
import subprocess
import time
import re
from pathlib import Path
import sys

def get_running_jobs(job_ids):
    """Check which job IDs are still running/pending in slurm queue."""
    if not job_ids:
        return []
    
    try:
        # Use squeue to check job status
        result = subprocess.run(
            ['squeue', '-j', ','.join(job_ids), '-h', '-o', '%i'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            running = [jid.strip() for jid in result.stdout.strip().split('\n') if jid.strip()]
            return running
        else:
            # If squeue returns non-zero, might mean no jobs found (all finished)
            return []
    except subprocess.TimeoutExpired:
        print("[WARNING] squeue command timed out")
        return job_ids  # Assume still running to be safe
    except Exception as e:
        print(f"[WARNING] Error checking job status: {e}")
        return job_ids  # Assume still running to be safe


def collect_job_ids(posterior_folder):
    """Collect all job IDs from job_*/job_id files in the posterior folder."""
    job_ids = []
    posterior_path = Path(posterior_folder)
    
    for job_dir in sorted(posterior_path.glob("job_*")):
        job_id_file = job_dir / "job_id"
        if job_id_file.exists():
            try:
                with open(job_id_file, 'r') as f:
                    job_id = f.read().strip()
                    if job_id:
                        job_ids.append(job_id)
            except Exception as e:
                print(f"[WARNING] Could not read {job_id_file}: {e}")
    
    return job_ids


def submit_posterior_folder(posterior_folder, submit_script):
    """Submit all jobs in a posterior folder using submit_all_jobs.sh"""
    print(f"\n{'='*60}")
    print(f"[INFO] Submitting jobs in: {posterior_folder}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            [str(submit_script), str(posterior_folder)],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(result.stdout)
        if result.stderr:
            print(f"[STDERR] {result.stderr}")
        
        if result.returncode != 0:
            print(f"[ERROR] submit_all_jobs.sh returned code {result.returncode}")
            return False
        
        return True
    except Exception as e:
        print(f"[ERROR] Failed to submit jobs: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Coordinate sequential submission of posterior sample jobs"
    )
    parser.add_argument(
        "base_folder",
        help="Base folder containing posterior_sample_* directories"
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=10,
        help="Minutes between job status checks (default: 10)"
    )
    parser.add_argument(
        "--submit-script",
        default=None,
        help="Path to submit_all_jobs.sh (default: auto-detect in utilities/)"
    )
    
    args = parser.parse_args()
    
    base_path = Path(args.base_folder).resolve()
    if not base_path.exists():
        print(f"[ERROR] Base folder does not exist: {base_path}")
        sys.exit(1)
    
    # Find submit_all_jobs.sh
    if args.submit_script:
        submit_script = Path(args.submit_script).resolve()
    else:
        submit_script = Path(__file__).parent / "submit_all_jobs.sh"
    
    if not submit_script.exists():
        print(f"[ERROR] Submit script not found: {submit_script}")
        sys.exit(1)
    
    print(f"[INFO] Base folder: {base_path}")
    print(f"[INFO] Submit script: {submit_script}")
    print(f"[INFO] Check interval: {args.check_interval} minutes")
    
    # Find all posterior_sample_* folders
    posterior_folders = sorted(base_path.glob("posterior_sample_*"))
    if not posterior_folders:
        print(f"[ERROR] No posterior_sample_* folders found in {base_path}")
        sys.exit(1)
    
    print(f"[INFO] Found {len(posterior_folders)} posterior sample folders")
    for folder in posterior_folders:
        print(f"  - {folder.name}")
    
    # Process each posterior folder sequentially
    for idx, posterior_folder in enumerate(posterior_folders, 1):
        print(f"\n{'#'*60}")
        print(f"# Processing folder {idx}/{len(posterior_folders)}: {posterior_folder.name}")
        print(f"{'#'*60}")
        
        # Submit jobs
        success = submit_posterior_folder(posterior_folder, submit_script)
        if not success:
            print(f"[ERROR] Failed to submit {posterior_folder.name}, stopping coordinator")
            sys.exit(1)
        
        # Give slurm a moment to register the jobs
        time.sleep(30)
        
        # Collect job IDs
        job_ids = collect_job_ids(posterior_folder)
        print(f"[INFO] Monitoring {len(job_ids)} jobs: {job_ids}")
        
        if not job_ids:
            print(f"[WARNING] No job IDs found for {posterior_folder.name}, moving to next folder")
            continue
        
        # Monitor until all jobs complete
        check_count = 0
        while True:
            running_jobs = get_running_jobs(job_ids)
            check_count += 1
            
            if not running_jobs:
                print(f"[INFO] All jobs completed for {posterior_folder.name}")
                break
            
            print(f"[CHECK #{check_count}] {len(running_jobs)}/{len(job_ids)} jobs still running at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Wait before next check
            time.sleep(args.check_interval * 60)
    
    print(f"\n{'='*60}")
    print("[SUCCESS] All posterior sample folders processed!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
