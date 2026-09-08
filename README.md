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

smallestEnergyGeV  1e-6

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
- `smallestEnergyGeV`: Minimum energy density (in GeV) for output in condensed grid mode. Default is 1e-6.

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

## Cross section mode (`crossSectionOnly`)

Measures only the inelastic cross section, without generating events.

An event is classified as inelastic entirely inside
`Init::setColorChargeDensity`; the Wilson lines, the forward lightcone solve
and the CYM evolution that normally follow have no bearing on that decision.
Setting `crossSectionOnly 1` stops each trial as soon as the decision is known
and repeats the sampling instead, which is ~10^3 times cheaper per accepted
event. It reproduces the full pipeline's accept/reject decision trial for
trial on a fixed seed.

```
crossSectionOnly       1     # measure sigma_inel only, generate no events
crossSectionTrials     10000 # independent trials per MPI rank
crossSectionVerbose    0     # 1 keeps the per-trial output (very noisy)
crossSectionDumpTrials 0     # 1 writes per-trial b, outcome and Q_s,min^2 S_T
```

`crossSectionDumpTrials` writes `trials<rank>.dat`. With a fixed seed the trial
sequence is reproducible across parameter values, so two runs that differ only
in (say) `QsTableTmin` can be compared trial by trial. That paired
(common-random-number) comparison is far more precise than differencing two
independent means -- in practice it turns a ~12% error on a ratio into ~0.3%.

`crossSection<rank>.dat` also reports `<Q_s,min^2 S_T>` and
`dsigmady_arb = sigma_inel * <Q_s,min^2 S_T>`. Since `Q_s,min^2 S_T` controls
dN/dy at leading order, that column is the production cross section up to a
constant which cancels in any ratio -- useful because sigma_inel and
`<dN/dy>` respond to the threshold in opposite directions and largely cancel
in their product.

Outputs, one pair per rank:

- `crossSection<rank>.dat` -- `sigma_inel` in mb with its statistical error,
  the trial and success counts, and the parameter set used.
- `PinelOfB<rank>.dat` -- `P_inel(b)` binned in impact parameter, with binomial
  errors. Multiple ranks are combined by summing the trial and success columns.

The estimator is the fixed-trial form, which is unbiased. With
`samplebFromLinearDistribution 1` (b sampled with pdf `2b/(bmax^2-bmin^2)`),

    sigma_inel = pi (bmax^2 - bmin^2) * nInelastic / nTrials,

and with uniform b sampling, `sigma_inel = 2 pi (bmax-bmin) <b*I>`. This is
preferable to `N_events / sum(nAttempts)` from the normal event loop, which is
a ratio of random variables and is biased at O(1/N).

### The interaction threshold (`QsTableTmin`)

The elastic/inelastic decision reduces to: *is there at least one lattice cell
where both nuclei have non-zero colour charge?* A cell's `g^2 mu^2` is zero
when `getNuclearQs2` returns zero, which happens when the nucleon thickness
`T_p` falls below a threshold `tau`. Historically `tau` was simply the lower
edge of the tabulated `Q_s(T_p, y)` -- for `qs2Adj_vs_Tp_vs_Y_200.in` that is
`1e-4 GeV^2`, i.e. `Q_s = 39.7 MeV`, which is a property of the table file
rather than a physics choice.

`QsTableTmin` makes it an input so its effect can be quantified:

```
QsTableTmin  -1        # <= 0: use the table's lower edge (historical default)
QsTableTmin  2.661e-3  # Q_s = 0.2 GeV, the same scale as the regulator m
```

The value is in GeV^2 and is clamped to the table's lower edge, since the table
cannot be extrapolated downwards. The threshold actually in force, and the
`Q_s` it corresponds to, are printed at startup and recorded in
`usedParameters*.dat`.

Note also that `sigma_inel` is capped at `4 * SigmaNN` and `P_inel(b)` vanishes
beyond `2*sqrt(0.1*SigmaNN/pi)` (2.92 fm at `SigmaNN 67`), because acceptance
additionally requires a cell within `sqrt(sigma_NN/pi)` of a collided nucleon
of *both* nuclei. Setting `bmax` just above that bound costs no accuracy and
avoids sampling impact parameters that can never be accepted.

See `runs/inputpp5020_crossSection` for a worked example.

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