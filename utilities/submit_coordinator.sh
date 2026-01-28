#!/usr/bin/env bash
#SBATCH --job-name=coordinator
#SBATCH --account=physics
#SBATCH --partition=ada
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH -t 200:00:00
#SBATCH -e coordinator.err
#SBATCH -o coordinator.log

# Usage: sbatch submit_coordinator.sh /path/to/base/folder [coordinator-args...]
# where base/folder contains posterior_sample_001, posterior_sample_002, etc.

if [ -z "$1" ]; then
    echo "Usage: sbatch submit_coordinator.sh /path/to/base/folder [coordinator-args...]"
    exit 1
fi

BASE_FOLDER=$1

# Get the directory where this script is located (utilities/)
SCRIPT_DIR="/home/frdcol002/hydro/IP-Glasma-only/ipglasma/utilities"

echo "Starting coordinator for: ${BASE_FOLDER}"
echo "Script directory: ${SCRIPT_DIR}"
echo "Start time: $(date)"

# Run the coordinator Python script (pass through all args)
python3 "${SCRIPT_DIR}/coordinate_posterior_jobs.py" "$@"

echo "Coordinator finished at: $(date)"
