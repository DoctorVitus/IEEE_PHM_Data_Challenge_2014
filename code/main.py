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


def scatter_with_guide(ax: plt.Axes, x: pd.Series, y: pd.Series, color, label: str, size: float = 12) -> None:
    x_values = pd.Series(x).reset_index(drop=True)
    y_values = pd.Series(y).reset_index(drop=True)

    marker_count = min(650, len(x_values))
    if marker_count > 1:
        marker_index = np.linspace(0, len(x_values) - 1, marker_count).astype(int)
    else:
        marker_index = np.arange(len(x_values))

    ax.scatter(
        x_values.iloc[marker_index],
        y_values.iloc[marker_index],
        color=color,
        s=size,
        alpha=0.72,
        edgecolors="none",
        label=label,
    )

    guide_count = min(70, len(x_values))
    if guide_count > 1:
        guide_index = np.linspace(0, len(x_values) - 1, guide_count).astype(int)
        ax.plot(
            x_values.iloc[guide_index],
            y_values.iloc[guide_index],
            color=color,
            linestyle=(0, (2, 3)),
            linewidth=1.0,
            alpha=0.6,
        )


def plot_ageing_voltage(ageing: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=False)
    colors = {"FC1": "#2563eb", "FC2": "#dc2626"}

    for fc, group in ageing.groupby("Fuel Cell"):
        group = group.sort_values("Time (h)")
        rolling = group["Utot (V)"].rolling(600, min_periods=1).mean()
        scatter_with_guide(axes[0], group["Time (h)"], rolling, colors.get(fc), fc, size=9.0)

        cell_cols = [f"U{i} (V)" for i in range(1, 6)]
        imbalance = group[cell_cols].std(axis=1).rolling(600, min_periods=1).mean()
        scatter_with_guide(axes[1], group["Time (h)"], imbalance * 1000, colors.get(fc), fc, size=9.0)

    axes[0].set_title("Stack Voltage Degradation")
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
            scatter_with_guide(ax, group["Time (h)"], values, colors.get(fc), fc, size=9.0)

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
            scatter_with_guide(
                ax,
                summary["J bin"],
                summary["Ustack (V)"],
                color,
                f"{hour} h",
                size=10,
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
    raw["Z_img(Ohm)"] = sign * raw["i/oHM"]
    return raw.sort_values("fREQUENCY/hZ", ascending=False)


def fit_circle(x: np.ndarray, y: np.ndarray) -> dict[str, float] | None:
    if len(x) < 4:
        return None

    matrix = np.column_stack([x, y, np.ones_like(x)])
    target = -(x**2 + y**2)
    a, b, c = np.linalg.lstsq(matrix, target, rcond=None)[0]
    center_x = -a / 2
    center_y = -b / 2
    radius_sq = center_x**2 + center_y**2 - c
    if radius_sq <= 0:
        return None

    radius = np.sqrt(radius_sq)
    radial_error = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2) - radius
    return {
        "center_x": center_x,
        "center_y": center_y,
        "radius": radius,
        "mse": float(np.mean(radial_error**2)),
    }


def circle_x_intercepts(circle: dict[str, float]) -> tuple[float, float] | None:
    center_x = circle["center_x"]
    center_y = circle["center_y"]
    radius = circle["radius"]
    delta_sq = radius**2 - center_y**2
    if delta_sq <= 0:
        return None

    delta = np.sqrt(delta_sq)
    return center_x - delta, center_x + delta


def fit_two_eis_arcs(arc: pd.DataFrame) -> dict[str, float] | None:
    arc = arc.sort_values("r/oHM")
    x = arc["r/oHM"].to_numpy(dtype=float)
    y = arc["Z_img(Ohm)"].to_numpy(dtype=float)
    n_points = len(arc)
    min_points = max(8, int(n_points * 0.18))
    best: dict[str, float] | None = None

    for split_idx in range(min_points, n_points - min_points + 1):
        x_first, y_first = x[:split_idx], y[:split_idx]
        x_second, y_second = x[split_idx - 1 :], y[split_idx - 1 :]
        first = fit_circle(x_first, y_first)
        second = fit_circle(x_second, y_second)
        if first is None or second is None:
            continue

        first_intercepts = circle_x_intercepts(first)
        second_intercepts = circle_x_intercepts(second)
        if first_intercepts is None or second_intercepts is None:
            continue

        first_left, first_right = first_intercepts
        second_left, second_right = second_intercepts
        if not (first_left < first_right <= second_right):
            continue

        total_mse = first["mse"] * len(x_first) + second["mse"] * len(x_second)
        if best is None or total_mse < best["Fit MSE"]:
            best = {
                "R_ohmic (Ohm)": first_left,
                "R_ct_anode (Ohm)": max(first_right - first_left, 0),
                "R_ct_cathode (Ohm)": max(second_right - second_left, 0),
                "R_ct_total (Ohm)": max(first_right - first_left, 0) + max(second_right - second_left, 0),
                "Arc Split Real (Ohm)": x[split_idx - 1],
                "Anode Circle Center Real (Ohm)": first["center_x"],
                "Anode Circle Center Imag (Ohm)": first["center_y"],
                "Anode Circle Radius (Ohm)": first["radius"],
                "Cathode Circle Center Real (Ohm)": second["center_x"],
                "Cathode Circle Center Imag (Ohm)": second["center_y"],
                "Cathode Circle Radius (Ohm)": second["radius"],
                "Fit MSE": total_mse,
            }

    return best


