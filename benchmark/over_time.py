import matplotlib.pyplot as plt
import yaml
from imgcat import imgcat
from matplotlib import rc

from aider.dump import dump  # noqa: 401


def get_legend_label(model):
    model = model.lower()
    if "claude-3-opus" in model:
        return "Opus"
    if "claude-3-sonnet" in model:
        return "Sonnet"
    if "gpt-3.5" in model:
        return "GPT-3.5 Turbo"
    if "gpt-4-" in model and "-4o" not in model:
        return "GPT-4"
    if "qwen" in model:
        return "Qwen"
    if "-4o" in model:
        return "GPT-4o"
    if "haiku" in model:
        return "Haiku"
    if "deepseek" in model:
        return "DeepSeek"
    if "mistral" in model:
        return "Mistral"
    return model


def get_model_color(model):
    default = "lightblue"

    if model == "gpt-4o-mini":
        return default

    if "qwen" in model.lower():
        return "darkblue"

    if "mistral" in model.lower():
        return "cyan"

    if "haiku" in model.lower():
        return "pink"

    if "deepseek" in model.lower():
        return "brown"

    if "sonnet" in model.lower():
        return "orange"

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

    fig, ax = plt.subplots(figsize=(12, 8))  # Make figure square

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
    orange_points = [(d, r) for d, r, c in zip(dates, pass_rates, colors) if c == "orange"]
    brown_points = [(d, r) for d, r, c in zip(dates, pass_rates, colors) if c == "brown"]
    pink_points = [(d, r) for d, r, c in zip(dates, pass_rates, colors) if c == "pink"]
    qwen_points = [(d, r) for d, r, c in zip(dates, pass_rates, colors) if c == "darkblue"]
    mistral_points = [(d, r) for d, r, c in zip(dates, pass_rates, colors) if c == "cyan"]

    # Plot lines for purple, red, green, orange and brown points
    if purple_points:
        purple_dates, purple_rates = zip(*sorted(purple_points))
        ax.plot(purple_dates, purple_rates, c="purple", alpha=0.5, linewidth=1)
    if red_points:
        red_dates, red_rates = zip(*sorted(red_points))
        ax.plot(red_dates, red_rates, c="red", alpha=0.5, linewidth=1)
    if green_points:
        green_dates, green_rates = zip(*sorted(green_points))
        ax.plot(green_dates, green_rates, c="green", alpha=0.5, linewidth=1)
    if orange_points:
        orange_dates, orange_rates = zip(*sorted(orange_points))
        ax.plot(orange_dates, orange_rates, c="orange", alpha=0.5, linewidth=1)
    if brown_points:
        brown_dates, brown_rates = zip(*sorted(brown_points))
        ax.plot(brown_dates, brown_rates, c="brown", alpha=0.5, linewidth=1)
    if pink_points:
        pink_dates, pink_rates = zip(*sorted(pink_points))
        ax.plot(pink_dates, pink_rates, c="pink", alpha=0.5, linewidth=1)
    if qwen_points:
        qwen_dates, qwen_rates = zip(*sorted(qwen_points))
        ax.plot(qwen_dates, qwen_rates, c="darkblue", alpha=0.5, linewidth=1)
    if mistral_points:
        mistral_dates, mistral_rates = zip(*sorted(mistral_points))
        ax.plot(mistral_dates, mistral_rates, c="cyan", alpha=0.5, linewidth=1)

    # Create legend handles
    legend_handles = []
    legend_labels = []

    # Plot points and collect unique model types for legend
    seen_colors = {}
    for i, (date, rate, color, model) in enumerate(zip(dates, pass_rates, colors, models)):
        if color not in seen_colors:
            # First time seeing this color, add to legend
            scatter = ax.scatter([date], [rate], c=[color], alpha=0.5, s=120)
            legend_handles.append(scatter)
            # Use simplified name for legend label
            legend_labels.append(get_legend_label(model))
            seen_colors[color] = True
        else:
            # Just plot the point without adding to legend
            ax.scatter([date], [rate], c=[color], alpha=0.5, s=120)

    ax.set_xlabel("Model release date", fontsize=18, color="#555")
    ax.set_ylabel(
        "Aider code editing benchmark,\npercent completed correctly", fontsize=18, color="#555"
    )
    ax.set_title("LLM code editing skill by model release date", fontsize=20)
    ax.set_ylim(30, 90)  # Adjust y-axis limit to accommodate higher values
    plt.xticks(fontsize=14, rotation=45, ha="right")  # Rotate x-axis labels for better readability
    # Add legend
    ax.legend(
        legend_handles, legend_labels, loc="center left", bbox_to_anchor=(1, 0.5), fontsize=10
    )

    plt.tight_layout(pad=3.0, rect=[0, 0, 0.85, 1])  # Adjust layout to make room for legend

    print("Debug: Saving figures...")
    plt.savefig("tmp_over_time.png")
    plt.savefig("tmp_over_time.svg")

    print("Debug: Displaying figure with imgcat...")
    imgcat(fig)

    print("Debug: Figure generation complete.")


# Example usage
plot_over_time("aider/website/_data/edit_leaderboard.yml")
