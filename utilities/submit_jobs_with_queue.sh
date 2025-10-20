#!/usr/bin/env bash
# Intelligent job submission script that maintains a maximum number of active jobs
# and automatically submits new jobs as old ones complete
# Adapted from submit_all_jobs.sh

# Temporarily disable set -e to debug
# set -e

# Cleanup function for graceful exit
cleanup() {
    local exit_code=$?
    echo ""
    echo "========================================"
    echo "Script interrupted or completed"
    if [ -f "$active_jobs_file" ] && [ -f "$completed_jobs_file" ]; then
        local active_count=$(wc -l < "$active_jobs_file" 2>/dev/null || echo 0)
        local completed_count=$(wc -l < "$completed_jobs_file" 2>/dev/null || echo 0)
        echo "Jobs submitted this session: $submitted_count"
        echo "Currently active jobs: $active_count"
        echo "Completed jobs: $completed_count"
        echo ""
        echo "Tracking files:"
        echo "  All jobs: $all_jobs_file"
        echo "  Active jobs: $active_jobs_file"
        echo "  Completed jobs: $completed_jobs_file"
    fi
    echo "Use 'squeue -u \$USER' to monitor remaining jobs"
    echo "========================================"
    exit $exit_code
}

# Set up signal traps
trap cleanup EXIT INT TERM

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

# Define tracking files
all_jobs_file="all_jobs.txt"
completed_jobs_file="completed_jobs.txt"
active_jobs_file="active_jobs.txt"

# Track submitted jobs with persistent files
submitted_jobs=()
submitted_count=0
next_job_index=0

# Function to check if a job completed successfully
check_job_completion() {
    local job_dir=$1
    
    # Check for SLURM output files indicating successful completion
    if ls "$job_dir"/slurm-*.out &>/dev/null; then
        local latest_slurm=$(ls -t "$job_dir"/slurm-*.out 2>/dev/null | head -1)
        if [ -f "$latest_slurm" ]; then
            # Check for success patterns and absence of failure patterns
            if grep -q "COMPLETED\|SUCCESS\|Finished\|Done" "$latest_slurm" 2>/dev/null && \
               ! grep -q "FAILED\|ERROR\|TIMEOUT\|CANCELLED" "$latest_slurm" 2>/dev/null; then
                return 0  # Job completed successfully
            fi
        fi
    fi
    
    # Check for specific output files that indicate completion
    if [ -f "$job_dir/output.dat" ] || [ -f "$job_dir/results.hdf5" ] || [ -f "$job_dir/COMPLETED" ]; then
        return 0  # Job completed successfully
    fi
    
    return 1  # Job has not completed successfully
}

# Function to check if a job path is already completed
is_job_completed() {
    local job_path=$1
    grep -Fxq "$job_path" "$completed_jobs_file" 2>/dev/null
}

# Function to mark a job as completed
mark_job_completed() {
    local job_path=$1
    echo "$job_path" >> "$completed_jobs_file"
    # Remove from active jobs if present
    grep -v "^$job_path " "$active_jobs_file" > "${active_jobs_file}.tmp" 2>/dev/null || touch "${active_jobs_file}.tmp"
    mv "${active_jobs_file}.tmp" "$active_jobs_file"
}

# Function to add job to active list
add_to_active_jobs() {
    local job_path=$1
    local job_id=$2
    echo "DEBUG: Adding to active jobs: $job_path $job_id"
    echo "DEBUG: Active jobs file: $active_jobs_file"
    echo "DEBUG: Current directory: $(pwd)"
    
    # Check if we can write to the file
    if [ ! -w "$(dirname "$active_jobs_file")" ]; then
        echo "DEBUG: ERROR: Cannot write to directory $(dirname "$active_jobs_file")"
        return 1
    fi
    
    # Try to write with more detailed error reporting
    if echo "$job_path $job_id" >> "$active_jobs_file" 2>&1; then
        echo "DEBUG: Successfully added to active jobs file"
        return 0
    else
        local write_error=$?
        echo "DEBUG: ERROR: Failed to write to active jobs file, exit code: $write_error"
        echo "DEBUG: Trying to create file if it doesn't exist..."
        touch "$active_jobs_file" 2>&1 || echo "DEBUG: Failed to touch active jobs file"
        return 1
    fi
}

