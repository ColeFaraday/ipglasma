#!/usr/bin/env bash
#SBATCH --job-name=processAll
#SBATCH --account=physics
#SBATCH --partition=ada
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=20
#SBATCH -t 200:00:00
#SBATCH -e processAll.err
#SBATCH -o processAll.log


# Usage: sbatch process_all_posterior_jobs.sh /path/to/base/folder

if [ -z "$1" ]; then
		echo "Usage: sbatch process_all_posterior_jobs.sh /path/to/base/folder"
		exit 1
fi

BASE_FOLDER=$1

# Run a command for each folder 

for POSTERIOR_DIR in "${BASE_FOLDER}"/posterior_sample_*/; do
		/home/frdcol002/hydro/IP-Glasma-only/ipglasma/utilities/combine_events_into_hdf5.py "${POSTERIOR_DIR}" &
done



