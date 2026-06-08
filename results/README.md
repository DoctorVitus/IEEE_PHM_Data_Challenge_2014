# Analysis Results

This folder contains generated outputs from `code/analyze_fuel_cell.py`.

## Summary

| Fuel Cell | Start Time (h) | End Time (h) | Duration (h) | Initial Utot (V) | Final Utot (V) | Voltage Drop (V) | Degradation Rate (mV/h) | Mean Current (A) | Mean Air Inlet Temp (C) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FC1 | 0.0 | 1154.2134 | 1154.2134 | 3.317 | 3.211 | -0.106 | -0.0918 | 70.2568 | 42.2916 |
| FC2 | 0.0 | 1020.5363 | 1020.5363 | 3.325 | 3.084 | -0.241 | -0.2362 | 69.9381 | 44.9914 |

## Figures

- `figures/ageing_voltage_degradation.png`: stack voltage and cell imbalance during ageing
- `figures/ageing_all_channels.png`: overview of every numeric ageing channel
- `figures/polarization_all_times.png`: polarization curves at every available ageing time
- `figures/eis_nyquist_all_currents.png`: EIS Nyquist curves for every available current and ageing time
