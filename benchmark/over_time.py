import matplotlib.pyplot as plt
import yaml
from datetime import datetime

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

    plt.figure(figsize=(10, 6))
    colors = ['red' if 'gpt-4' in model else 'green' if 'gpt-3.5' in model else 'blue' for model in models]
    plt.scatter(dates, pass_rates, c=colors, alpha=0.5)

    for i, model in enumerate(models):
        plt.annotate(model, (dates[i], pass_rates[i]), fontsize=8, alpha=0.75)

    plt.xlabel('Release Date')
    plt.ylabel('Pass Rate 2')
    plt.title('Model Performance Over Time')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# Example usage
plot_over_time('_data/edit_leaderboard.yml')
