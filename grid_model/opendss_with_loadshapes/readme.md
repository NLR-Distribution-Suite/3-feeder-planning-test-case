# Three-feeder OpenDSS model with annual profiles

This folder is self-contained. All network files and snapshot load ratings
come from ../opendss. Copy/upload the entire folder, including profiles/.

## Run

Compile master.dss in OpenDSS. It initializes the source snapshot, attaches
profiles, and sets yearly mode, 1-hour steps, 8760 steps, starting at hour 0.
Then issue `Solve` to run the year. Alternatively compile run_yearly.dss.
For a single first-hour check, after compiling master.dss issue
`Set number=1` then `Solve`. Recompile before starting a complete year.
master_snapshot.dss is the original snapshot entry point without profiles.

## Loads

80 headerless single-column CSVs contain 8760 multipliers between 0 and 1.
Nominal P(t) = snapshot kW * multiplier(t), with LoadMult=1. No feeder-wide
upscaling is applied. useactual=no prevents shapes from replacing base ratings.
With no separate Q multiplier, the same multiplier scales snapshot kvar,
preserving the specified power factor. Actual terminal power still follows
the original OpenDSS voltage-dependent load model and voltage limits.

## Timing

All packaged profiles use hour-ending Mountain Standard Time (UTC-7), without
DST clock changes. Stock profiles published in EST are cyclically shifted
two hours earlier. Synthetic September-November processing and 08:00-22:00 EV
schedules remain local; these two composites are rebuilt after alignment.
The original data/golden_jefferson_county CSVs are not modified. Their former
blanket local-time label did not account for stock data published in EST.
Consequently, use this package's descriptions for its corrected annual metrics.
Source: https://natlabrockies.github.io/ComStock.github.io/docs/faq.html

## PV

11 native PVSystem elements retain original Pmpp, kVA, temperature-power and
efficiency curves. They share Golden PVWatts plane-of-array irradiance and
cell temperature. POA W/m2 is divided by 1000; base irradiance is 1 kW/m2.
Irradiance is not peak-normalized or clipped to 1: it may exceed 1 kW/m2.
PV operates at unity PF. The load-shape 0-to-1 restriction applies to loads.
This is native OpenDSS PV conversion, not replay of PVWatts AC generation.
The source model's curves/loss treatment differ from PVWatts; its 14% losses
and 96% inverter efficiency are not separately imposed in OpenDSS. Therefore
earlier PVWatts AC energy totals are not expected to match this model.
TMY solar weather is calendar-mapped to 2018 and is not weather-coincident
with AMY2018 building loads.

## Provenance and validation

loadshape_descriptions.csv lists base ratings, shape bounds and nominal energy.
profile_metadata.json contains configuration, timing, PV provenance and
source-model hashes. Source customer descriptions are included under profiles/.
Generation checks cover inventory, lengths, finite values and load bounds.
Annual convergence, voltage and loading validation is left to the user.
Rebuild script: 3test_feeders/scripts/package_opendss_shapes.py (refuses to
overwrite a populated destination).
