import matplotlib.pyplot as plt
import yaml
from datetime import datetime
from matplotlib import rc
from imgcat import imgcat

def plot_over_time(yaml_file):
    with open(yaml_file, 'r') as file:
        data = yaml.safe_load(file)

    dates = []
    pass_rates = []
    models = []

    for entry in data:
        if 'released' in entry and 'pass_rate_2' in entry:
            dates.append(entry['released'])
            pass_rates.append(entry['pass_rate_2'])
            models.append(entry['model'])

    plt.rcParams["hatch.linewidth"] = 0.5
    plt.rcParams["hatch.color"] = "#444444"

    rc("font", **{"family": "sans-serif", "sans-serif": ["Helvetica"], "size": 10})

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.grid(axis="y", zorder=0, lw=0.2)
    colors = ['red' if 'gpt-4' in model else 'green' if 'gpt-3.5' in model else 'blue' for model in models]
    ax.scatter(dates, pass_rates, c=colors, alpha=0.5)

    for i, model in enumerate(models):
        ax.annotate(model, (dates[i], pass_rates[i]), fontsize=8, alpha=0.75)

    ax.set_xlabel('Release Date')
    ax.set_ylabel('Pass Rate 2')
    ax.set_title('Model Performance Over Time')
    plt.tight_layout()
    plt.savefig("tmp_over_time.png")
    imgcat(fig)

# Example usage
plot_over_time('_data/edit_leaderboard.yml')
