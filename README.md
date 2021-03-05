# Adaptive Comfort Map

Adaptive thermal comfort map recipe for Pollination.

Compute spatially-resolved operative temperature and adaptive thermal comfort from
a Honeybee model and EPW. Raw results are written into a `results/` folder and
include CSV matrices of hourly operative temperatures and thermal conditions. Processed
metrics of Thermal Comfort Percent (TCP) can be found in the `metrics/` folder.

## Methods

This recipe uses EnergyPlus to obtain longwave radiant temperatures and indoor air
temperatures. The outdoor air temperature and air speed are taken directly from the EPW.
A Radiance-based enhanced 2-phase method is used for shortwave MRT calculations,
which includes an accurate direct sun calculation using precise solar positions. The
energy properties of the model geometry are what determine the outcome of the
simulation and the model's SensorGrids are what determine where the comfort
mapping occurs.

To determine Thermal Comfort Percent (TCP), the occupancy schedules of the energy
model are used. Any hour of the occupancy schedule that is 0.1 or greater will be
considered occupied. All hours of the outdoor are considered occupied.
