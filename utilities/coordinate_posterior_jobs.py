#!/usr/bin/env python
"""
Coordinator script to sequentially submit and monitor posterior sample jobs.
Submits one posterior_sample_XXX folder at a time, waits for completion, then moves to the next.

This version can detect already-completed posterior samples and skip them.
Completion heuristic (as requested): in the first job_* folder, look at the last event_* folder
by numeric order; if it contains a file matching multiplicity-t0.4-*.dat, consider the whole
posterior_sample_* complete.
"""

import argparse
import subprocess
import time
import re
from pathlib import Path
import sys


_JOB_DIR_RE = re.compile(r"^job_(\d+)$")
_EVENT_DIR_RE = re.compile(r"^event_(\d+)$")


def _numeric_suffix(path: Path, pattern: re.Pattern):
    match = pattern.match(path.name)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def get_first_job_dir(posterior_path: Path):
    """Return the first job_* directory (by numeric order) under posterior_path, or None."""
    job_dirs = []
    for candidate in posterior_path.iterdir():
        if not candidate.is_dir():
            continue
        idx = _numeric_suffix(candidate, _JOB_DIR_RE)
        if idx is not None:
            job_dirs.append((idx, candidate))
    if not job_dirs:
        return None
    job_dirs.sort(key=lambda x: x[0])
    return job_dirs[0][1]


def get_last_event_dir(job_path: Path):
    """Return the last event_* directory (by numeric order) under job_path, or None."""
    event_dirs = []
    for candidate in job_path.iterdir():
        if not candidate.is_dir():
            continue
        idx = _numeric_suffix(candidate, _EVENT_DIR_RE)
        if idx is not None:
            event_dirs.append((idx, candidate))
    if not event_dirs:
        return None
    event_dirs.sort(key=lambda x: x[0])
    return event_dirs[-1][1]


def is_posterior_folder_completed(posterior_path: Path):
    """Determine whether a posterior_sample_* folder is already complete.

    Heuristic: first job_* dir -> last event_* dir -> presence of multiplicity-t0.4-*.dat.
    """
    first_job = get_first_job_dir(posterior_path)
    if first_job is None:
        return False

    last_event = get_last_event_dir(first_job)
    if last_event is None:
        return False

    return any(last_event.glob("multiplicity-t0.4-*.dat"))

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
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Actually submit and monitor jobs. Default is dry-run (print what would run)."
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
    print(f"[INFO] Mode: {'SUBMIT' if args.submit else 'DRY-RUN'}")
    
    # Find all posterior_sample_* folders (directories only)
    posterior_folders = sorted([f for f in base_path.glob("posterior_sample_*") if f.is_dir()])
    if not posterior_folders:
        print(f"[ERROR] No posterior_sample_* folders found in {base_path}")
        sys.exit(1)
    
    print(f"[INFO] Found {len(posterior_folders)} posterior sample folders")
    for folder in posterior_folders:
        print(f"  - {folder.name}")

    # Decide which folders still need to run
    folders_to_run = []
    skipped_folders = []
    for folder in posterior_folders:
        try:
            if is_posterior_folder_completed(folder):
                skipped_folders.append(folder)
            else:
                folders_to_run.append(folder)
        except Exception as e:
            # If detection fails, be conservative and include it to run (or at least report it).
            print(f"[WARNING] Could not determine completion for {folder.name}: {e}")
            folders_to_run.append(folder)

    print(f"[INFO] Skipping {len(skipped_folders)} completed folders")
    print(f"[INFO] Would run {len(folders_to_run)} folders")

    if not args.submit:
        if skipped_folders:
            print("\n[SKIP] Completed posterior samples:")
            for folder in skipped_folders:
                first_job = get_first_job_dir(folder)
                last_event = get_last_event_dir(first_job) if first_job else None
                detail = ""
                if first_job and last_event:
                    detail = f" (checked {first_job.name}/{last_event.name})"
                print(f"  - {folder.name}{detail}")

        print("\n[RUN] Posterior samples that would be submitted:")
        for folder in folders_to_run:
            print(f"  - {folder.name}")
        print("\n[INFO] Dry-run complete. Re-run with --submit to actually submit/monitor.")
        return
    
    # Process each posterior folder sequentially
    for idx, posterior_folder in enumerate(folders_to_run, 1):
        print(f"\n{'#'*60}")
        print(f"# Processing folder {idx}/{len(folders_to_run)}: {posterior_folder.name}")
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
