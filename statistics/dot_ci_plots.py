import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def plot_dot_ci(
    group_stats_file,
    individual_stats_file,
    condition_col,
    mean_col,
    ci_low_col,
    ci_high_col,
    unit_col,
    conditions,
    x_labels,
    title,
    y_label,
    output_path,
    y_limits=(1, 4),
    jitter=0.08,
    x_spacing=0.25
):
    """
    Creates a dot + CI plot:
    - individual means as dots (jittered)
    - group mean as large dot
    - 95% CI as vertical line
    """

    colors = ["#4C72B0", "#DD8452"]  # blue, orange

    # Load data
    df_group = pd.read_csv(group_stats_file)
    df_ind = pd.read_csv(individual_stats_file)

    # Basic validation
    required_group = {condition_col, mean_col, ci_low_col, ci_high_col}
    required_ind = {condition_col, mean_col, unit_col}

    if not required_group.issubset(df_group.columns):
        raise ValueError("Group stats file missing required columns")

    if not required_ind.issubset(df_ind.columns):
        raise ValueError("Individual stats file missing required columns")

    fig, ax = plt.subplots(figsize=(6, 4))

    for i, condition in enumerate(conditions):
        center = (len(conditions) - 1) / 2
        x = (i - center) * x_spacing

        # ---- Group stats ----
        g = df_group[df_group[condition_col] == condition].iloc[0]

        ax.vlines(
            x,
            g[ci_low_col],
            g[ci_high_col],
            color="grey",
            alpha=0.9,
            linewidth=2,
            zorder=1,
            label="95% CI" if i == 0 else None
        )

        ax.scatter(
            x,
            g[mean_col],
            s=120,
            color=colors[0],
            zorder=3,
            label="Group mean" if i == 0 else None
        )

        # ---- Individual stats ----
        ind = df_ind[df_ind[condition_col] == condition]

        jittered_x = x + np.random.uniform(-jitter, jitter, size=len(ind))

        ax.scatter(
            jittered_x,
            ind[mean_col],
            s=40,
            color=colors[1],
            alpha=0.8,
            zorder=2,
            label="Individual means" if i == 0 else None
        )

    # ---- Axes & layout ----
    center = (len(x_labels) - 1) / 2
    ax.set_xticks([(i - center) * x_spacing for i in range(len(x_labels))])
    ax.set_xticklabels(x_labels)
    ax.set_ylabel(y_label)
    ax.set_ylim(*y_limits)
    ax.set_title(title)

    ax.legend(frameon=True, fancybox=True)
    ax.grid(axis="y", alpha=0.25)

    plt.tight_layout()
    plt.savefig(output_path, format="svg")
    plt.close()

    print(f"Saved plot: {output_path}")


# =========================================================
# Function calls
# =========================================================

BASE_DIR = "gform_csvs/processed_data/"
FIGURES_DIR = BASE_DIR + "figures/"

# ---- Voice / Gesture plot ----
plot_dot_ci(
    group_stats_file=BASE_DIR + "voice_gesture_group_stats.csv",
    individual_stats_file=BASE_DIR + "voice_gesture_participant_stats.csv",
    condition_col="question",
    mean_col="mean",
    ci_low_col="ci_low",
    ci_high_col="ci_high",
    unit_col="participant",
    conditions=["voice", "gesture"],
    x_labels=["Voice", "Gesture"],
    title="Voice and Gesture Evaluation",
    y_label="Score",
    output_path=FIGURES_DIR + "voice_gesture_dot_ci.svg",
)

# ---- Chat evaluation plot ----
plot_dot_ci(
    group_stats_file=BASE_DIR + "chat_eval_chat_stats.csv",
    individual_stats_file=BASE_DIR + "chat_eval_rater_stats.csv",
    condition_col="dimension",
    mean_col="mean",
    ci_low_col="ci_low",
    ci_high_col="ci_high",
    unit_col="rater",
    conditions=[
        "nao_relevance_current",
        "nao_relevance_history",
    ],
    x_labels=["Current input", "Chat history"],
    title="Chat Response Relevance",
    y_label="Score",
    output_path=FIGURES_DIR + "chat_eval_dot_ci.svg",
    y_limits=(3.2, 4.4)
)