# Function to clean up stale active jobs
cleanup_stale_active_jobs() {
    echo "DEBUG: cleanup_stale_active_jobs called"
    if [ ! -s "$active_jobs_file" ]; then
        echo "DEBUG: Active jobs file is empty or doesn't exist, nothing to clean up"
        return
    fi
    
    echo "DEBUG: Active jobs file has content, proceeding with cleanup"
    local temp_file="${active_jobs_file}.tmp"
    
    # Create empty temp file with error checking
    if ! : > "$temp_file"; then
        echo "DEBUG: ERROR: Failed to create temp file $temp_file"
        return 1
    fi
    
    while IFS=' ' read -r job_path job_id; do
        echo "DEBUG: Checking job: $job_path $job_id"
        if [ -n "$job_id" ] && timeout 10 squeue -j "$job_id" &>/dev/null; then
            # Job is still active
            echo "DEBUG: Job $job_id is still active"
            echo "$job_path $job_id" >> "$temp_file"
        else
            # Job is no longer active - check if it completed successfully
            echo "DEBUG: Job $job_id is no longer active, checking completion"
            local job_dir=$(dirname "$job_path")
            if check_job_completion "$job_dir"; then
                echo "DEBUG: Job completed successfully, marking as completed"
                mark_job_completed "$job_path"
                echo "Marked completed job: $job_path"
            else
                echo "DEBUG: Job did not complete successfully"
            fi
        fi
    done < "$active_jobs_file"
    
    if ! mv "$temp_file" "$active_jobs_file"; then
        echo "DEBUG: ERROR: Failed to move temp file to active jobs file"
        return 1
    fi
    echo "DEBUG: cleanup_stale_active_jobs completed successfully"
}

# Function to get number of currently active jobs
get_active_job_count() {
    echo "DEBUG: get_active_job_count called"
    if cleanup_stale_active_jobs; then
        echo "DEBUG: cleanup_stale_active_jobs succeeded"
    else
        echo "DEBUG: cleanup_stale_active_jobs failed, continuing anyway"
    fi
    local count=$(wc -l < "$active_jobs_file" 2>/dev/null || echo 0)
    echo "DEBUG: Active job count: $count"
    echo $count
}

# Function to get count of completed jobs
get_completed_job_count() {
    wc -l < "$completed_jobs_file" 2>/dev/null || echo 0
}

# Initialize or load job tracking
initialize_job_tracking() {
    echo "DEBUG: Initializing job tracking..."
    # Create all_jobs.txt with full paths of all jobs to submit
    printf '%s\n' "${job_scripts[@]}" > "$all_jobs_file"
    echo "Created job list in $all_jobs_file"
    echo "DEBUG: Wrote ${#job_scripts[@]} jobs to $all_jobs_file"
    
    # Create empty files if they don't exist
    touch "$completed_jobs_file"
    touch "$active_jobs_file"
    echo "DEBUG: Created/touched tracking files"
    
    # Load previously completed jobs
    if [ -s "$completed_jobs_file" ]; then
        local completed_count=$(wc -l < "$completed_jobs_file")
        echo "Found $completed_count previously completed jobs"
        echo "DEBUG: Previously completed jobs found: $completed_count"
    else
        echo "DEBUG: No previously completed jobs found"
    fi
    
    # Clean up stale active jobs (jobs that are no longer in queue)
    echo "DEBUG: Cleaning up stale active jobs..."
    cleanup_stale_active_jobs
    echo "DEBUG: Job tracking initialization complete"
}

# Initialize job tracking
initialize_job_tracking

# Count jobs that are already completed or active
completed_count=$(get_completed_job_count)
active_count=$(get_active_job_count)
remaining_jobs=$((total_jobs - completed_count))

echo "Job status:"
echo "  Total jobs: $total_jobs"
echo "  Completed jobs: $completed_count"
echo "  Active jobs: $active_count"
echo "  Remaining jobs: $remaining_jobs"
echo ""

if [ $remaining_jobs -eq 0 ]; then
    echo "All jobs are already completed or active. Nothing to submit."
    exit 0
fi

# Function to submit a job
submit_job() {
    local script_path=$1
    local job_dir=$(dirname "$script_path")

    echo "DEBUG: submit_job called with script_path=$script_path"
    echo "DEBUG: job_dir=$job_dir"

    # Check if job is already completed
    echo "DEBUG: Checking if job is already completed..."
    if is_job_completed "$script_path"; then
        echo "[$(date '+%H:%M:%S')] Skipping already completed job: $job_dir"
        echo "DEBUG: Job was already completed, returning 2"
        return 2  # Return 2 to indicate job was skipped
    fi
    echo "DEBUG: Job not completed, proceeding..."

    # Change to job directory with error checking
    echo "DEBUG: Changing to directory $job_dir"
    if ! cd "$job_dir"; then
        echo "[$(date '+%H:%M:%S')] ERROR: Cannot access directory $job_dir"
        echo "DEBUG: Failed to change directory, returning 1"
        return 1
    fi
    echo "DEBUG: Successfully changed to directory $(pwd)"

    echo "DEBUG: About to run sbatch command..."
    local output
    output=$(sbatch -q "$queue" submit_job.script 2>&1)
    local exit_code=$?
    echo "DEBUG: sbatch exit_code=$exit_code"
    echo "DEBUG: sbatch output='$output'"

    if [ $exit_code -eq 0 ]; then
        # Extract job ID from sbatch output (format: "Submitted batch job 12345")
        local job_id=$(echo "$output" | awk '{print $4}')
        echo "DEBUG: Extracted job_id='$job_id'"
        
        # Write job ID with retry logic to handle filesystem issues
        echo "DEBUG: Writing job_id to file..."
        local retry_count=0
        local max_retries=3
        while [ $retry_count -lt $max_retries ]; do
            if echo "$job_id" > job_id 2>/dev/null; then
                echo "DEBUG: Successfully wrote job_id file"
                break
            else
                retry_count=$((retry_count + 1))
                echo "[$(date '+%H:%M:%S')] Warning: Failed to write job_id (attempt $retry_count/$max_retries) in $job_dir"
                if [ $retry_count -lt $max_retries ]; then
                    sleep 1
                fi
            fi
        done
        
        # Track the job in our persistent files
        echo "DEBUG: Adding job to active jobs list..."
        if add_to_active_jobs "$script_path" "$job_id"; then
            echo "DEBUG: Successfully added job to active jobs list"
        else
            echo "DEBUG: WARNING: Failed to add job to active jobs list, but continuing..."
        fi
        
        submitted_jobs+=("$job_id")
        submitted_count=$((submitted_count + 1))
        echo "DEBUG: Updated submitted_count to $submitted_count"
        echo "[$(date '+%H:%M:%S')] Submitted job $submitted_count/$total_jobs (ID: $job_id) in $job_dir"
        echo "DEBUG: submit_job returning 0 (success)"
        return 0
    else
        echo "[$(date '+%H:%M:%S')] ERROR: Failed to submit job in $job_dir: $output"
        echo "DEBUG: submit_job returning 1 (failure)"
        return 1
    fi
}

