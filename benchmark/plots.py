import matplotlib.pyplot as plt
import numpy as np
from imgcat import imgcat

from aider.dump import dump  # noqa: F401


def plot_timing(df):
    """plot a graph showing the average duration of each (model, edit_format)"""
    plt.rcParams["hatch.linewidth"] = 0.5
    plt.rcParams["hatch.color"] = "#444444"

    from matplotlib import rc

    rc("font", **{"family": "sans-serif", "sans-serif": ["Helvetica"], "size": 10})

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.grid(axis="y", zorder=0, lw=0.2)

    zorder = 1
    grouped = df.groupby(["model", "edit_format"])["avg_duration"].mean().unstack()
    num_models, num_formats = grouped.shape

    pos = np.array(range(num_models))
    width = 0.8 / num_formats

    formats = grouped.columns
    models = grouped.index

    for i, fmt in enumerate(formats):
        edge = dict(edgecolor="#ffffff", linewidth=1.5)
        color = "#b3e6a8" if "diff" in fmt else "#b3d1e6"
        hatch = "////" if "func" in fmt else ""
        rects = ax.bar(
            pos + i * width,
            grouped[fmt],
            width * 0.95,
            label=fmt,
            color=color,
            hatch=hatch,
            zorder=zorder + 1,
            **edge,
        )
        ax.bar_label(rects, padding=4, labels=[f"{v:.1f}s" for v in grouped[fmt]], size=6)

    ax.set_xticks([p + 0.5 * width for p in pos])
    ax.set_xticklabels(models)

    ax.set_ylabel("Average GPT response time\nper exercise (sec)")
    ax.set_title("GPT Code Editing Speed\n(time per coding task)")
    ax.legend(
        title="Edit Format",
        loc="upper left",
    )
    ax.set_ylim(top=max(grouped.max()) * 1.1)  # Set y-axis limit to 10% more than the max value

    plt.tight_layout()
    plt.savefig("tmp_timing.svg")
    imgcat(fig)


def plot_outcomes(df, repeats, repeat_hi, repeat_lo, repeat_avg):
    tries = [df.groupby(["model", "edit_format"])["pass_rate_2"].mean()]
    if True:
        tries += [df.groupby(["model", "edit_format"])["pass_rate_1"].mean()]

    plt.rcParams["hatch.linewidth"] = 0.5
    plt.rcParams["hatch.color"] = "#444444"

    from matplotlib import rc

    rc("font", **{"family": "sans-serif", "sans-serif": ["Helvetica"], "size": 10})

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.grid(axis="y", zorder=0, lw=0.2)

    zorder = 1
    for grouped in tries:
        zorder += 1
        df = grouped.unstack()
        num_models, num_formats = df.shape

        pos = np.array(range(num_models))
        width = 0.8 / num_formats

        formats = df.columns
        models = df.index

        for i, fmt in enumerate(formats):
            if zorder > 1:
                edge = dict(
                    edgecolor="#ffffff",
                    linewidth=1.5,
                )
            else:
                edge = dict()
            if zorder == 2:
                edge["label"] = fmt

            color = "#b3e6a8" if "diff" in fmt else "#b3d1e6"
            hatch = "////" if "func" in fmt else ""
            rects = ax.bar(
                pos + i * width,
                df[fmt],
                width * 0.95,
                color=color,
                hatch=hatch,
                zorder=zorder,
                **edge,
            )
            if zorder == 2:
                ax.bar_label(rects, padding=4, labels=[f"{v:.0f}%" for v in df[fmt]], size=6)

    if len(repeats):
        ax.errorbar(
            1.4,
            repeat_avg,
            yerr=[[repeat_lo], [repeat_hi]],
            fmt="none",
            zorder=5,
            capsize=2.5,
            elinewidth=1,
            markeredgewidth=1,
        )

    ax.set_xticks([p + 0.5 * width for p in pos])
    model_labels = []
    for model in models:
        pieces = model.split("-")
        ml = "-".join(pieces[:2]) + "-\n" + "-".join(pieces[2:])
        model_labels.append(ml)

    ax.set_xticklabels(model_labels)

    top = 95
    ax.annotate(
        "First attempt,\nbased on\nnatural language\ninstructions",
        xy=(2.20, 41),
        xytext=(2, top),
        horizontalalignment="center",
        verticalalignment="top",
        arrowprops={"arrowstyle": "->", "connectionstyle": "arc3,rad=0.3"},
    )
    ax.annotate(
        "Second attempt,\nincluding unit test\nerror output",
        xy=(2.55, 56),
        xytext=(3.5, top),
        horizontalalignment="center",
        verticalalignment="top",
        arrowprops={"arrowstyle": "->", "connectionstyle": "arc3,rad=0.3"},
    )

    ax.set_ylabel("Percent of exercises completed successfully")
    # ax.set_xlabel("Model")
    ax.set_title("GPT Code Editing Skill\n(percent coding tasks correct)")
    ax.legend(
        title="Edit Format",
        loc="upper left",
        # bbox_to_anchor=(0.95, 0.95),
    )
    ax.set_ylim(top=100)

    plt.tight_layout()
    plt.savefig("tmp.svg")
    imgcat(fig)

    # df.to_csv("tmp.benchmarks.csv")


