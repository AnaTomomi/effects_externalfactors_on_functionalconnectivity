#!/bin/bash 
#SBATCH --time=4-00:00:00
#SBATCH --array=1-91
#SBATCH --mem=38G
#SBATCH --cpus-per-task=10

module load matlab

x=${SLURM_ARRAY_TASK_ID}

matlab -r "run_decode_par($x,25,2,1,'ISCout2','decode_ISCout2_25_2_1') ; exit(0)"
