import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# -------------------------
# Paths
# -------------------------
BASE_DIR = "gform_csvs/"
PROCESSED_DIR = BASE_DIR + "processed_data/"
FIGURES_DIR = PROCESSED_DIR + "figures/"

LABEL_FILE = PROCESSED_DIR + "friendliness_label_summary.csv"
CHAT_FILE = PROCESSED_DIR + "friendliness_chat_scores.csv"

os.makedirs(FIGURES_DIR, exist_ok=True)

# -------------------------
# Global plotting style
# -------------------------
# plt.rcParams.update({
#     "figure.figsize": (6, 4),
#     "font.size": 10,
#     "axes.labelsize": 10,
#     "axes.titlesize": 11,
#     "legend.fontsize": 9,
#     "xtick.labelsize": 9,
#     "ytick.labelsize": 9,
#     "svg.fonttype": "none"  # keep text as text in SVG (LaTeX-friendly)
# })

# -------------------------
# Figure 1: Label distribution (grouped bar chart)
# -------------------------
df_labels = pd.read_csv(LABEL_FILE)

required_cols = {
    "label",
    "human_rate_mean_probability",
    "llm_rate_fraction_of_turns_predicted"
}
missing = required_cols - set(df_labels.columns)
if missing:
    raise ValueError(f"Missing columns in label summary: {missing}")

# Sort labels by human rate (descending)
df_labels = df_labels.sort_values(
    by="human_rate_mean_probability",
    ascending=False
)

labels = df_labels["label"].tolist()
human_rates = df_labels["human_rate_mean_probability"].values
llm_rates = df_labels["llm_rate_fraction_of_turns_predicted"].values

x = np.arange(len(labels))
width = 0.35

fig, ax = plt.subplots(figsize=(6, 4))

ax.bar(
    x - width / 2,
    human_rates,
    width,
    label="Humans",
    color="#4C72B0"
)

ax.bar(
    x + width / 2,
    llm_rates,
    width,
    label="LLM",
    color="#DD8452"
)

ax.set_xlabel("Friendliness label")
ax.set_ylabel("Proportion of turns")
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylim(0, 1.0)
ax.legend(frameon=True)

fig.tight_layout()

label_fig_path = FIGURES_DIR + "fig_label_distribution.svg"
fig.savefig(label_fig_path, format="svg")
plt.close(fig)

print(f"Saved label distribution figure to: {label_fig_path}")

# -------------------------
# Figure 2: Chat-level Soft Jaccard comparison
# -------------------------
df_chat = pd.read_csv(CHAT_FILE)

required_cols = {
    "chat_id",
    "mean_soft_jaccard_llm",
    "mean_soft_jaccard_human_baseline"
}
missing = required_cols - set(df_chat.columns)
if missing:
    raise ValueError(f"Missing columns in chat-level summary: {missing}")

# Sort chats consistently (alphabetical or original order)
df_chat = df_chat.sort_values("chat_id")

chat_ids = df_chat["chat_id"].tolist()
llm_scores = df_chat["mean_soft_jaccard_llm"].values
human_scores = df_chat["mean_soft_jaccard_human_baseline"].values

x = np.arange(len(chat_ids))
offset = 0.0

fig, ax = plt.subplots(figsize=(6, 4))

# Connecting lines
for i in range(len(chat_ids)):
    ax.plot(
        [x[i] - offset, x[i] + offset],
        [llm_scores[i], human_scores[i]],
        color="gray",
        alpha=0.6,
        linewidth=1,
        zorder=1
    )

# Points
ax.scatter(
    x - offset,
    llm_scores,
    label="LLM vs Humans",
    color="#DD8452",
    s=60,
    zorder=2
)

ax.scatter(
    x + offset,
    human_scores,
    label="Human baseline",
    color="#4C72B0",
    s=70,
    marker="x",
    linewidths=2,
    zorder=3
)

ax.set_xlabel("Chat history")
ax.set_ylabel("Mean Soft Jaccard similarity")
ax.set_xticks(x)
ax.set_xticklabels(chat_ids, rotation=0)
ax.set_ylim(0, 1.0)
ax.legend(frameon=True)

fig.tight_layout()

chat_fig_path = FIGURES_DIR + "fig_chat_soft_jaccard.svg"
fig.savefig(chat_fig_path, format="svg")
plt.close(fig)

print(f"Saved chat-level Soft Jaccard figure to: {chat_fig_path}")

print("\nFigure generation complete.")
