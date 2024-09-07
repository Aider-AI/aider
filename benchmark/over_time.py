import matplotlib.pyplot as plt
import yaml
from imgcat import imgcat
from matplotlib import rc

from aider.dump import dump  # noqa: 401


def get_model_color(model):
    default = "lightblue"

    if model == "gpt-4o-mini":
        return default

    if "-4o" in model:
        return "purple"

    if "gpt-4" in model:
        return "red"

    if "gpt-3.5" in model:
        return "green"

    return default


def plot_over_time(yaml_file):
    with open(yaml_file, "r") as file:
        data = yaml.safe_load(file)

    dates = []
    pass_rates = []
    models = []

    print("Debug: Raw data from YAML file:")
    print(data)

    for entry in data:
        if "released" in entry and "pass_rate_2" in entry:
            dates.append(entry["released"])
            pass_rates.append(entry["pass_rate_2"])
            models.append(entry["model"].split("(")[0].strip())

    print("Debug: Processed data:")
    print("Dates:", dates)
    print("Pass rates:", pass_rates)
    print("Models:", models)

    if not dates or not pass_rates:
        print(
            "Error: No data to plot. Check if the YAML file is empty or if the data is in the"
            " expected format."
        )
        return

    plt.rcParams["hatch.linewidth"] = 0.5
    plt.rcParams["hatch.color"] = "#444444"

    rc("font", **{"family": "sans-serif", "sans-serif": ["Helvetica"], "size": 10})
    plt.rcParams["text.color"] = "#444444"

    fig, ax = plt.subplots(figsize=(12, 6))  # Increase figure size for better visibility

    print("Debug: Figure created. Plotting data...")
    ax.grid(axis="y", zorder=0, lw=0.2)
    for spine in ax.spines.values():
        spine.set_edgecolor("#DDDDDD")
        spine.set_linewidth(0.5)

    colors = [get_model_color(model) for model in models]

    # Separate data points by color
    purple_points = [(d, r) for d, r, c in zip(dates, pass_rates, colors) if c == "purple"]
    red_points = [(d, r) for d, r, c in zip(dates, pass_rates, colors) if c == "red"]
    green_points = [(d, r) for d, r, c in zip(dates, pass_rates, colors) if c == "green"]

    # Plot lines for purple, red, and green points
    if purple_points:
        purple_dates, purple_rates = zip(*sorted(purple_points))
        ax.plot(purple_dates, purple_rates, c="purple", alpha=0.5, linewidth=1)
    if red_points:
        red_dates, red_rates = zip(*sorted(red_points))
        ax.plot(red_dates, red_rates, c="red", alpha=0.5, linewidth=1)
    if green_points:
        green_dates, green_rates = zip(*sorted(green_points))
        ax.plot(green_dates, green_rates, c="green", alpha=0.5, linewidth=1)

    # Plot all points
    ax.scatter(dates, pass_rates, c=colors, alpha=0.5, s=120)

    for i, model in enumerate(models):
        ax.annotate(
            model,
            (dates[i], pass_rates[i]),
            fontsize=8,
            alpha=0.75,
            xytext=(5, 5),
            textcoords="offset points",
        )

    ax.set_xlabel("Model release date", fontsize=18, color="#555")
    ax.set_ylabel(
        "Aider code editing benchmark,\npercent completed correctly", fontsize=18, color="#555"
    )
    ax.set_title("LLM code editing skill by model release date", fontsize=20)
    ax.set_ylim(0, 100)  # Adjust y-axis limit to accommodate higher values
    plt.xticks(fontsize=14, rotation=45, ha="right")  # Rotate x-axis labels for better readability
    plt.tight_layout(pad=3.0)

    print("Debug: Saving figures...")
    plt.savefig("tmp_over_time.png")
    plt.savefig("tmp_over_time.svg")

    print("Debug: Displaying figure with imgcat...")
    imgcat(fig)

    print("Debug: Figure generation complete.")


# Example usage
plot_over_time("aider/website/_data/edit_leaderboard.yml")
