# Analysis Results

This folder contains generated outputs from `code/analyze_fuel_cell.py`.

## Summary

| Fuel Cell | Start Time (h) | End Time (h) | Duration (h) | Initial Utot (V) | Final Utot (V) | Voltage Drop (V) | Degradation Rate (mV/h) | Mean Current (A) | Mean Air Inlet Temp (C) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FC1 | 0.0 | 1154.2134 | 1154.2134 | 3.317 | 3.211 | -0.106 | -0.0918 | 70.2568 | 42.2916 |
| FC2 | 0.0 | 1020.5363 | 1020.5363 | 3.325 | 3.084 | -0.241 | -0.2362 | 69.9381 | 44.9914 |

## Figures

- `figures/ageing_voltage_degradation.png`: stack voltage and cell imbalance during ageing
- `figures/ageing_channels/`: individual ageing plots for every numeric channel
- `figures/polarization/`: individual polarization plots
- `figures/eis/`: individual EIS Nyquist plots using raw data with sign-flipped imaginary impedance

## Ageing Parameter Notes

| Parameter | Meaning |
| --- | --- |
| U1 (V) | Voltage of cell 1. |
| U2 (V) | Voltage of cell 2. |
| U3 (V) | Voltage of cell 3. |
| U4 (V) | Voltage of cell 4. |
| U5 (V) | Voltage of cell 5. |
| Utot (V) | Total stack voltage. |
| J (A/cm2) | Current density normalized by active area. |
| I (A) | Stack current. |
| TinH2 (deg C) | Hydrogen inlet temperature. |
| ToutH2 (deg C) | Hydrogen outlet temperature. |
| TinAIR (deg C) | Air inlet temperature. |
| ToutAIR (deg C) | Air outlet temperature. |
| TinWAT (deg C) | Cooling-water inlet temperature. |
| ToutWAT (deg C) | Cooling-water outlet temperature. |
| PinAIR (mbara) | Air inlet absolute pressure. |
| PoutAIR (mbara) | Air outlet absolute pressure. |
| PoutH2 (mbara) | Hydrogen outlet absolute pressure. |
| PinH2 (mbara) | Hydrogen inlet absolute pressure. |
| DinH2 (l/mn) | Hydrogen inlet flow rate. |
| DoutH2 (l/mn) | Hydrogen outlet flow rate. |
| DinAIR (l/mn) | Air inlet flow rate. |
| DoutAIR (l/mn) | Air outlet flow rate. |
| DWAT (l/mn) | Cooling-water flow rate. |
| HrAIRFC (%) | Relative humidity of the air feed. |

## Individual Ageing Figures

- `figures/ageing_channels/u1_v.png`: U1 (V)
- `figures/ageing_channels/u2_v.png`: U2 (V)
- `figures/ageing_channels/u3_v.png`: U3 (V)
- `figures/ageing_channels/u4_v.png`: U4 (V)
- `figures/ageing_channels/u5_v.png`: U5 (V)
- `figures/ageing_channels/utot_v.png`: Utot (V)
- `figures/ageing_channels/j_a_cm2.png`: J (A/cm2)
- `figures/ageing_channels/i_a.png`: I (A)
- `figures/ageing_channels/tinh2_deg_c.png`: TinH2 (deg C)
- `figures/ageing_channels/touth2_deg_c.png`: ToutH2 (deg C)
- `figures/ageing_channels/tinair_deg_c.png`: TinAIR (deg C)
- `figures/ageing_channels/toutair_deg_c.png`: ToutAIR (deg C)
- `figures/ageing_channels/tinwat_deg_c.png`: TinWAT (deg C)
- `figures/ageing_channels/toutwat_deg_c.png`: ToutWAT (deg C)
- `figures/ageing_channels/pinair_mbara.png`: PinAIR (mbara)
- `figures/ageing_channels/poutair_mbara.png`: PoutAIR (mbara)
- `figures/ageing_channels/pouth2_mbara.png`: PoutH2 (mbara)
- `figures/ageing_channels/pinh2_mbara.png`: PinH2 (mbara)
- `figures/ageing_channels/dinh2_l_mn.png`: DinH2 (l/mn)
- `figures/ageing_channels/douth2_l_mn.png`: DoutH2 (l/mn)
- `figures/ageing_channels/dinair_l_mn.png`: DinAIR (l/mn)
- `figures/ageing_channels/doutair_l_mn.png`: DoutAIR (l/mn)
- `figures/ageing_channels/dwat_l_mn.png`: DWAT (l/mn)
- `figures/ageing_channels/hrairfc.png`: HrAIRFC (%)

## Individual Polarization Figures

- `figures/polarization/fc1_polarization_curves.png`: FC1 polarization curves
- `figures/polarization/fc2_polarization_curves.png`: FC2 polarization curves

## Individual EIS Figures

- `figures/eis/fc1_eis_20a.png`: FC1 EIS Nyquist at 20 A
- `figures/eis/fc1_eis_45a.png`: FC1 EIS Nyquist at 45 A
- `figures/eis/fc1_eis_70a.png`: FC1 EIS Nyquist at 70 A
- `figures/eis/fc2_eis_20a.png`: FC2 EIS Nyquist at 20 A
- `figures/eis/fc2_eis_45a.png`: FC2 EIS Nyquist at 45 A
- `figures/eis/fc2_eis_70a.png`: FC2 EIS Nyquist at 70 A
