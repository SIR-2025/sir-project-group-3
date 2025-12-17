import pandas as pd
import numpy as np
from scipy import stats

# -------------------------
# Paths
# -------------------------
BASE_DIR = "gform_csvs/"
PROCESSED_DIR = BASE_DIR + "processed_data/"

INPUT_FILE = PROCESSED_DIR + "voice_gesture_eval_clean.csv"

PARTICIPANT_STATS_FILE = PROCESSED_DIR + "voice_gesture_participant_stats.csv"
GROUP_STATS_FILE = PROCESSED_DIR + "voice_gesture_group_stats.csv"

# -------------------------
# Config
# -------------------------
TARGET_SCORE = 3
ALPHA = 0.05

# -------------------------
# Load data
# -------------------------
df = pd.read_csv(INPUT_FILE)

required_cols = {"participant", "repetition", "question", "score"}
missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df["score"] = pd.to_numeric(df["score"], errors="coerce")

# -------------------------
# NaN diagnostics
# -------------------------
nan_summary = (
    df[df["score"].isna()]
    .groupby("question")
    .size()
)

if not nan_summary.empty:
    print("NaN values detected in scores:")
    print(nan_summary)
    df = df.dropna(subset=["score"])

# -------------------------
# Helper: confidence interval
# -------------------------
def mean_ci(data, alpha=0.05):
    n = len(data)
    if n <= 1:
        return np.nan, np.nan
    mean = np.mean(data)
    sem = stats.sem(data)
    h = sem * stats.t.ppf(1 - alpha / 2, n - 1)
    return mean - h, mean + h

# -------------------------
# Participant-level stats
# -------------------------
participant_rows = []

for (participant, question), group in df.groupby(
    ["participant", "question"]
):
    values = group["score"].values
    ci_low, ci_high = mean_ci(values, ALPHA)

    participant_rows.append({
        "participant": participant,
        "question": question,
        "mean": np.mean(values),
        "median": np.median(values),
        "std": np.std(values, ddof=1) if len(values) > 1 else np.nan,
        "min": np.min(values),
        "max": np.max(values),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "n": len(values)
    })

df_participant_stats = pd.DataFrame(participant_rows)
df_participant_stats.to_csv(PARTICIPANT_STATS_FILE, index=False)

# -------------------------
# Group-level stats + t-test
# -------------------------
group_rows = []

for question, group in df_participant_stats.groupby("question"):
    participant_means = group["mean"].values
    ci_low, ci_high = mean_ci(participant_means, ALPHA)

    t_stat, p_val = stats.ttest_1samp(
        participant_means,
        TARGET_SCORE,
        alternative="greater"
    )

    group_rows.append({
        "question": question,
        "mean": np.mean(participant_means),
        "median": np.median(participant_means),
        "std": np.std(participant_means, ddof=1) if len(participant_means) > 1 else np.nan,
        "min": np.min(participant_means),
        "max": np.max(participant_means),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "n_participants": len(participant_means),
        "t_statistic": t_stat,
        "p_value": p_val
    })

df_group_stats = pd.DataFrame(group_rows)
df_group_stats.to_csv(GROUP_STATS_FILE, index=False)

# -------------------------
# Done
# -------------------------
print("Voice/Gesture statistics complete.")
print(f"Participant-level stats written to: {PARTICIPANT_STATS_FILE}")
print(f"Group-level stats written to: {GROUP_STATS_FILE}")
