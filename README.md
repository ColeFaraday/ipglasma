# README #

IP-Glasma code with improved matrix exponential - openmp development


### openmp IP-Glasma ###

 * this is version 0.1
 * work on openmp fftw (http://www.fftw.org/fftw3_doc/Usage-of-Multi_002dthreaded-FFTW.html)
 
 
## Input parameters

 - **writeOutputs**: this parameter controls output files
 	- 0: no output
 	- 1: output initial conditions e, u^\mu, and pi^{\mu\nu} for hydrodynamic simulations
 	- 2: output the initial condition for energy density according to the Jazma model
 	- 3: output 1 & 2
 	- 4: output initial T^{\mu\nu} for the effective kinetic theory (KoMPoST) simulations
 	- 5: output 1 & 4
 	- 6: output 2 & 4
 	- 7: output 1 & 2 & 4
 
 - **writeOutputsToHDF5**: this parameter decides whether to collect all the IPGlasma output files into a hdf5 data file
 	- 0: no
 	- 1: yes	

---

## Codebase Overview

**IP-Glasma** is a simulation code for modeling the initial state of heavy-ion collisions using the Color Glass Condensate effective theory. It generates event-by-event fluctuating initial conditions for hydrodynamics, including energy density and flow velocity profiles.

### Directory Structure

```
ipglasma/
├── CMakeLists.txt
├── compile_IPGlasma.sh
├── docker/
├── input
├── nucleusConfigurations/
├── qs2Adj_vs_Tp_vs_Y_200.in
├── src/
│   ├── *.cpp, *.h
├── tables/
├── utilities/
│   ├── *.py, *.sh
```

- **src/**: Main C++ source code.
- **input**: Default input parameter file.
- **nucleusConfigurations/**: Nuclear configuration files.
- **tables/**: Parameter tables for posterior sampling.
- **utilities/**: Helper scripts for job generation, data processing, etc.

### Main Components

1. **Parameters**
   - Handles all simulation parameters, read from the `input` file.
   - See `src/Parameters.h` and `src/Parameters.cpp`.
2. **Lattice & Cell**
   - `Lattice`: Represents the 2D grid of the transverse plane.
   - `Cell`: Represents a single grid point, storing local fields (energy density, color charge, etc.).
3. **Evolution**
   - Main evolution logic (time stepping, field updates, output).
   - See `src/Evolution.cpp`.
4. **Init**
   - Initialization routines for nuclei, color charges, and Wilson lines.
5. **Utilities**
   - Python and shell scripts for job management and data post-processing.

---

## Input File

The main configuration is provided in the `input` file.  
**Example parameters:**
```
mode  1
size  720
L  30.0
Nc  3
...
outputCondensedGrid  1
EndOfFile
```

**Key parameters:**
- `outputCondensedGrid`: Controls condensed output for Tmunu and epsilon-u files.

---

## Output Files

### 1. Energy Density and Flow Velocity
- **Files:** `epsilon-u*.dat`
- **Format:**  
  Each line:  
  `x  y  epsilon  utau  ux  uy  ueta`
- **Description:**  
  - `x`, `y`: Coordinates (fm)
  - `epsilon`: Local energy density (GeV/fm³)
  - `utau`, `ux`, `uy`, `ueta`: Flow velocity components

### 2. Tmunu Tensor
- **Files:** `Tmunu-t*.dat`
- **Format:**  
  Each line:  
  `ix  iy  T00  Txx  Tyy  Tetaeta  -T0x  -T0y  -T0eta  -Txy  -Tyeta  -Txeta`
- **Description:**  
  Components of the energy-momentum tensor at each grid point.

### 3. Other Outputs
- **Gluon spectrum:** `Nkxky*.dat`
- **Eccentricities:** `eccentricities*.dat`
- **Anisotropy:** `anisotropy*.dat`
- **Total energy:** `totalEnergy*.dat`
- **Initial Wilson lines:** `V-*.txt` or binary files

---

## Utilities

- **generate_jobs.py**: Automates job and event folder creation for batch runs.
- **combine_events_into_hdf5.py**: Combines event outputs into HDF5 format.
- **fetch_IPGlasma_event_from_hdf5_database.py**: Retrieves events from HDF5.
- **saveToBinaryFile.py**: Converts outputs to binary format.

---

## How to Run

1. **Edit the `input` file** to set your desired parameters.
2. **Compile the code** using the provided script or CMake.
3. **Run the executable** (e.g., `./ipglasma input`).
4. **Analyze outputs** in the generated files.

---

## Extending and Customizing

- **Add new parameters:**  
  - Edit `src/Parameters.h` and `src/Parameters.cpp`.
  - Add to the `input` file and `main.cpp` input reading logic.
- **Change output format:**  
  - Edit the relevant output section in `src/Evolution.cpp` or `src/MyEigen.cpp`.

---

## Further Reading

- For detailed physics background, see the original IP-Glasma papers.
- For code-specific questions, see comments in the source files or contact the maintainers.