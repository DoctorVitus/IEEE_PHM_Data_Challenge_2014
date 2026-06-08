from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIGURE_DIR = RESULTS_DIR / "figures"


plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "axes.titlesize": 15,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 9,
        "figure.titlesize": 17,
    }
)


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, sep=";", decimal=",")

    sheet = pd.ExcelFile(path).sheet_names[0]
    return pd.read_excel(path, sheet_name=sheet)


def clean_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(how="all")


def find_column(df: pd.DataFrame, prefix: str) -> str:
    matches = [col for col in df.columns if str(col).startswith(prefix)]
    if not matches:
        raise KeyError(f"Could not find a column starting with {prefix!r}")
    return matches[0]


def display_label(label: str) -> str:
    return (
        str(label)
        .replace("ｰC", "deg C")
        .replace("ｲ", "2")
        .replace("節캜", "deg C")
        .replace("節?", "2")
    )


def safe_filename(label: str) -> str:
    name = display_label(label)
    name = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return name.lower()


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
    temp_col = find_column(ageing, "TinAIR")
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
                "Mean Air Inlet Temp (C)": group[temp_col].mean(),
            }
        )
    return pd.DataFrame(rows)


def save_figure(fig: plt.Figure, name: str, rect: tuple[float, float, float, float] | None = None) -> None:
    fig.tight_layout(rect=rect)
    fig.savefig(FIGURE_DIR / name, dpi=220)
    plt.close(fig)


def plot_ageing_voltage(ageing: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=False)
    colors = {"FC1": "#2563eb", "FC2": "#dc2626"}

    for fc, group in ageing.groupby("Fuel Cell"):
        group = group.sort_values("Time (h)")
        rolling = group["Utot (V)"].rolling(600, min_periods=1).mean()
        axes[0].plot(group["Time (h)"], rolling, label=fc, color=colors.get(fc), linewidth=1.8)

        cell_cols = [f"U{i} (V)" for i in range(1, 6)]
        imbalance = group[cell_cols].std(axis=1).rolling(600, min_periods=1).mean()
        axes[1].plot(group["Time (h)"], imbalance * 1000, label=fc, color=colors.get(fc), linewidth=1.8)

    axes[0].set_title("Stack Voltage Degradation During Ageing")
    axes[0].set_ylabel("Utot (V), rolling mean")
    axes[0].grid(alpha=0.25)
    axes[0].legend()

    axes[1].set_title("Cell-to-Cell Voltage Imbalance")
    axes[1].set_xlabel("Time (h)")
    axes[1].set_ylabel("Std. of cell voltages (mV)")
    axes[1].grid(alpha=0.25)
    axes[1].legend()

    save_figure(fig, "ageing_voltage_degradation.png")


def plot_ageing_channel_figures(ageing: pd.DataFrame) -> list[tuple[str, str]]:
    numeric_cols = [
        col
        for col in ageing.select_dtypes(include=[np.number]).columns
        if col != "Time (h)"
    ]
    channel_dir = FIGURE_DIR / "ageing_channels"
    channel_dir.mkdir(parents=True, exist_ok=True)
    colors = {"FC1": "#2563eb", "FC2": "#dc2626"}
    outputs: list[tuple[str, str]] = []

    for col in numeric_cols:
        fig, ax = plt.subplots(figsize=(8.5, 5.2))
        for fc, group in ageing.groupby("Fuel Cell"):
            group = group.sort_values("Time (h)")
            values = group[col].rolling(600, min_periods=1).mean()
            ax.plot(group["Time (h)"], values, color=colors.get(fc), linewidth=1.4, label=fc)

        ax.set_title(display_label(col))
        ax.set_xlabel("Time (h)")
        ax.set_ylabel(display_label(col))
        ax.grid(alpha=0.25)
        ax.legend(frameon=False)

        filename = f"{safe_filename(col)}.png"
        fig.tight_layout()
        fig.savefig(channel_dir / filename, dpi=220)
        plt.close(fig)
        outputs.append((display_label(col), f"figures/ageing_channels/{filename}"))

    return outputs


