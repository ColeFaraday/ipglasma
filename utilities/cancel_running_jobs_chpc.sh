#!/usr/bin/env bash
# From https://github.com/chunshen1987/iEBE-MUSIC
# Extended to handle multiple folders

usage="Usage: ./cancel_running_jobs.sh folder1 [folder2 folder3 ...]

Arguments:
  folders - One or more directories containing job_* subdirectories

Examples:
  ./cancel_running_jobs.sh /path/to/results
  ./cancel_running_jobs.sh folder1 folder2 folder3"

if [ $# -eq 0 ]; then
    echo "$usage"
    exit 1
fi

# Function to cancel jobs in a single folder
cancel_jobs_in_folder() {
    local jobFolder=$1
    jobFolder=${jobFolder%"/"}
    
    if [ ! -d "$jobFolder" ]; then
        echo "Warning: Directory '$jobFolder' does not exist, skipping..."
        return 1
    fi
    
    echo "Cancelling jobs in $jobFolder"
    
    local job_count=0
    local cancelled_count=0
    
    for ijob in $(ls --color=none "$jobFolder" 2>/dev/null | grep "^job"); do
        eventsPath="$jobFolder/$ijob"
        if [ -f "$eventsPath/job_id" ]; then
            local job_id=$(cat "$eventsPath/job_id")
            if [ -n "$job_id" ]; then
                echo "  Cancelling job $job_id in $ijob"
                if qdel "$job_id" 2>/dev/null; then
                    cancelled_count=$((cancelled_count + 1))
                else
                    echo "    Warning: Failed to cancel job $job_id (may have already finished)"
                fi
            else
                echo "    Warning: Empty job_id file in $ijob"
            fi
        else
            echo "    Warning: No job_id file found in $ijob"
        fi
        job_count=$((job_count + 1))
    done
    
    if [ $job_count -eq 0 ]; then
        echo "  No job directories found in $jobFolder"
    else
        echo "  Processed $job_count job directories, cancelled $cancelled_count jobs"
    fi
}

# Process all provided folders
total_folders=$#
processed_folders=0

echo "========================================"
echo "Job Cancellation Script"
echo "========================================"
echo "Processing $total_folders folder(s)..."
echo ""

for jobFolder in "$@"; do
    processed_folders=$((processed_folders + 1))
    echo "[$processed_folders/$total_folders] Processing: $jobFolder"
    cancel_jobs_in_folder "$jobFolder"
    echo ""
done

echo "========================================"
echo "Job cancellation complete!"
echo "========================================"

