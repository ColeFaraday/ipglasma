# `QsTableTmin` (tau) threshold scan -- cross section mode

Standard 5.02 TeV pp and pPb parameters (identical to
`../inputpp5020_runWithkt` and `../inputpPb5020_runWithkt`) differing only in
`QsTableTmin`, the T_p threshold below which `getNuclearQs2` returns zero and a
cell carries no colour charge. That threshold *is* the elastic/inelastic
decision, so these run in `crossSectionOnly` mode: sigma_inel, P_inel(b) and
<Q_s,min^2 S_T>, no events.

| file suffix        | `QsTableTmin` [GeV^2] | Q_s(y=0) |
|--------------------|-----------------------|----------|
| `_Qs040_tableEdge` | `-1` (-> 1e-4)        | 39.7 MeV |
| `_Qs100`           | 6.348e-4              | 100 MeV  |
| `_Qs150`           | 1.427e-3              | 150 MeV  |
| `_Qs200`           | 2.532e-3              | 200 MeV  |
| `_Qs300`           | 5.672e-3              | 300 MeV  |
| `_Qs500`           | 1.557e-2              | 500 MeV  |

`_Qs040_tableEdge` is the historical default: `QsTableTmin <= 0` clamps to the
lower edge of `qs2Adj_vs_Tp_vs_Y_200.in` (T_p = 1e-4 GeV^2), a property of the
table file rather than a physics choice. 200 MeV is the same scale as the
regulator `m`.

The tau values come from inverting the y = 0 slice of that table with the
interpolation the code itself uses (linear in Q_s^2 vs T_p,
`Init::getNuclearQs2`), so each lands on the quoted Q_s to better than 1 MeV.
The threshold in force and its Q_s are echoed at startup and written to
`usedParameters*.dat`. (The main README quotes 2.661e-3 for "Q_s = 0.2 GeV";
that is the nearest tabulated T_p node above, which is really Q_s = 205 MeV.)

## Differences from the standard inputs

- `crossSectionOnly 1`, `crossSectionTrials 10000` per rank,
  `crossSectionDumpTrials 1` -- `trials<rank>.dat` holds the per-trial b,
  outcome and Q_s,min^2 S_T.
- `useTimeForSeed 0` with the standard `seed 3`. Fixed seeds make the trial
  sequence identical across the six tau values, so they can be compared
  trial by trial (common random numbers) instead of by differencing
  independent means -- roughly a ~12% -> ~0.3% error on a ratio.
- pp `bmax 3.0` instead of 10.0. P_inel(b) vanishes beyond
  2*sqrt(0.1*SigmaNN/pi) = 2.92 fm at `SigmaNN 67.`, so this costs no accuracy
  and removes impact parameters that can never be accepted. pPb keeps
  `bmax 15.0`.

Everything else -- lattice, `m`, `BG`/`BGq`, `QsmuRatio`, `SigmaNN`, the
sub-nucleon settings -- is the standard set, unchanged.

Compare `sigma_inel` from `crossSection<rank>.dat` (and `dsigmady_arb`, which
folds in <Q_s,min^2 S_T> and largely cancels the opposing responses of
sigma_inel and dN/dy) across the six files.