def plot_polarization(polarization: pd.DataFrame) -> list[tuple[str, str]]:
    output_dir = FIGURE_DIR / "polarization"
    output_dir.mkdir(parents=True, exist_ok=True)
    j_col = find_column(polarization, "J (A/cm")
    outputs: list[tuple[str, str]] = []

    for fc, group in polarization.groupby("Fuel Cell"):
        fig, ax = plt.subplots(figsize=(8.5, 5.6))
        hours = sorted(group["Test Hour"].unique())
        cmap = plt.get_cmap("viridis")
        colors = cmap(np.linspace(0.05, 0.95, len(hours)))

        for hour, color in zip(hours, colors):
            curve = group[group["Test Hour"] == hour].copy()
            curve["J bin"] = curve[j_col].round(2)
            summary = curve.groupby("J bin", as_index=False)["Ustack (V)"].mean()
            ax.plot(
                summary["J bin"],
                summary["Ustack (V)"],
                color=color,
                linewidth=1.2,
                alpha=0.9,
                label=f"{hour} h",
            )

        ax.set_title(f"{fc} Polarization Curves")
        ax.set_xlabel("Current density (A/cm2)")
        ax.set_ylabel("Stack voltage (V)")
        ax.grid(alpha=0.25)
        ax.legend(title="Ageing time", frameon=False, ncol=2, fontsize=8)

        filename = f"{fc.lower()}_polarization_curves.png"
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=220)
        plt.close(fig)
        outputs.append((f"{fc} polarization curves", f"figures/polarization/{filename}"))

    return outputs


def raw_eis_with_flipped_sign(curve: pd.DataFrame) -> pd.DataFrame:
    raw = curve.copy()
    sign = 1 if raw["i/oHM"].median() >= 0 else -1
    raw["Z imag, sign-corrected (Ohm)"] = sign * raw["i/oHM"]
    return raw.sort_values("fREQUENCY/hZ", ascending=False)


def plot_eis(eis: pd.DataFrame) -> list[tuple[str, str]]:
    output_dir = FIGURE_DIR / "eis"
    output_dir.mkdir(parents=True, exist_ok=True)
    fcs = ["FC1", "FC2"]
    currents = sorted(eis["Current (A)"].unique())
    outputs: list[tuple[str, str]] = []

    for fc in fcs:
        for current in currents:
            fig, ax = plt.subplots(figsize=(8.5, 5.6))
            group = eis[(eis["Fuel Cell"] == fc) & (eis["Current (A)"] == current)]
            hours = sorted(group["Test Hour"].unique())
            cmap = plt.get_cmap("plasma")
            colors = cmap(np.linspace(0.05, 0.95, len(hours)))

            for hour, color in zip(hours, colors):
                curve = raw_eis_with_flipped_sign(group[group["Test Hour"] == hour])
                ax.plot(
                    curve["r/oHM"],
                    curve["Z imag, sign-corrected (Ohm)"],
                    color=color,
                    linewidth=1.1,
                    alpha=0.9,
                    label=f"{hour} h",
                )

            ax.set_title(f"{fc} EIS Nyquist at {current} A")
            ax.set_xlabel("Z real (Ohm)")
            ax.set_ylabel("Z imag, sign-corrected (Ohm)")
            ax.grid(alpha=0.25)
            ax.legend(title="Ageing time", frameon=False, fontsize=7, ncol=2)

            filename = f"{fc.lower()}_eis_{current}a.png"
            fig.tight_layout()
            fig.savefig(output_dir / filename, dpi=220)
            plt.close(fig)
            outputs.append((f"{fc} EIS Nyquist at {current} A", f"figures/eis/{filename}"))

    return outputs


