from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "analysis_outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, sep=";", decimal=",")

    sheet = pd.ExcelFile(path).sheet_names[0]
    return pd.read_excel(path, sheet_name=sheet)


def clean_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(how="all")


def fuel_cell_from_name(path: Path) -> str:
    match = re.match(r"(FC\d)", path.name)
    if not match:
        raise ValueError(f"Could not parse fuel-cell id from {path.name}")
    return match.group(1)


def test_hour_from_name(path: Path) -> int:
    match = re.search(r"_T(\d+)", path.stem)
    if not match:
        raise ValueError(f"Could not parse test hour from {path.name}")
    return int(match.group(1))


def load_ageing() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in sorted(DATA_DIR.rglob("*Ageing_part*.*")):
        if path.suffix.lower() not in {".xlsx", ".csv"}:
            continue
        df = clean_numeric(read_table(path))
        df["Fuel Cell"] = fuel_cell_from_name(path)
        df["Source File"] = path.name
        frames.append(df)

    ageing = pd.concat(frames, ignore_index=True)
    return ageing.sort_values(["Fuel Cell", "Time (h)"]).reset_index(drop=True)


def load_polarization() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in sorted(DATA_DIR.rglob("*_Pola_T*.*")):
        df = clean_numeric(read_table(path))
        df["Fuel Cell"] = fuel_cell_from_name(path)
        df["Test Hour"] = test_hour_from_name(path)
        frames.append(df)

    return pd.concat(frames, ignore_index=True)


def load_eis() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    pattern = re.compile(r"(?P<fc>FC\d)_EIS(?P<current>\d+)A_(?P<stage>[^_]+)_T(?P<hour>\d+)")

    for path in sorted(DATA_DIR.rglob("*_EIS*A_*.*")):
        if path.suffix.lower() not in {".xlsx", ".csv"}:
            continue
        match = pattern.match(path.stem)
        if not match:
            continue

        df = clean_numeric(read_table(path))
        df["Fuel Cell"] = match.group("fc")
        df["Current (A)"] = int(match.group("current"))
        df["Stage"] = match.group("stage")
        df["Test Hour"] = int(match.group("hour"))
        frames.append(df)

    return pd.concat(frames, ignore_index=True)


def summarize_ageing(ageing: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for fc, group in ageing.groupby("Fuel Cell"):
        group = group.sort_values("Time (h)")
        start = group.iloc[0]
        end = group.iloc[-1]
        duration = end["Time (h)"] - start["Time (h)"]
        voltage_drop = end["Utot (V)"] - start["Utot (V)"]
        rows.append(
            {
                "Fuel Cell": fc,
                "Start Time (h)": start["Time (h)"],
                "End Time (h)": end["Time (h)"],
                "Duration (h)": duration,
                "Initial Utot (V)": start["Utot (V)"],
                "Final Utot (V)": end["Utot (V)"],
                "Voltage Drop (V)": voltage_drop,
                "Degradation Rate (mV/h)": voltage_drop * 1000 / duration,
                "Mean Current (A)": group["I (A)"].mean(),
                "Mean Air Inlet Temp (C)": group["TinAIR (ｰC)"].mean(),
            }
        )
    return pd.DataFrame(rows)


def plot_ageing_voltage(ageing: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=False)
    colors = {"FC1": "#2563eb", "FC2": "#dc2626"}

    for fc, group in ageing.groupby("Fuel Cell"):
        group = group.sort_values("Time (h)")
        rolling = group["Utot (V)"].rolling(600, min_periods=1).mean()
        axes[0].plot(group["Time (h)"], rolling, label=fc, color=colors.get(fc))

        cell_cols = [f"U{i} (V)" for i in range(1, 6)]
        imbalance = group[cell_cols].std(axis=1).rolling(600, min_periods=1).mean()
        axes[1].plot(group["Time (h)"], imbalance * 1000, label=fc, color=colors.get(fc))

    axes[0].set_title("Stack Voltage Degradation During Ageing")
    axes[0].set_ylabel("Utot (V), rolling mean")
    axes[0].grid(alpha=0.25)
    axes[0].legend()

    axes[1].set_title("Cell-to-Cell Voltage Imbalance")
    axes[1].set_xlabel("Time (h)")
    axes[1].set_ylabel("Std. of cell voltages (mV)")
    axes[1].grid(alpha=0.25)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "ageing_voltage_degradation.png", dpi=180)
    plt.close(fig)


def plot_polarization(polarization: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, (fc, group) in zip(axes, polarization.groupby("Fuel Cell")):
        hours = sorted(group["Test Hour"].unique())
        selected = [hours[0], hours[len(hours) // 2], hours[-1]]

        for hour in selected:
            curve = group[group["Test Hour"] == hour].copy()
            curve["J bin"] = curve["J (A/cmｲ)"].round(2)
            summary = curve.groupby("J bin", as_index=False)["Ustack (V)"].mean()
            ax.plot(summary["J bin"], summary["Ustack (V)"], marker="o", markersize=3, label=f"T{hour:03d}")

        ax.set_title(f"{fc} Polarization Curves")
        ax.set_xlabel("Current density (A/cm2)")
        ax.grid(alpha=0.25)
        ax.legend(title="Ageing time")

    axes[0].set_ylabel("Stack voltage (V)")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "polarization_evolution.png", dpi=180)
    plt.close(fig)


def plot_eis(eis: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)

    for ax, fc in zip(axes, ["FC1", "FC2"]):
        group = eis[(eis["Fuel Cell"] == fc) & (eis["Current (A)"] == 70)]
        hours = sorted(group["Test Hour"].unique())
        selected = [hours[0], hours[len(hours) // 2], hours[-1]]

        for hour in selected:
            curve = group[group["Test Hour"] == hour].sort_values("fREQUENCY/hZ")
            ax.plot(curve["r/oHM"], -curve["i/oHM"], marker="o", markersize=3, label=f"T{hour:03d}")

        ax.set_title(f"{fc} EIS Nyquist at 70 A")
        ax.set_xlabel("Z real (Ohm)")
        ax.grid(alpha=0.25)
        ax.legend(title="Ageing time")

    axes[0].set_ylabel("-Z imag (Ohm)")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "eis_nyquist_70A.png", dpi=180)
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    ageing = load_ageing()
    polarization = load_polarization()
    eis = load_eis()

    summary = summarize_ageing(ageing)
    summary.to_csv(OUTPUT_DIR / "ageing_summary.csv", index=False)

    plot_ageing_voltage(ageing)
    plot_polarization(polarization)
    plot_eis(eis)

    print("Analysis complete")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