# Initial submission batch
echo ""
echo "========================================"
echo "Initial job submission (up to $max_active_jobs jobs)"
echo "========================================"
echo "DEBUG: Starting initial submission loop"
echo "DEBUG: next_job_index=$next_job_index, total_jobs=$total_jobs, submitted_count=$submitted_count, max_active_jobs=$max_active_jobs"

while [ $next_job_index -lt $total_jobs ] && [ $submitted_count -lt $max_active_jobs ]; do
    echo "DEBUG: Loop iteration - next_job_index=$next_job_index, submitted_count=$submitted_count"
    echo "DEBUG: About to submit job: ${job_scripts[$next_job_index]}"
    
    submit_job "${job_scripts[$next_job_index]}"
    local submit_result=$?
    
    echo "DEBUG: Submit result='$submit_result'"
    
    if [ $submit_result -eq 0 ]; then
        # Job submitted successfully
        echo "DEBUG: Job submitted successfully, incrementing counters"
        next_job_index=$((next_job_index + 1))
    elif [ $submit_result -eq 2 ]; then
        # Job was skipped (already completed)
        echo "DEBUG: Job was skipped (already completed)"
        next_job_index=$((next_job_index + 1))
    else
        # Job submission failed, skip this job and continue
        echo "[$(date '+%H:%M:%S')] Skipping failed job, continuing with next..."
        echo "DEBUG: Job submission failed"
        next_job_index=$((next_job_index + 1))
    fi
    
    echo "DEBUG: After processing - next_job_index=$next_job_index, submitted_count=$submitted_count"
    echo "DEBUG: Loop condition check: next_job_index < total_jobs = $next_job_index < $total_jobs = $((next_job_index < total_jobs))"
    echo "DEBUG: Loop condition check: submitted_count < max_active_jobs = $submitted_count < $max_active_jobs = $((submitted_count < max_active_jobs))"
done

echo "DEBUG: Exited initial submission loop"
echo "DEBUG: Final values - next_job_index=$next_job_index, submitted_count=$submitted_count"

# If all jobs were submitted in initial batch, we're done
echo "DEBUG: Checking if all jobs submitted in initial batch..."
echo "DEBUG: next_job_index=$next_job_index, total_jobs=$total_jobs"
if [ $next_job_index -ge $total_jobs ]; then
    echo ""
    echo "========================================"
    echo "All $total_jobs jobs submitted!"
    echo "========================================"
    echo "DEBUG: Exiting because all jobs were processed in initial batch"
    exit 0
fi
echo "DEBUG: Not all jobs submitted, continuing to monitoring phase..."

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
    
    # Get current counts
    active_count=$(get_active_job_count)
    completed_count=$(get_completed_job_count)
    
    echo "[$(date '+%H:%M:%S')] Active: $active_count/$max_active_jobs | Submitted: $submitted_count | Completed: $completed_count | Total: $total_jobs"
    
    # Submit new jobs if we have capacity
    while [ $active_count -lt $max_active_jobs ] && [ $next_job_index -lt $total_jobs ]; do
        submit_job "${job_scripts[$next_job_index]}"
        local submit_result=$?
        
        if [ $submit_result -eq 0 ]; then
            # Job submitted successfully
            next_job_index=$((next_job_index + 1))
            active_count=$((active_count + 1))
        elif [ $submit_result -eq 2 ]; then
            # Job was skipped (already completed)
            next_job_index=$((next_job_index + 1))
        else
            # Job submission failed, skip this job and continue
            echo "[$(date '+%H:%M:%S')] Skipping failed job, continuing with next..."
            next_job_index=$((next_job_index + 1))
        fi
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
echo "DEBUG: Script completed normally at the end"
echo ""
