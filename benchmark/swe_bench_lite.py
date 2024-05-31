import sys
from pathlib import Path

import matplotlib.pyplot as plt
from imgcat import imgcat
from matplotlib import rc


def plot_swe_bench_lite(data_file):
    with open(data_file, "r") as file:
        lines = file.readlines()

    models = []
    pass_rates = []

    for line in lines:
        if line.strip():
            pass_rate, model = line.split("%")
            model = model.strip()
            model = model.replace("|", "\n")
            models.insert(0, model.strip())
            pass_rates.insert(0, float(pass_rate.strip()))

    plt.rcParams["hatch.linewidth"] = 0.5
    plt.rcParams["hatch.color"] = "#444444"

    font_color = "#555"
    font_params = {
        "family": "sans-serif",
        "sans-serif": ["Helvetica"],
        "size": 10,
        "weight": "bold",
    }
    rc("font", **font_params)
    plt.rcParams["text.color"] = font_color

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.grid(axis="y", zorder=0, lw=0.2)
    for spine in ax.spines.values():
        spine.set_edgecolor("#DDDDDD")
        spine.set_linewidth(0.5)

    colors = ["#17965A" if "Aider" in model else "#b3d1e6" for model in models]
    bars = []
    for model, pass_rate, color in zip(models, pass_rates, colors):
        alpha = 0.9 if "Aider" in model else 0.3
        hatch = ""
        # if "lite" not in data_file:
        #    hatch = "///" if "(570)" in model else ""
        bar = ax.bar(model, pass_rate, color=color, alpha=alpha, zorder=3, hatch=hatch)
        bars.append(bar[0])

    for model, bar in zip(models, bars):
        yval = bar.get_height()
        y = yval - 1
        va = "top"
        color = "#eee" if "Aider" in model else "#555"
        fontfamily = "Helvetica Bold" if "Aider" in model else "Helvetica"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            f"{yval}%",
            ha="center",
            va=va,
            fontsize=16,
            color=color,
            fontfamily=fontfamily,
        )

    # ax.set_xlabel("Models", fontsize=18)
    ax.set_ylabel("Instances resolved (%)", fontsize=18, color=font_color)
    if "lite" in data_file:
        title = "SWE Bench Lite"
    else:
        title = "SWE Bench"
    ax.set_title(title, fontsize=20)
    # ax.set_ylim(0, 29.9)
    plt.xticks(
        fontsize=16,
        color=font_color,
    )

    # Add note at the bottom of the graph
    note = (
        "Note: (570) and (2294) refer to the number of SWE Bench instances that were benchmarked."
    )
    plt.figtext(
        0.5,
        0.05,
        note,
        wrap=True,
        horizontalalignment="center",
        fontsize=12,
        color=font_color,
    )

    plt.tight_layout(pad=3.0, rect=[0, 0.05, 1, 1])

    out_fname = Path(data_file.replace("-", "_"))
    plt.savefig(out_fname.with_suffix(".jpg").name)
    plt.savefig(out_fname.with_suffix(".svg").name)
    imgcat(fig)
    ax.xaxis.label.set_color(font_color)


fname = sys.argv[1]
plot_swe_bench_lite(fname)
