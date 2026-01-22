#!/usr/bin/env bash
#SBATCH --job-name=coordinator
#SBATCH --account=physics
#SBATCH --partition=ada
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH -t 200:00:00
#SBATCH -e submit.err
#SBATCH -o submit.log

utilities/generate_jobs.py --num-jobs 200 --threads 1 --events 75 --results-folder /scratch/frdcol002/ipglasma/pp5020_bayesian_15k/ --input-file runs/BayesianPosteriors/inputpp5020_runWithkt --posterior-sample 1 19 > /dev/null
