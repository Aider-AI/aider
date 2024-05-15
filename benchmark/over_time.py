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

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.grid(axis="y", zorder=0, lw=0.2)
    for spine in ax.spines.values():
        spine.set_edgecolor('#DDDDDD')
        spine.set_linewidth(0.5)

    colors = ['red' if 'gpt-4' in model else 'green' if 'gpt-3.5' in model else 'blue' for model in models]
    ax.scatter(dates, pass_rates, c=colors, alpha=0.5, s=100)

    for i, model in enumerate(models):
        ax.annotate(model, (dates[i], pass_rates[i]), fontsize=12, alpha=0.75,
                    xytext=(5, 5), textcoords='offset points')

    ax.set_xlabel('Model release date', fontsize=14)
    ax.set_ylabel('Aider code editing benchmark,\npercent completed correctly', fontsize=14)
    ax.set_title('LLM code editing skill by model release date')
    plt.tight_layout()
    plt.savefig("tmp_over_time.png")
    imgcat(fig)

# Example usage
plot_over_time('_data/edit_leaderboard.yml')
