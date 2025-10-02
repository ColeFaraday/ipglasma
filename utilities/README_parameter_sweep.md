# Parameter Sweep Utility

## Overview
`generate_jobs_varyings_params.py` is a utility script that generates multiple IP-Glasma simulation jobs with varying parameter values. It uses a YAML configuration file to specify which parameters to vary and their ranges.

## Features
- Vary one or more parameters across specified ranges or value lists
- Automatically generates input files for each parameter combination
- Calls `generate_jobs.py` to create job scripts for each combination
- Stores all input files in organized directories for easy debugging
- Creates a summary CSV file with all parameter combinations
- Preserves the original config file for reference

## Usage

### Basic Usage
```bash
python3 generate_jobs_varyings_params.py sweep_config.yaml
```

### Config File Format

Create a YAML file with the following structure:

```yaml
# Path to template input file (all non-varying parameters come from here)
input_template: "../runs/inputPbPb"

# Parameters to vary
vary:
  # Option 1: Range with step size
  g2mu:
    start: 0.05
    stop: 0.15
    step: 0.05
  
  # Option 2: Explicit list of values
  smearingWidth:
    values: [0.4, 0.6, 0.8]
  
  # Option 3: Range with number of points (uses linspace)
  QsmuRatio:
    start: 0.6
    stop: 1.0
    num: 5

# Job settings
job_settings:
  num_jobs: 5           # Number of job scripts per parameter combination
  threads: 8            # Threads per job
  events: 10            # Events per job
  results_folder: "results_sweep"  # Output directory
```

### Parameter Specification

For each parameter you want to vary, you can use one of three methods:

1. **Range with step**: `start`, `stop`, and `step`
   - Generates values from start to stop with given step size
   - Uses `np.arange(start, stop + step/2, step)`

2. **Explicit values**: `values`
   - Provide a list of exact values to use
   
3. **Range with count**: `start`, `stop`, and `num`
   - Generates `num` evenly-spaced values from start to stop
   - Uses `np.linspace(start, stop, num)`

## Output Structure

The script creates the following directory structure:

```
results_sweep/
├── g2mu_0p05_smearingWidth_0p4/
│   ├── input.txt                      # Modified input file for this combination
│   ├── job_0/
│   │   ├── event_0/
│   │   ├── event_1/
│   │   └── submit_job.script
│   ├── job_1/
│   └── ...
├── g2mu_0p05_smearingWidth_0p6/
│   └── ...
├── sweep_summary.csv                  # Summary of all parameter combinations
└── sweep_config.yaml                  # Copy of the config file used
```

### Summary File

The `sweep_summary.csv` contains:
- `folder`: The folder name for this combination
- `param_folder`: Full path to the parameter folder
- One column for each varied parameter with its value

Example:
```csv
folder,param_folder,g2mu,smearingWidth
g2mu_0p05_smearingWidth_0p4,/path/to/results/g2mu_0p05_smearingWidth_0p4,0.05,0.4
g2mu_0p05_smearingWidth_0p6,/path/to/results/g2mu_0p05_smearingWidth_0p6,0.05,0.6
...
```

## Example Workflow

1. Create a config file:
```bash
cp sweep_config_example.yaml my_sweep.yaml
# Edit my_sweep.yaml with your desired parameters
```

2. Run the parameter sweep:
```bash
python3 generate_jobs_varyings_params.py my_sweep.yaml
```

3. Submit all jobs:
```bash
cd results_sweep
for dir in g2mu_*/; do
    cd "$dir"
    for job in job_*/; do
        cd "$job"
        sbatch submit_job.script
        cd ..
    done
    cd ..
done
```

Or create a master submission script:
```bash
cd results_sweep
find . -name "submit_job.script" -type f | while read script; do
    dir=$(dirname "$script")
    echo "cd $dir && sbatch submit_job.script && cd -"
done > submit_all.sh
chmod +x submit_all.sh
./submit_all.sh
```

## Requirements

- Python 3.6+
- PyYAML: `pip install pyyaml`
- NumPy: `pip install numpy`
- `generate_jobs.py` must be in the same directory

## Notes

- The script will prompt before deleting an existing results folder
- All constant parameters are inherited from the template input file
- Only the varying parameters need to be specified in the config
- Folder names use `p` instead of `.` for decimal points (e.g., `0p05` for `0.05`)
