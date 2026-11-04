# Load, PV and temperature profiles

## Files

- `loadshape/`: 80 hourly per-unit customer-demand CSVs.
- `pv/irradiance_kw_m2.csv`: plane-of-array irradiance in kW/m2.
- `temperature/cell_temperature_c.csv`: PV cell temperature in degrees Celsius.
- `profile_descriptions.json`: load categories and sources, PV system ratings, irradiance and cell-temperature definitions, units and CSV paths (relative to this folder).

OpenDSS reads the CSVs directly through relative paths. Keep `profiles/` and
`grid_model/` together. The detailed `metadata/` folder is local, ignored by
Git, and not required to run the model or interpret the published files.

## Time and load scaling

All runtime CSVs are headerless, single-column files with 8760 hourly values.
The calendar is 2018, hour ending, Mountain Standard Time (UTC-7), without DST
clock changes. Row 1 represents January 1, 00:00-01:00; row 8760 represents
December 31, 23:00-24:00. Published stock data in EST are shifted two hours
earlier with cyclic year wrapping. Synthetic schedules use the local calendar.

Load multipliers range from 0 to 1. Nominal demand equals the snapshot kW
times the multiplier, with default LoadMult=1. The same multiplier scales
base kvar, preserving power factor. Actual solved power remains subject to
the existing voltage-dependent OpenDSS load model. DSS kW is interpreted as
the customer's annual peak, not a coincident feeder demand target.

## Sources and customer construction

- ResStock: `2025/resstock_amy2018_release_1`, baseline upgrade 0.
- ComStock: `2025/comstock_amy2018_release_3`, baseline upgrade 0.
- Both use actual meteorological year 2018 (AMY2018).
- Source data: https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/

Single-family loads aggregate sampled detached-dwelling profiles before peak
scaling. The assumed dwelling count is max(1, round(base kW / 6)); each count
is recorded in the JSON. These are synthetic customer representations, not
identified physical customers. Commercial profiles use the assigned building
type, selecting the closest peak among five sampled candidates and scaling
to base kW. Geography and individual source building identifiers are omitted
from the published descriptions; these files alone do not reproduce the exact
source selection, but the complete hourly profiles are provided.

Special customers:
- `fdr2_14-3_load`: 15 sampled multifamily dwelling profiles, summed and scaled
  to 90 kW. The unit count is an assumption; common areas are not separately added.
- `fdr2_23_load`: Grocery demand plus four 7.2 kW EV ports. Synthetic Poisson
  arrivals average 16 sessions/day, one hour each, uniformly assigned between
  08:00 and 22:00. Occupancy is capped at four; excess arrivals are unserved.
  Only Grocery demand is rescaled to retain a combined 270 kW peak. EV demand
  is already included in the load CSV and must not be added again.
- `fdr3_23_load`: Warehouse background plus processing September-November,
  Monday-Saturday, 06:00-18:00. The mixture is 0.05 times normalized warehouse
  demand plus 0.95 times the processing on/off schedule, then peak-scaled to
  220 kW. The background fraction is not an annual energy share.

## PV and temperature

Irradiance and cell temperature come from PVWatts V8 hourly outputs using
NSRDB typical-year weather, mapped to the 2018 calendar. Assumptions are standard
modules, fixed rooftop mounting, 30-degree tilt, south-facing orientation,
and a 1:1 DC-to-AC nameplate ratio. All PV systems share these weather profiles.
Irradiance is POA W/m2 divided by 1000, used with base irradiance=1 kW/m2;
it may exceed 1 and is not peak-normalized. Cell temperatures are in Celsius.
OpenDSS computes AC power using its existing temperature and efficiency curves
at unity power factor. These are not PVWatts AC-power multipliers; PVWatts loss
and efficiency assumptions are not separately imposed on the native DSS model.
Typical-year solar weather is not weather-coincident with AMY2018 building loads.
PVWatts reference: https://developer.nlr.gov/docs/solar/pvwatts/v8/
