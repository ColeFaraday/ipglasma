#!/usr/bin/env python3

import argparse
import yaml
import numpy as np
import itertools
import subprocess
from pathlib import Path
import shutil
import csv
import sys

def parse_input_file(input_file_path):
    """Parse an IP-Glasma input file and return a dictionary of parameters."""
    params = {}
    with open(input_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line == 'EndOfFile':
                break
            parts = line.split()
            if len(parts) >= 2:
                key = parts[0]
                value = ' '.join(parts[1:])
                params[key] = value
    return params

def write_input_file(output_path, params):
    """Write parameters to an IP-Glasma input file."""
    with open(output_path, 'w') as f:
        for key, value in params.items():
            f.write(f"{key}  {value}\n")
        f.write("EndOfFile\n")

def generate_parameter_values(param_spec):
    """Generate a list of values for a parameter based on its specification."""
    if 'values' in param_spec:
        # Explicit list of values
        return param_spec['values']
    elif 'start' in param_spec and 'stop' in param_spec:
        # Range specification
        start = param_spec['start']
        stop = param_spec['stop']
        step = param_spec.get('step', None)
        num = param_spec.get('num', None)
        
        if step is not None:
            # Use arange with step
            values = np.arange(start, stop + step/2, step)
        elif num is not None:
            # Use linspace with num points
            values = np.linspace(start, stop, num)
        else:
            raise ValueError(f"Must specify either 'step' or 'num' for range: {param_spec}")
        
        return values.tolist()
    else:
        raise ValueError(f"Invalid parameter specification: {param_spec}")

def generate_parameter_combinations(vary_spec):
    """Generate all combinations of varying parameters."""
    param_names = []
    param_values_lists = []
    
    for param_name, param_spec in vary_spec.items():
        param_names.append(param_name)
        param_values_lists.append(generate_parameter_values(param_spec))
    
    # Generate Cartesian product of all parameter values
    combinations = list(itertools.product(*param_values_lists))
    
    # Convert to list of dictionaries
    param_combinations = []
    for combo in combinations:
        param_dict = {name: value for name, value in zip(param_names, combo)}
        param_combinations.append(param_dict)
    
    return param_combinations

def create_folder_name(param_dict):
    """Create a descriptive folder name from parameter values."""
    parts = []
    for key, value in sorted(param_dict.items()):
        # Format the value nicely
        if isinstance(value, float):
            value_str = f"{value:.4g}".replace('.', 'p')
        else:
            value_str = str(value).replace('.', 'p')
        parts.append(f"{key}_{value_str}")
    return "_".join(parts)

def generate_jobs_with_varying_params(config_path):
    """Main function to generate jobs with varying parameters."""
    
    # Load config file
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Extract configuration
    input_template_path = Path(config['input_template']).resolve()
    vary_spec = config.get('vary', {})
    job_settings = config['job_settings']
    
    results_folder = Path(job_settings['results_folder']).resolve()
    num_jobs = job_settings['num_jobs']
    threads = job_settings['threads']
    events = job_settings['events']
    
    print(f"[INFO] Using template: {input_template_path}")
    print(f"[INFO] Results folder: {results_folder}")
    
    # Check if results folder exists
    if results_folder.exists():
        response = input(f"Folder '{results_folder}' already exists. Delete it? [y/N]: ").strip().lower()
        if response == 'y':
            shutil.rmtree(results_folder)
            print(f"[INFO] Deleted existing folder: {results_folder}")
        else:
            print("[INFO] Aborting.")
            sys.exit(1)
    
    # Create results folder
    results_folder.mkdir(parents=True, exist_ok=True)
    
    # Parse template input file
    base_params = parse_input_file(input_template_path)
    print(f"[INFO] Parsed {len(base_params)} parameters from template")
    
    # Generate parameter combinations
    param_combinations = generate_parameter_combinations(vary_spec)
    print(f"[INFO] Generated {len(param_combinations)} parameter combinations")
    
    # Store summary information
    summary_data = []
    
    # Get the path to generate_jobs.py
    generate_jobs_script = Path(__file__).parent / "generate_jobs.py"
    
    # For each parameter combination
    for idx, param_dict in enumerate(param_combinations):
        # Create folder name
        folder_name = create_folder_name(param_dict)
        param_folder = results_folder / folder_name
        param_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"\n[INFO] Processing combination {idx+1}/{len(param_combinations)}: {folder_name}")
        
        # Create modified input file
        modified_params = base_params.copy()
        for param_name, param_value in param_dict.items():
            modified_params[param_name] = str(param_value)
        
        # Write input file to the parameter folder
        input_file_name = "input.txt"
        input_file_path = param_folder / input_file_name
        write_input_file(input_file_path, modified_params)
        print(f"[INFO] Created input file: {input_file_path}")
        
        # Call generate_jobs.py
        cmd = [
            "python3",
            str(generate_jobs_script),
            "--num-jobs", str(num_jobs),
            "--threads", str(threads),
            "--events", str(events),
            "--results-folder", str(param_folder) + "/results",
            "--input-file", str(input_file_path)
        ]
        
        print(f"[INFO] Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[ERROR] Failed to generate jobs for {folder_name}")
            print(f"[ERROR] stdout: {result.stdout}")
            print(f"[ERROR] stderr: {result.stderr}")
            sys.exit(1)
        
        # Add to summary
        summary_entry = {
            'folder': folder_name,
            'param_folder': str(param_folder),
            **param_dict
        }
        summary_data.append(summary_entry)
    
    # Write summary CSV
    summary_path = results_folder / "sweep_summary.csv"
    if summary_data:
        fieldnames = ['folder', 'param_folder'] + list(vary_spec.keys())
        with open(summary_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_data)
        print(f"\n[INFO] Wrote summary to: {summary_path}")
    
    # Copy config file to results folder for reference
    config_copy_path = results_folder / "sweep_config.yaml"
    shutil.copy(config_path, config_copy_path)
    print(f"[INFO] Copied config to: {config_copy_path}")
    
    print(f"\n[SUCCESS] Generated {len(param_combinations)} parameter sweeps in {results_folder}")

def main():
    parser = argparse.ArgumentParser(
        description="Generate IP-Glasma jobs with varying parameters from a YAML config file."
    )
    parser.add_argument(
        "config",
        type=str,
        help="Path to YAML configuration file specifying parameter sweep"
    )
    
    args = parser.parse_args()
    generate_jobs_with_varying_params(args.config)

if __name__ == "__main__":
    main()
