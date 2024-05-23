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
            models.append(model.strip())
            pass_rates.append(float(pass_rate.strip()))

    plt.rcParams["hatch.linewidth"] = 0.5
    plt.rcParams["hatch.color"] = "#444444"

    font_color = "#555"
    rc("font", **{"family": "sans-serif", "sans-serif": ["Helvetica"], "size": 10})
    plt.rcParams["text.color"] = font_color

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.grid(axis="y", zorder=0, lw=0.2)
    for spine in ax.spines.values():
        spine.set_edgecolor("#DDDDDD")
        spine.set_linewidth(0.5)

    colors = ["#b3e6a8" if "Aider" in model else "#b3d1e6" for model in models]
    bars = ax.bar(models, pass_rates, color=colors, alpha=0.75, zorder=3)

    for bar in bars:
        yval = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            yval - 1.25,
            f"{yval}%",
            ha="center",
            va="top",
            fontsize=14,
            # alpha=0.75,
        )

    # ax.set_xlabel("Models", fontsize=18)
    ax.set_ylabel("Instances resolved (%)", fontsize=18, color=font_color)
    ax.set_title("SWE Bench Lite", fontsize=20)
    ax.set_ylim(0, 29)
    plt.xticks(
        # rotation=45,
        # ha="center",
        fontsize=16,
        color=font_color,
    )
    plt.tight_layout(pad=3.0)
    plt.savefig("swe_bench_lite.jpg")
    plt.savefig("swe_bench_lite.svg")
    imgcat(fig)
    ax.xaxis.label.set_color(font_color)


# Example usage
plot_swe_bench_lite("benchmark/tmp.txt")
