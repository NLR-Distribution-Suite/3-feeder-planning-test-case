# OpenDSS time-series model

This model reads shared CSVs from the repository-root profiles/ folder.
Keep grid_model/ and profiles/ together when copying the model.

## Entry points

- master.dss: all three feeders and the substation (80 loads, 11 PV).
- feeder_1/master.dss: feeder 1 alone (25 loads, no PV).
- feeder_2/master.dss: feeder 2 alone (27 loads, 4 PV).
- feeder_3/master.dss: feeder 3 alone (28 loads, 7 PV).

Compile the desired master, then issue Solve to run 8760 hourly steps.
Alternatively compile run_yearly.dss in that same directory. Compilation
performs a snapshot initialization, then sets yearly mode at hour zero.
Recompile before rerunning a year. For a one-hour check, set number=1 before Solve.
Standalone sources match their snapshot counterparts and are not equivalent
to the full substation model. The combined master redirects feeder equipment,
not the standalone masters (which create separate circuits).

Load nominal kW and kvar equal snapshot values times their 0-to-1 hourly
multiplier; LoadMult defaults to 1. Voltage-dependent load behavior remains.
Load yearly/status and PV yearly/Tyearly assignments are embedded in New objects.
All shapes are defined before the objects that reference them.

Profiles use 8760 hour-ending samples on the 2018 MST calendar (UTC-7).
Stock EST data have been shifted to MST; synthetic schedules remain local.
Native PVSystem conversion uses POA irradiance (W/m2 divided by 1000)
and cell temperature with the existing DSS efficiency/temperature curves.
Irradiance may exceed 1 and is not peak-normalized. PVWatts AC output is not
replayed; previous PVWatts AC totals need not match native OpenDSS generation.
PV typical-year weather is not weather-coincident with AMY2018 building loads.

Profiles: ../../../profiles/{loadshape,pv,temperature}/.
Published descriptions: ../../../profiles/profile_descriptions.json and ../../../profiles/readme.md.
Snapshot-only models: ../snapshot/.
Baseline voltage/thermal violations remain available as study use cases.
