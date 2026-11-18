# A Compact Three-Feeder Test System for Electric Distribution Planning
This repositiory describes a new test system for U.S.-
style electric distribution planning. It is designed to support
a wide range of planning analyses including upgrades and
reconfigurations for load growth and DER while remaining small
enough for fast computation and to make it easy to visually
anticipate and check planning results. It uses three similar
feeders each with about 50 single or multi-phase buses but
with intentional diversity in load and wiring configurations and
overhead versus underground lines to enable cross-comparisons
of different results. It also provides substation switching internals
with two transformers and realistic hourly time series for loads
and rooftop solar. The system is available open-source in both
OpenDSS and GDM formats.

- `grid_model/opendss/snapshot/`: original snapshot model, including individual feeder masters.
- `grid_model/opendss/timeseries/`: annual load/PV model, usable as one substation or individual feeders.
- `profiles/`: hourly load/PV/temperature profiles, README and compact load descriptions.
- `grid_model/geopackage/three_feeder_nodes_edges.gpkg`: QGIS node/edge representation.

For yearly simulation compile the chosen time-series `master.dss`, then issue `Solve`.
Each master initializes the network and configures 8760 hourly steps at LoadMult=1.
See the model and profiles READMEs for timing, PV assumptions and entry points.
Baseline voltage and equipment-loading violations are intentional study opportunities;
these models are not a guarantee of violation-free operation.

What about cost data? We have included detailed descriptions of realistic equipment and conductors so that you can use system specific, updated costs for any comparisons. These technical parameters can also be converted to costs with the [Distribution Cost Database](https://www.nlr.gov/solar/market-research-analysis/distribution-grid-integration-unit-cost-database)

If you make use of this data in your work, please cite:

```A. Poudyal, B. Palmintier, and W. Wang, “A Compact Three-Feeder Test System for Electric Distribution Planning,” Submitted to the IEEE PES General Meeting 2027, San Francisco, CA: IEEE. (In Review)```

