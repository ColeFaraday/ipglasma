#!/usr/bin/env bash
# Usage: ./make_array_jobs_chpc.sh <workFolder> <cores_per_job> <queue>
# Example: ./make_array_jobs_chpc.sh /path/to/sim 40 normal
# A single job script that submits many jobs in parallel

workFolder=$1
coresPerJob=$2
queue=$3

if [ -z "$workFolder" ] || [ -z "$coresPerJob" ]; then
    echo "Usage: $0 <workFolder> <cores_per_job> <queue>"
    exit 1
fi

cd "$workFolder" || exit 1

jobDirs=(job_*)
numJobs=${#jobDirs[@]}
numScripts=$(( (numJobs + coresPerJob - 1) / coresPerJob ))

echo "Creating $numScripts PBS scripts for $numJobs jobs (max $coresPerJob tasks per script)."

for (( i=0; i<numScripts; i++ )); do
    start=$(( i * coresPerJob ))
    end=$(( start + coresPerJob - 1 ))
    if [ $end -ge $numJobs ]; then
        end=$(( numJobs - 1 ))
    fi
    chunkSize=$(( end - start + 1 ))

    scriptName="submit_batch_${i}.pbs"

    # Extract slice of job directories
    slice=("${jobDirs[@]:$start:$chunkSize}")

    cat > "$scriptName" <<EOF
#!/usr/bin/env bash
#PBS -N batch_${i}
#PBS -P PHYS0974
#PBS -q ${queue}
#PBS -l select=1:ncpus=${coresPerJob}:mpiprocs=1
#PBS -l walltime=48:00:00
#PBS -V

module load chpc/fftw/3.3.6-pl1/gcc-6.1.0
module load chpc/earth/GSL/2.7
export LD_LIBRARY_PATH=\$FFTW_LIB_PATH:\$GSL_LIB_PATH:\$LD_LIBRARY_PATH
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

source /mnt/lustre/users/cfaraday/envs/iebe-music/bin/activate
cd ${workFolder} || exit 1

jobDirs=(${slice[@]})

for d in "\${jobDirs[@]}"; do
    echo "Running in \$d"
    ( cd "\$d" && bash submit_job.script ) &
done

wait
echo "All tasks finished."
EOF

    echo "  Created $scriptName handling ${chunkSize} tasks."
done