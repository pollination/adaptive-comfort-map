# Adaptive Comfort Map

Adaptive thermal comfort map recipe for Pollination.

Compute spatially-resolved operative temperature and adaptive thermal comfort from
a Honeybee model and EPW. Raw results are written into a `results/` folder and
include CSV matrices of hourly operative temperatures and thermal conditions. Processed
metrics of Thermal Comfort Percent (TCP) can be found in the `metrics/` folder.

## Methods

This recipe uses EnergyPlus to obtain longwave radiant temperatures and indoor air
temperatures. The outdoor air temperature and air speed are taken directly from
the EPW. All outdoor points are assumed to be at one half of the EPW meteorological
wind speed (effectively representing wind speed at ground/human height).

Longwave radiant temperatures are achieved by computing spherical view factors
from each sensor to the surfaces of the model using Radiance. These view factors
are then multiplied by the surface temperatures output by EnergyPlus to yield
longwave MRT at each sensor. All indoor shades (eg. those representing furniture)
are assumed to be at the room-average MRT. For outdoor sensors, the EnergyPlus
outdoor surface temperatures are used and each sensor's sky view is multiplied by
the EPW sky temperature to account for longwave radiant exchange with the sky.
All outdoor context shades and the ground are assumed to be at the EPW air
temperature unless they have been modeled as Honeybee rooms.

A Radiance-based enhanced 2-phase method is used for all shortwave MRT calculations,
which precisely represents direct sun by tracing a ray from each sensor to the
solar position. The energy properties of the model geometry are what determine
the reflectance and transmittance of the Radiance materials in this shortwave
calculation.

To determine Thermal Comfort Percent (TCP), the occupancy schedules of the energy
model are used. Any hour of the occupancy schedule that is 0.1 or greater will be
considered occupied. For outdoor sensors, all hours are considered occupied.
