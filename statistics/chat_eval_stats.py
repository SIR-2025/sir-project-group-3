import pandas as pd
import numpy as np
from scipy import stats

# -------------------------
# Paths
# -------------------------
BASE_DIR = "gform_csvs/"
PROCESSED_DIR = BASE_DIR + "processed_data/"

INPUT_FILE = PROCESSED_DIR + "chat_eval_clean.csv"

RATER_STATS_FILE = PROCESSED_DIR + "chat_eval_rater_stats.csv"
CHAT_STATS_FILE = PROCESSED_DIR + "chat_eval_chat_stats.csv"

# -------------------------
# Config
# -------------------------
TARGET_SCORE = 3
ALPHA = 0.05

NUMERIC_DIMENSIONS = [
    "nao_relevance_current",
    "nao_relevance_history"
]

# -------------------------
# 1. Load data
# -------------------------
df = pd.read_csv(INPUT_FILE)

required_cols = {"chat_id", "rater", "dimension", "value"}
missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {missing}")

# -------------------------
# 2. Filter numeric dimensions
# -------------------------
df_num = df[df["dimension"].isin(NUMERIC_DIMENSIONS)].copy()

# Ensure numeric
df_num["value"] = pd.to_numeric(df_num["value"], errors="coerce")

print("Checking for NaN values")
nan_summary = (
    df_num[df_num["value"].isna()]
    .groupby("dimension")
    .size()
)

if not nan_summary.empty:
    print("NaN values detected in numeric scores:")
    print(nan_summary)
    # raise ValueError("NaN values detected — aborting.")
    df_num = df_num.dropna(subset=["value"])


# -------------------------
# Helper: confidence interval
# -------------------------
def mean_ci(data, alpha=0.05):
    n = len(data)
    mean = np.mean(data)
    sem = stats.sem(data)
    if n <= 1:
        return np.nan, np.nan
    h = sem * stats.t.ppf(1 - alpha / 2, n - 1)
    return mean - h, mean + h

# -------------------------
# 3. Rater-level stats
# -------------------------
print("Calculating rater-level stats")
rater_rows = []

for (chat_id, rater, dimension), group in df_num.groupby(
    ["chat_id", "rater", "dimension"]
):
    values = group["value"].values

    ci_low, ci_high = mean_ci(values, ALPHA)

    rater_rows.append({
        "chat_id": chat_id,
        "rater": rater,
        "dimension": dimension,
        "mean": np.mean(values),
        "median": np.median(values),
        "std": np.std(values, ddof=1) if len(values) > 1 else np.nan,
        "min": np.min(values),
        "max": np.max(values),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "n": len(values)
    })

df_rater_stats = pd.DataFrame(rater_rows)
df_rater_stats.to_csv(RATER_STATS_FILE, index=False)

# -------------------------
# 4. Chat-level stats + t-test
# -------------------------
print("Calculating chat-level stats and t-test")
chat_rows = []

for (chat_id, dimension), group in df_rater_stats.groupby(
    ["chat_id", "dimension"]
):
    rater_means = group["mean"].values

    ci_low, ci_high = mean_ci(rater_means, ALPHA)

    # One-sample t-test vs target
    t_stat, p_val = stats.ttest_1samp(
        rater_means,
        TARGET_SCORE,
        alternative="greater"
    )

    chat_rows.append({
        "chat_id": chat_id,
        "dimension": dimension,
        "mean": np.mean(rater_means),
        "median": np.median(rater_means),
        "std": np.std(rater_means, ddof=1) if len(rater_means) > 1 else np.nan,
        "min": np.min(rater_means),
        "max": np.max(rater_means),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "n_raters": len(rater_means),
        "t_statistic": t_stat,
        "p_value": p_val
    })

df_chat_stats = pd.DataFrame(chat_rows)
df_chat_stats.to_csv(CHAT_STATS_FILE, index=False)

# -------------------------
# 5. Done
# -------------------------
print("Statistics computation complete.")
print(f"Rater-level stats written to: {RATER_STATS_FILE}")
print(f"Chat-level stats written to: {CHAT_STATS_FILE}")


# -------------------------
# 5. Aggregated LLM-level stats (rater × chat)
# -------------------------
print("Calculating aggregated LLM-level stats (rater × chat)")

AGGREGATED_STATS_FILE = PROCESSED_DIR + "chat_eval_aggregated_llm_stats.csv"

agg_rows = []

for dimension, group in df_rater_stats.groupby("dimension"):
    values = group["mean"].values  # rater × chat means

    ci_low, ci_high = mean_ci(values, ALPHA)

    t_stat, p_val = stats.ttest_1samp(
        values,
        TARGET_SCORE,
        alternative="greater"
    )

    agg_rows.append({
        "dimension": dimension,
        "mean": np.mean(values),
        "std": np.std(values, ddof=1),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "n_observations": len(values),
        "t_statistic": t_stat,
        "p_value": p_val
    })

df_aggregated_stats = pd.DataFrame(agg_rows)
df_aggregated_stats.to_csv(AGGREGATED_STATS_FILE, index=False)

print(f"Aggregated LLM-level stats written to: {AGGREGATED_STATS_FILE}")
