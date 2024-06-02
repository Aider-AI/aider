import sys
from pathlib import Path

import matplotlib.pyplot as plt
from imgcat import imgcat
from matplotlib import rc

from aider.dump import dump  # noqa: F401


def plot_swe_bench(data_file, is_lite):
    with open(data_file, "r") as file:
        lines = file.readlines()

    models = []
    pass_rates = []
    instances = []
    for line in lines:
        if line.strip():
            pass_rate, model = line.split("%")
            model = model.strip()
            if "(" in model:
                pieces = model.split("(")
                model = pieces[0]
                ins = pieces[1].strip(")")
            else:
                ins = None
            instances.insert(0, ins)
            model = model.replace("|", "\n")
            models.insert(0, model.strip())
            pass_rates.insert(0, float(pass_rate.strip()))

    dump(instances)

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

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.grid(axis="y", zorder=0, lw=0.2)
    for spine in ax.spines.values():
        spine.set_edgecolor("#DDDDDD")
        spine.set_linewidth(0.5)

    if is_lite:
        colors = ["#17965A" if "Aider" in model else "#b3d1e6" for model in models]
    else:
        colors = ["#1A75C2" if "Aider" in model else "#b3d1e6" for model in models]

    bars = []
    for model, pass_rate, color in zip(models, pass_rates, colors):
        alpha = 0.9 if "Aider" in model else 0.3
        hatch = ""
        # if is_lite:
        #    hatch = "///" if "(570)" in model else ""
        bar = ax.bar(model, pass_rate, color=color, alpha=alpha, zorder=3, hatch=hatch)
        bars.append(bar[0])

    for label in ax.get_xticklabels():
        if "Aider" in str(label):
            label.set_fontfamily("Helvetica Bold")

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

    for model, ins, bar in zip(models, instances, bars):
        if not ins:
            continue
        yval = bar.get_height()
        y = yval - 2.5
        va = "top"
        color = "#eee" if "Aider" in model else "#555"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            f"of {ins}",
            ha="center",
            va=va,
            fontsize=12,
            color=color,
        )

    # ax.set_xlabel("Models", fontsize=18)
    ax.set_ylabel("Pass@1 (%)", fontsize=18, color=font_color)
    if is_lite:
        title = "SWE Bench Lite"
    else:
        title = "SWE Bench"
    ax.set_title(title, fontsize=20)
    # ax.set_ylim(0, 29.9)
    plt.xticks(
        fontsize=16,
        color=font_color,
    )

    plt.tight_layout(pad=3.0)

    out_fname = Path(data_file.replace("-", "_"))
    plt.savefig(out_fname.with_suffix(".jpg").name)
    plt.savefig(out_fname.with_suffix(".svg").name)
    imgcat(fig)
    ax.xaxis.label.set_color(font_color)


fname = sys.argv[1]
is_lite = "lite" in fname

plot_swe_bench(fname, is_lite)