PARAMETER_DESCRIPTIONS = {
    "U1 (V)": "Voltage of cell 1.",
    "U2 (V)": "Voltage of cell 2.",
    "U3 (V)": "Voltage of cell 3.",
    "U4 (V)": "Voltage of cell 4.",
    "U5 (V)": "Voltage of cell 5.",
    "Utot (V)": "Total stack voltage.",
    "J (A/cm2)": "Current density normalized by active area.",
    "I (A)": "Stack current.",
    "TinH2 (deg C)": "Hydrogen inlet temperature.",
    "ToutH2 (deg C)": "Hydrogen outlet temperature.",
    "TinAIR (deg C)": "Air inlet temperature.",
    "ToutAIR (deg C)": "Air outlet temperature.",
    "TinWAT (deg C)": "Cooling-water inlet temperature.",
    "ToutWAT (deg C)": "Cooling-water outlet temperature.",
    "PinAIR (mbara)": "Air inlet absolute pressure.",
    "PoutAIR (mbara)": "Air outlet absolute pressure.",
    "PoutH2 (mbara)": "Hydrogen outlet absolute pressure.",
    "PinH2 (mbara)": "Hydrogen inlet absolute pressure.",
    "DinH2 (l/mn)": "Hydrogen inlet flow rate.",
    "DoutH2 (l/mn)": "Hydrogen outlet flow rate.",
    "DinAIR (l/mn)": "Air inlet flow rate.",
    "DoutAIR (l/mn)": "Air outlet flow rate.",
    "DWAT (l/mn)": "Cooling-water flow rate.",
    "HrAIRFC (%)": "Relative humidity of the air feed.",
}


def write_results_readme(
    summary: pd.DataFrame,
    ageing_figures: list[tuple[str, str]],
    polarization_figures: list[tuple[str, str]],
    eis_figures: list[tuple[str, str]],
) -> None:
    rounded = summary.round(4)
    header = "| " + " | ".join(rounded.columns) + " |"
    divider = "| " + " | ".join(["---"] * len(rounded.columns)) + " |"
    rows = [
        "| " + " | ".join(str(value) for value in row) + " |"
        for row in rounded.to_numpy()
    ]
    lines = [
        "# Analysis Results",
        "",
        "This folder contains generated outputs from `code/analyze_fuel_cell.py`.",
        "",
        "## Summary",
        "",
        header,
        divider,
        *rows,
        "",
        "## Figures",
        "",
        "- `figures/ageing_voltage_degradation.png`: stack voltage and cell imbalance during ageing",
        "- `figures/ageing_channels/`: individual ageing plots for every numeric channel",
        "- `figures/polarization/`: individual polarization plots",
        "- `figures/eis/`: individual EIS Nyquist plots using raw data with sign-flipped imaginary impedance",
        "",
        "## Ageing Parameter Notes",
        "",
        "| Parameter | Meaning |",
        "| --- | --- |",
        *[
            f"| {parameter} | {PARAMETER_DESCRIPTIONS.get(parameter, 'Recorded operating variable.')} |"
            for parameter, _path in ageing_figures
        ],
        "",
        "## Individual Ageing Figures",
        "",
        *[f"- `{path}`: {parameter}" for parameter, path in ageing_figures],
        "",
        "## Individual Polarization Figures",
        "",
        *[f"- `{path}`: {label}" for label, path in polarization_figures],
        "",
        "## Individual EIS Figures",
        "",
        *[f"- `{path}`: {label}" for label, path in eis_figures],
        "",
    ]
    (RESULTS_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    ageing = load_ageing()
    polarization = load_polarization()
    eis = load_eis()

    summary = summarize_ageing(ageing)
    summary.to_csv(RESULTS_DIR / "ageing_summary.csv", index=False)

    plot_ageing_voltage(ageing)
    ageing_figures = plot_ageing_channel_figures(ageing)
    polarization_figures = plot_polarization(polarization)
    eis_figures = plot_eis(eis)
    write_results_readme(summary, ageing_figures, polarization_figures, eis_figures)

    print("Analysis complete")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
