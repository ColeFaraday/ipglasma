#!/usr/bin/env bash
# Usage: ./make_array_jobs_chpc.sh <workFolder> <cores_per_job>
# Example: ./make_array_jobs_chpc.sh /path/to/sim 40

workFolder=$1
coresPerJob=$2

if [ -z "$workFolder" ] || [ -z "$coresPerJob" ]; then
    echo "Usage: $0 <workFolder> <cores_per_job>"
    exit 1
fi

cd "$workFolder" || exit 1

jobDirs=(job_*)
numJobs=${#jobDirs[@]}
numScripts=$(( (numJobs + coresPerJob - 1) / coresPerJob ))

echo "Creating $numScripts PBS array scripts for $numJobs jobs (max $coresPerJob per array job)."

for (( i=0; i<numScripts; i++ )); do
    start=$(( i * coresPerJob ))
    end=$(( start + coresPerJob - 1 ))
    if [ $end -ge $numJobs ]; then
        end=$(( numJobs - 1 ))
    fi
    chunkSize=$(( end - start + 1 ))

    scriptName="submit_array_${i}.pbs"
    cat > "$scriptName" <<EOF
#!/usr/bin/env bash
#PBS -N batch_${i}
#PBS -P PHYS0974
#PBS -l select=1:ncpus=${chunkSize}:mpiprocs=${chunkSize}
#PBS -l walltime=48:00:00
#PBS -J 0-$((chunkSize - 1))
#PBS -V

module load chpc/fftw/3.3.6-pl1/gcc-6.1.0
module load chpc/earth/GSL/2.7
export LD_LIBRARY_PATH=\$FFTW_LIB_PATH:\$GSL_LIB_PATH:\$LD_LIBRARY_PATH

source /mnt/lustre/users/cfaraday/envs/iebe-music/bin/activate
cd ${workFolder} || exit 1

jobDirs=(${jobDirs[@]:$start:$chunkSize})
jobDir=\${jobDirs[\$PBS_ARRAY_INDEX]}

cd "\$jobDir" || exit 1
echo "Running in \$jobDir"
bash submit_job.script
EOF

    echo "  Created $scriptName with $chunkSize array elements."
done