def plot_outcomes_claude(df):
    print(df)

    # Fix wrong column label
    df["model"] = df["model"].replace("gpt-4-0314", "gpt-4-0613")

    tries = [
        df[["model", "pass_rate_2"]],
        df[["model", "pass_rate_1"]],
    ]

    plt.rcParams["hatch.linewidth"] = 0.5
    plt.rcParams["hatch.color"] = "#444444"

    from matplotlib import rc

    rc("font", **{"family": "sans-serif", "sans-serif": ["Helvetica"], "size": 10})

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.grid(axis="y", zorder=0, lw=0.2)

    zorder = 1
    for df in tries:
        zorder += 1
        print(df)

        num_models, _ = df.shape
        num_formats = 1

        pos = np.array(range(num_models))
        width = 0.6 / num_formats

        if zorder > 1:
            edge = dict(
                edgecolor="#ffffff",
                linewidth=1.5,
            )
        else:
            edge = dict()
        if zorder == 2:
            edge["label"] = "??"

        color = [
            "#b3e6a8",
            "#b3e6a8",
            "#b3e6a8",
            "#b3d1e6",
        ]
        hatch = [  # noqa: F841
            "",
            "",
            "",
            "",
            "////",
            "////",
            "////",
            "",
            "////",
        ]
        hatch = [  # noqa: F841
            "////",
            "////",
            "////",
            "////",
            "",
            "",
            "",
            "////",
            "",
        ]
        rects = ax.bar(
            pos + 0.5 * width,
            df.iloc[:, 1],
            width * 0.95,
            color=color,
            # hatch=hatch,
            # zorder=zorder,
            **edge,
        )
        if zorder == 2:
            ax.bar_label(rects, padding=4, labels=[f"{v:.0f}%" for v in df.iloc[:, 1]], size=6)

    ax.set_xticks([p + 0.5 * width for p in pos])

    models = df.iloc[:, 0]
    model_map = {
        "gpt-4-0613": "gpt-4-\n0613",
        "gpt-4-0125-preview": "gpt-4-\n0125-preview",
        "gpt-4-1106-preview": "gpt-4-\n1106-preview",
        "gpt-4-turbo-2024-04-09": "gpt-4-turbo-\n2024-04-09\n(GPT-4 Turbo with Vision)",
    }
    model_labels = []
    for model in models:
        ml = model_map.get(model, model)
        model_labels.append(ml)
    ax.set_xticklabels(model_labels, rotation=0)

    top = 95
    ax.annotate(
        "First attempt,\nbased on\nnatural language\ninstructions",
        xy=(1.0, 53),
        xytext=(0.75, top),
        horizontalalignment="center",
        verticalalignment="top",
        arrowprops={"arrowstyle": "->", "connectionstyle": "arc3,rad=0.3"},
    )
    ax.annotate(
        "Second attempt,\nincluding unit test\nerror output",
        xy=(1.55, 65),
        xytext=(1.9, top),
        horizontalalignment="center",
        verticalalignment="top",
        arrowprops={"arrowstyle": "->", "connectionstyle": "arc3,rad=0.3"},
    )

    ax.set_ylabel("Percent of exercises completed successfully")
    # ax.set_xlabel("Model")
    ax.set_title("Code Editing Skill")
    # ax.legend(
    #    title="Model family",
    #    loc="upper left",
    # )
    ax.set_ylim(top=100)

    plt.tight_layout()
    plt.savefig("tmp.svg")
    imgcat(fig)

    # df.to_csv("tmp.benchmarks.csv")


