# Three-feeder planning test case

- `grid_model/opendss/snapshot/`: original snapshot model, including individual feeder masters.
- `grid_model/opendss/timeseries/`: annual load/PV model, usable as one substation or individual feeders.
- `profiles/`: hourly load/PV/temperature profiles, README and compact load descriptions.
- `grid_model/geopackage/three_feeder_nodes_edges.gpkg`: QGIS node/edge representation.

For yearly simulation compile the chosen time-series `master.dss`, then issue `Solve`.
Each master initializes the network and configures 8760 hourly steps at LoadMult=1.
See the model and profiles READMEs for timing, PV assumptions and entry points.
Baseline voltage and equipment-loading violations are intentional study opportunities;
these models are not a guarantee of violation-free operation.
