#!/usr/bin/env bash
# available partitions can be found on uct HPC website: https://hex.uct.ac.za/db/. Use ada in most circumstances.
# Adapted from https://github.com/chunshen1987/iEBE-MUSIC

usage="./submit_all_jobs.sh workFolder [queue_name]"

workFolder=$1
queue=$2

if [ -z "$workFolder" ]
then
    echo $usage
    exit 1
fi

if [ -z "$queue" ]
then
    queue="ada"
fi

echo "submit jobs in " ${workFolder}
echo ${workFolder} >> current_sims_list.txt

Numjobs=0
cd ${workFolder}
for jobdir in job_*; do
    if [ -d "$jobdir" ]; then
        echo "submit job in " ${workFolder}/${jobdir}
        cd ${jobdir}
        sbatch -q ${queue} submit_job.script | awk {'print $4'} > job_id
        cd ..
        ((Numjobs++))
    fi
done

echo "Submitted " ${Numjobs} " jobs in total. Have a nice day!"