def plot_refactoring(df):
    tries = [df.groupby(["model", "edit_format"])["pass_rate_1"].mean()]

    plt.rcParams["hatch.linewidth"] = 0.5
    plt.rcParams["hatch.color"] = "#444444"

    from matplotlib import rc

    rc("font", **{"family": "sans-serif", "sans-serif": ["Helvetica"], "size": 10})

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.grid(axis="y", zorder=0, lw=0.2)

    zorder = 1
    for grouped in tries:
        zorder += 1
        df = grouped.unstack()

        i, j = 0, 1
        temp = df.iloc[i].copy()
        df.iloc[i], df.iloc[j] = df.iloc[j], temp
        dump(df)

        # df.sort_values(by=["model"], ascending=False, inplace=True)
        num_models, num_formats = df.shape

        pos = np.array(range(num_models))
        width = 0.8 / num_formats

        formats = df.columns
        models = df.index

        dump(df)
        dump(models)
        dump(formats)
        for i, fmt in enumerate(formats):
            hatch = ""

            if fmt == "diff":
                color = "#b3e6a8"
                label = "Search/replace blocks"
            elif fmt == "udiff":
                color = "#b3d1e6"
                label = "Unified diffs"
            elif fmt == "difffolk":
                label = "Baseline + blind, no hands, $2k tip, etc"
                color = "#b3e6a8"
                hatch = "////"
            elif fmt == "udifffolk":
                label = "Unified diffs + blind, no hands, $2k tip, etc"
                color = "#b3d1e6"
                hatch = "////"

            if zorder > 1:
                edge = dict(
                    edgecolor="#ffffff",
                    linewidth=1.5,
                )
            else:
                edge = dict()
            if zorder == 2:
                edge["label"] = label

            color = [
                "#b3e6a8",
                "#b3e6a8",
                "#b3d1e6",
            ]

            rects = ax.bar(
                pos + i * width,
                df[fmt],
                width * 0.95,
                color=color,
                hatch=hatch,
                zorder=zorder,
                **edge,
            )

            if zorder == 2:
                ax.bar_label(rects, padding=4, labels=[f"{v:.0f}%" for v in df[fmt]], size=6)

    ax.set_xticks([p + 0 * width for p in pos])

    model_map = {
        "gpt-4-0125-preview": "gpt-4-\n0125-preview",
        "gpt-4-1106-preview": "gpt-4-\n1106-preview",
        "gpt-4-turbo-2024-04-09": "gpt-4-turbo-\n2024-04-09\n(GPT-4 Turbo with Vision)",
    }
    model_labels = []

    for model in models:
        ml = model_map.get(model, model)
        model_labels.append(ml)

    model_labels = [
        "gpt-4-\n1106-preview",
        "gpt-4-\n0125-preview",
        "gpt-4-turbo-\n2024-04-09\n(GPT-4 Turbo with Vision)",
    ]
    ax.set_xticklabels(model_labels, rotation=0)

    ax.set_ylabel("Percent of exercises completed successfully")
    # ax.set_xlabel("Model")
    ax.set_title('Refactoring "Laziness" Benchmark')
    # ax.legend(
    # title="Edit Format",
    # loc="upper left",
    # bbox_to_anchor=(0.95, 0.95),
    # )
    ax.set_ylim(top=100)

    plt.tight_layout()
    plt.savefig("tmp.svg")
    imgcat(fig)

    # df.to_csv("tmp.benchmarks.csv")
