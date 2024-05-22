import matplotlib.pyplot as plt
from matplotlib import rc
from imgcat import imgcat

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

    rc("font", **{"family": "sans-serif", "sans-serif": ["Helvetica"], "size": 10})

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.grid(axis="y", zorder=0, lw=0.2)
    for spine in ax.spines.values():
        spine.set_edgecolor("#DDDDDD")
        spine.set_linewidth(0.5)

    colors = [
        "#b3e6a8" if "Aider" in model else "#b3d1e6" for model in models
    ]
    bars = ax.bar(models, pass_rates, color=colors, alpha=0.75, zorder=3)

    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 0.5, f'{yval}%', ha='center', va='bottom', fontsize=12, alpha=0.75)

    #ax.set_xlabel("Models", fontsize=18)
    ax.set_ylabel("Pass rate (%)", fontsize=18)
    ax.set_title("SWE Bench Lite pass rates", fontsize=20)
    ax.set_ylim(0, 30)
    plt.xticks(rotation=45, ha='right', fontsize=16)
    plt.tight_layout()
    plt.savefig("swe_bench_lite.png")
    plt.savefig("swe_bench_lite.svg")
    imgcat(fig)

# Example usage
plot_swe_bench_lite("benchmark/tmp.txt")
