#!/usr/bin/env bash
# Intelligent job submission script that maintains a maximum number of active jobs
# and automatically submits new jobs as old ones complete
# Adapted from submit_all_jobs.sh

set -e

usage="Usage: ./submit_jobs_with_queue.sh workFolder1 [workFolder2 ...] [--queue queue_name] [--max-jobs max_active_jobs]

Arguments:
  workFolders      - One or more directories containing job_* subdirectories
  --queue          - SLURM partition/queue name (default: ada)
  --max-jobs       - Maximum number of jobs to have active at once (default: 300)

Examples:
  ./submit_jobs_with_queue.sh /path/to/results
  ./submit_jobs_with_queue.sh folder1 folder2 folder3 --queue ada --max-jobs 250
"

# Parse arguments
workFolders=()
queue="ada"
max_active_jobs=300

while [[ $# -gt 0 ]]; do
    case $1 in
        --queue)
            queue="$2"
            shift 2
            ;;
        --max-jobs)
            max_active_jobs="$2"
            shift 2
            ;;
        -h|--help)
            echo "$usage"
            exit 0
            ;;
        *)
            # Treat as work folder
            if [ -d "$1" ]; then
                workFolders+=("$(realpath "$1")")
            else
                echo "Error: Directory '$1' does not exist"
                exit 1
            fi
            shift
            ;;
    esac
done

if [ ${#workFolders[@]} -eq 0 ]; then
    echo "$usage"
    exit 1
fi

echo "========================================"
echo "Job Submission Manager"
echo "========================================"
echo "Work folders:       ${#workFolders[@]}"
for folder in "${workFolders[@]}"; do
    echo "  - $folder"
done
echo "Queue:              $queue"
echo "Max active jobs:    $max_active_jobs"
echo "========================================"

# Log this submission
for folder in "${workFolders[@]}"; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $folder" >> current_sims_list.txt
done

# Build list of all job scripts to submit from all folders
job_scripts=()
echo "Scanning for job directories..."
for workFolder in "${workFolders[@]}"; do
    echo "  Scanning $workFolder..."
    cd "$workFolder"
    for jobdir in job_*; do
        if [ -d "$jobdir" ]; then
            script_path="$workFolder/$jobdir/submit_job.script"
            if [ -f "$script_path" ]; then
                job_scripts+=("$script_path")
            else
                echo "    Warning: No submit_job.script found in $jobdir"
            fi
        fi
    done
done

total_jobs=${#job_scripts[@]}
echo "Found $total_jobs jobs to submit"

if [ $total_jobs -eq 0 ]; then
    echo "No jobs to submit. Exiting."
    exit 0
fi

# Track submitted jobs
submitted_jobs=()
submitted_count=0
next_job_index=0

# Function to get number of currently running/pending jobs submitted by this script
get_active_job_count() {
    local count=0
    for job_id in "${submitted_jobs[@]}"; do
        # Check if job still exists in queue
        if squeue -j "$job_id" &>/dev/null; then
            count=$((count + 1))
        fi
    done
    echo $count
}

# Function to clean up completed jobs from tracking array
cleanup_completed_jobs() {
    local active_jobs=()
    for job_id in "${submitted_jobs[@]}"; do
        if squeue -j "$job_id" &>/dev/null; then
            active_jobs+=("$job_id")
        fi
    done
    submitted_jobs=("${active_jobs[@]}")
}

# Function to submit a job
submit_job() {
    echo "start submit job"
    local script_path=$1
    local job_dir=$(dirname "$script_path")

    echo "job_dir: $job_dir"

    cd "$job_dir"
    local output
    output=$(sbatch -q "$queue" submit_job.script 2>&1)
    echo "sbatch output: $output"
    local exit_code=$?

    echo "exit_code: $exit_code"

    if [ $exit_code -eq 0 ]; then
        # Extract job ID from sbatch output (format: "Submitted batch job 12345")
        local job_id=$(echo "$output" | awk '{print $4}')
        echo "Submitted batch job $job_id"
        echo "$job_id" > job_id
        submitted_jobs+=("$job_id")
        echo "testing"
        submitted_count=$((submitted_count + 1))
        echo "testing"
        echo "[$(date '+%H:%M:%S')] Submitted job $submitted_count/$total_jobs (ID: $job_id) in $(basename "$job_dir")"
        return 0
    else
        echo "[$(date '+%H:%M:%S')] ERROR: Failed to submit job in $(basename "$job_dir"): $output"
        return 1
    fi
}

# Initial submission batch
echo ""
echo "========================================"
echo "Initial job submission (up to $max_active_jobs jobs)"
echo "========================================"

while [ $next_job_index -lt $total_jobs ] && [ $submitted_count -lt $max_active_jobs ]; do
    submit_job "${job_scripts[$next_job_index]}"
    next_job_index=$((next_job_index + 1))
done

# If all jobs were submitted in initial batch, we're done
if [ $next_job_index -ge $total_jobs ]; then
    echo ""
    echo "========================================"
    echo "All $total_jobs jobs submitted!"
    echo "========================================"
    exit 0
fi

# Monitor and submit remaining jobs
echo ""
echo "========================================"
echo "Monitoring jobs and submitting remaining..."
echo "========================================"
echo "Remaining jobs: $((total_jobs - next_job_index))"
echo "Checking every 60 seconds..."
echo ""

check_interval=60  # Check every 60 seconds

while [ $next_job_index -lt $total_jobs ]; do
    sleep $check_interval
    
    # Clean up completed jobs and get current count
    cleanup_completed_jobs
    active_count=$(get_active_job_count)
    
    echo "[$(date '+%H:%M:%S')] Active jobs: $active_count/$max_active_jobs | Submitted: $submitted_count/$total_jobs"
    
    # Submit new jobs if we have capacity
    while [ $active_count -lt $max_active_jobs ] && [ $next_job_index -lt $total_jobs ]; do
        submit_job "${job_scripts[$next_job_index]}"
        next_job_index=$((next_job_index + 1))
        active_count=$((active_count + 1))
    done
    
    # Check if we're done
    if [ $next_job_index -ge $total_jobs ]; then
        break
    fi
done

echo ""
echo "========================================"
echo "All $total_jobs jobs have been submitted!"
echo "========================================"
echo "Note: Jobs are still running. Use 'squeue -u \$USER' to monitor them."
echo ""