def fit_eis_resistances(eis: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (fc, current, hour), group in eis.groupby(["Fuel Cell", "Current (A)", "Test Hour"]):
        curve = raw_eis_with_flipped_sign(group)
        arc = curve[curve["Z_img(Ohm)"] >= 0].dropna(subset=["r/oHM", "Z_img(Ohm)"])
        if len(arc) < 5:
            continue

        fit = fit_two_eis_arcs(arc)
        if fit is None:
            continue

        rows.append(
            {
                "Fuel Cell": fc,
                "Current (A)": current,
                "Test Hour": hour,
                **fit,
            }
        )

    return pd.DataFrame(rows).sort_values(["Fuel Cell", "Current (A)", "Test Hour"]).reset_index(drop=True)


def plot_eis_resistance_trends(resistances: pd.DataFrame) -> list[tuple[str, str]]:
    output_dir = FIGURE_DIR / "eis_resistance_trends"
    output_dir.mkdir(parents=True, exist_ok=True)
    resistance_cols = [
        ("R_ohmic (Ohm)", "Ohmic Resistance"),
        ("R_ct_anode (Ohm)", "Anode Charge Transfer Resistance"),
        ("R_ct_cathode (Ohm)", "Cathode Charge Transfer Resistance"),
    ]
    outputs: list[tuple[str, str]] = []

    for fc, fc_group in resistances.groupby("Fuel Cell"):
        for col, title in resistance_cols:
            fig, ax = plt.subplots(figsize=(8.5, 5.4))
            currents = sorted(fc_group["Current (A)"].unique())
            cmap = plt.get_cmap("magma")
            colors = cmap(np.linspace(0.08, 0.92, len(currents)))

            for current, color in zip(currents, colors):
                group = fc_group[fc_group["Current (A)"] == current].sort_values("Test Hour")
                scatter_with_guide(ax, group["Test Hour"], group[col], color, f"{current} A", size=24)

            ax.set_title(f"{fc} {title}")
            ax.set_xlabel("Ageing time (h)")
            ax.set_ylabel(col)
            ax.grid(alpha=0.25)
            ax.legend(title="EIS current", frameon=False)

            filename = f"{fc.lower()}_{safe_filename(title)}.png"
            fig.tight_layout()
            fig.savefig(output_dir / filename, dpi=220)
            plt.close(fig)
            outputs.append((f"{fc} {title}", f"figures/eis_resistance_trends/{filename}"))

    return outputs


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
                scatter_with_guide(
                    ax,
                    curve["r/oHM"],
                    curve["Z_img(Ohm)"],
                    color,
                    f"{hour} h",
                    size=10,
                )

            ax.set_title(f"{fc} EIS Nyquist at {current} A")
            ax.set_xlabel("Z_real(Ohm)")
            ax.set_ylabel("Z_img(Ohm)")
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


def markdown_table(df: pd.DataFrame) -> list[str]:
    rounded = df.round(4)
    header = "| " + " | ".join(rounded.columns) + " |"
    divider = "| " + " | ".join(["---"] * len(rounded.columns)) + " |"
    rows = [
        "| " + " | ".join(str(value) for value in row) + " |"
        for row in rounded.to_numpy()
    ]
    return [header, divider, *rows]


def write_main_readme(
    summary: pd.DataFrame,
    resistance_summary: pd.DataFrame,
    ageing_figures: list[tuple[str, str]],
    polarization_figures: list[tuple[str, str]],
    eis_figures: list[tuple[str, str]],
    resistance_figures: list[tuple[str, str]],
) -> None:
    lines = [
        "# IEEE PHM Data Challenge 2014",
        "",
        "This repository contains the IEEE PHM Data Challenge 2014 fuel-cell durability dataset and a reproducible analysis workflow for quick exploration and visualization.",
        "",
        "## Repository Structure",
        "",
        "```text",
        "data/     Original dataset files. Do not modify these files.",
        "code/     Reproducible Python analysis scripts.",
        "results/  Generated summaries and figures.",
        "```",
        "",
        "## Dataset",
        "",
        "- **FC1**: fuel-cell durability test operated in a stationary regime",
        "- **FC2**: fuel-cell durability test operated under dynamic current",
        "- **Source**: https://search-data.ubfc.fr/FR-18008901306731-2021-07-19_IEEE-PHM-Data-Challenge-2014.html#pub_col_ver",
        "",
        "The dataset includes ageing, polarization, and electrochemical impedance spectroscopy (EIS) measurements.",
        "",
        "## Quick Analysis",
        "",
        "Run the analysis script from the repository root:",
        "",
        "```bash",
        "python code/main.py",
        "```",
        "",
        "The script reads the Excel/CSV files under `data/` and writes figures plus summary tables to `results/`.",
        "",
        "## Key Results",
        "",
        "| Fuel Cell | Duration (h) | Initial Utot (V) | Final Utot (V) | Voltage Drop (V) | Degradation Rate (mV/h) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        *[
            f"| {row['Fuel Cell']} | {row['Duration (h)']:.1f} | {row['Initial Utot (V)']:.3f} | {row['Final Utot (V)']:.3f} | {row['Voltage Drop (V)']:.3f} | {row['Degradation Rate (mV/h)']:.3f} |"
            for _, row in summary.iterrows()
        ],
        "",
        "FC2 shows a larger voltage loss and a faster degradation rate than FC1, consistent with the stronger stress expected from dynamic-current operation.",
        "",
        "## Summary Table",
        "",
        *markdown_table(summary),
        "",
        "## Figures",
        "",
        "- `figures/ageing_voltage_degradation.png`: stack voltage and cell imbalance during ageing",
        "- `figures/ageing_channels/`: individual ageing plots for every numeric channel",
        "- `figures/polarization/`: individual polarization plots using scatter points with dashed guide lines",
        "- `figures/eis/`: individual EIS Nyquist plots using raw impedance data",
        "",
        "### Ageing Voltage Degradation",
        "",
        "![Ageing voltage degradation](results/figures/ageing_voltage_degradation.png)",
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
        *[
            f"### {label}\n\n![{label}](results/{path})"
            for label, path in polarization_figures
        ],
        "",
        "## Individual EIS Figures",
        "",
        *[
            f"### {label}\n\n![{label}](results/{path})"
            for label, path in eis_figures
        ],
        "",
        "## EIS Resistance Analysis",
        "",
        "EIS resistance values were estimated by fitting two least-squares circles to the Nyquist-oriented impedance arc. The split point is selected by scanning candidate boundaries and choosing the two-circle fit with the lowest residual error. `R_ohmic` is taken from the high-frequency real-axis intercept of the first fitted circle. `R_ct_anode` and `R_ct_cathode` are estimated from the real-axis diameters of the first and second fitted circles, respectively.",
        "",
        "The full fitted resistance table is saved at `results/eis_resistance_summary.csv`.",
        "",
        "### Mean Fitted Resistance by Fuel Cell and EIS Current",
        "",
        *markdown_table(
            resistance_summary.groupby(["Fuel Cell", "Current (A)"], as_index=False)[
                ["R_ohmic (Ohm)", "R_ct_anode (Ohm)", "R_ct_cathode (Ohm)", "R_ct_total (Ohm)"]
            ].mean()
        ),
        "",
        "### Resistance Trend Figures",
        "",
        *[
            f"#### {label}\n\n![{label}](results/{path})"
            for label, path in resistance_figures
        ],
        "",
    ]
    (ROOT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    ageing = load_ageing()
    polarization = load_polarization()
    eis = load_eis()

    summary = summarize_ageing(ageing)
    resistance_summary = fit_eis_resistances(eis)
    summary.to_csv(RESULTS_DIR / "ageing_summary.csv", index=False)
    resistance_summary.to_csv(RESULTS_DIR / "eis_resistance_summary.csv", index=False)

    plot_ageing_voltage(ageing)
    ageing_figures = plot_ageing_channel_figures(ageing)
    polarization_figures = plot_polarization(polarization)
    eis_figures = plot_eis(eis)
    resistance_figures = plot_eis_resistance_trends(resistance_summary)
    write_main_readme(summary, resistance_summary, ageing_figures, polarization_figures, eis_figures, resistance_figures)

    print("Analysis complete")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
