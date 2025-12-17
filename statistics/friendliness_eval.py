import pandas as pd
import numpy as np

# -------------------------
# Paths
# -------------------------
BASE_DIR = "gform_csvs/"
PROCESSED_DIR = BASE_DIR + "processed_data/"
INPUT_FILE = PROCESSED_DIR + "chat_eval_clean.csv"

TURN_OUT = PROCESSED_DIR + "friendliness_turn_scores.csv"
CHAT_OUT = PROCESSED_DIR + "friendliness_chat_scores.csv"
OVERALL_OUT = PROCESSED_DIR + "friendliness_overall_summary.csv"
LABEL_OUT = PROCESSED_DIR + "friendliness_label_summary.csv"


# -------------------------
# Helpers
# -------------------------
def letters_to_set(s) -> set[str]:
    """Convert 'BCGH' -> {'B','C','G','H'}. Empty/NaN -> empty set."""
    if pd.isna(s):
        return set()
    s = str(s).strip()
    if not s:
        return set()
    return set(list(s))


def soft_jaccard(p_dict: dict[str, float], pred_set: set[str], label_universe: list[str]) -> float:
    """
    Soft Jaccard between a soft distribution p(l) (humans) and a hard set y(l) (LLM or a human).
    y(l) = 1 if l in pred_set else 0.

    numerator = sum_l min(p(l), y(l)) = sum_{l in pred_set} p(l)
    denom     = sum_l max(p(l), y(l)) = sum_{l in pred_set} 1 + sum_{l not in pred_set} p(l)
    """
    num = 0.0
    denom = 0.0
    for lab in label_universe:
        p = float(p_dict.get(lab, 0.0))
        y = 1.0 if lab in pred_set else 0.0
        num += min(p, y)
        denom += max(p, y)
    if denom == 0.0:
        # No human signal (all p=0) and empty prediction -> treat as perfect match
        return np.nan
    return num / denom


# -------------------------
# Load and isolate friendliness
# -------------------------
df = pd.read_csv(INPUT_FILE)

required_cols = {"chat_id", "rater", "turn", "dimension", "value"}
missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df_f = df[df["dimension"] == "user_friendliness_score"].copy()
if df_f.empty:
    raise ValueError("No rows found for dimension == 'user_friendliness_score'")

# Split humans vs LLM
df_llm = df_f[df_f["rater"].astype(str) == "llm"].copy()
df_h = df_f[df_f["rater"].astype(str) != "llm"].copy()

# Parse to sets
df_llm["label_set"] = df_llm["value"].apply(letters_to_set)
df_h["label_set"] = df_h["value"].apply(letters_to_set)

# Determine label universe (A–J or whatever actually appears)
label_universe = sorted(set().union(*df_h["label_set"].tolist(), *df_llm["label_set"].tolist()))
if not label_universe:
    raise ValueError("Label universe is empty — do your friendliness values contain letters?")

# -------------------------
# Build turn-level human distributions + compute Soft Jaccard for LLM
# -------------------------
turn_rows = []
dropped_missing_llm = 0
dropped_no_humans = 0

# Group humans by (chat, turn)
for (chat_id, turn), g_h in df_h.groupby(["chat_id", "turn"]):
    # Human distribution p(l) = (#humans selecting l) / (n_humans)
    n_humans = len(g_h)
    if n_humans == 0:
        dropped_no_humans += 1
        continue

    counts = {lab: 0 for lab in label_universe}
    for s in g_h["label_set"]:
        for lab in s:
            if lab in counts:
                counts[lab] += 1

    p = {lab: counts[lab] / n_humans for lab in label_universe}

    # LLM prediction for this (chat, turn)
    g_llm = df_llm[(df_llm["chat_id"] == chat_id) & (df_llm["turn"] == turn)]
    if g_llm.empty:
        dropped_missing_llm += 1
        continue
    if len(g_llm) > 1:
        raise ValueError(f"Multiple LLM rows found for chat_id={chat_id}, turn={turn}")

    llm_set = g_llm.iloc[0]["label_set"]

    sj_llm = soft_jaccard(p, llm_set, label_universe)

    # Human-vs-human baseline: leave-one-out soft jaccard per human rater
    # (each human compared to distribution of the other humans)
    baseline_scores = []
    if n_humans >= 2:
        human_sets = g_h["label_set"].tolist()
        for i, s_i in enumerate(human_sets):
            other_sets = [s for j, s in enumerate(human_sets) if j != i]
            n_other = len(other_sets)
            other_counts = {lab: 0 for lab in label_universe}
            for s in other_sets:
                for lab in s:
                    if lab in other_counts:
                        other_counts[lab] += 1
            p_other = {lab: other_counts[lab] / n_other for lab in label_universe}
            baseline_scores.append(soft_jaccard(p_other, s_i, label_universe))

    sj_human_baseline_mean = float(np.mean(baseline_scores)) if baseline_scores else np.nan

    turn_rows.append({
        "chat_id": chat_id,
        "turn": int(turn),
        "n_human_raters": int(n_humans),
        "soft_jaccard_llm": float(sj_llm),
        "soft_jaccard_human_baseline": sj_human_baseline_mean
    })

df_turn = pd.DataFrame(turn_rows).sort_values(["chat_id", "turn"])
n_nan = df_turn["soft_jaccard_llm"].isna().sum()
print(f"Number of turns with undefined Soft Jaccard (no human signal): {n_nan}")
df_turn.to_csv(TURN_OUT, index=False)

print(f"Wrote turn-level Soft Jaccard scores to: {TURN_OUT}")
if dropped_missing_llm:
    print(f"Warning: dropped {dropped_missing_llm} (chat,turn) because LLM row was missing.")
if dropped_no_humans:
    print(f"Warning: dropped {dropped_no_humans} (chat,turn) because no human rows were present.")

# -------------------------
# Aggregate: per-chat then overall
# -------------------------
df_chat = (
    df_turn.dropna(subset=["soft_jaccard_llm"])
    .groupby("chat_id", as_index=False)
    .agg(
        n_turns=("turn", "count"),
        mean_soft_jaccard_llm=("soft_jaccard_llm", "mean"),
        mean_soft_jaccard_human_baseline=("soft_jaccard_human_baseline", "mean"),
    )
)
df_chat.to_csv(CHAT_OUT, index=False)
print(f"Wrote chat-level averages to: {CHAT_OUT}")

overall = {
    "n_chats": int(df_chat["chat_id"].nunique()),
    "n_turns_total": int(df_turn.shape[0]),
    "overall_mean_soft_jaccard_llm": float(df_chat["mean_soft_jaccard_llm"].mean()),
    "overall_std_soft_jaccard_llm_across_chats": float(df_chat["mean_soft_jaccard_llm"].std(ddof=1)) if df_chat.shape[0] > 1 else np.nan,
    "overall_mean_soft_jaccard_human_baseline": float(df_chat["mean_soft_jaccard_human_baseline"].mean()),
    "overall_std_soft_jaccard_human_baseline_across_chats": float(df_chat["mean_soft_jaccard_human_baseline"].std(ddof=1)) if df_chat.shape[0] > 1 else np.nan,
}
df_overall = pd.DataFrame([overall])
df_overall.to_csv(OVERALL_OUT, index=False)
print(f"Wrote overall summary to: {OVERALL_OUT}")

# -------------------------
# Label-wise analysis (humans vs LLM + soft precision/recall-style)
# -------------------------
# Build per-(chat,turn) human probabilities p(l) and llm binary y(l),
# then aggregate expected TP/FP/FN over all turns.
label_rows = []
# Map (chat,turn) -> (p_dict, llm_set)
turn_map = {}

for _, r in df_turn.iterrows():
    turn_map[(r["chat_id"], int(r["turn"]))] = None  # placeholder

# Rebuild p and llm_set for each (chat,turn) that survived in df_turn
for (chat_id, turn), _ in turn_map.items():
    g_h = df_h[(df_h["chat_id"] == chat_id) & (df_h["turn"] == turn)]
    n_humans = len(g_h)
    counts = {lab: 0 for lab in label_universe}
    for s in g_h["label_set"]:
        for lab in s:
            if lab in counts:
                counts[lab] += 1
    p = {lab: counts[lab] / n_humans for lab in label_universe}

    g_llm = df_llm[(df_llm["chat_id"] == chat_id) & (df_llm["turn"] == turn)]
    llm_set = g_llm.iloc[0]["label_set"] if not g_llm.empty else set()

    turn_map[(chat_id, turn)] = (p, llm_set)

# Aggregate human label rates and llm label rates
n_turns_used = len(turn_map)

for lab in label_universe:
    # Human probability per turn is p(lab); average that over turns
    human_probs = []
    llm_preds = []

    # Soft expected counts:
    # TP = y * p
    # FP = y * (1 - p)
    # FN = (1 - y) * p
    tp = fp = fn = 0.0

    for (p, llm_set) in turn_map.values():
        p_lab = float(p.get(lab, 0.0))
        y = 1.0 if lab in llm_set else 0.0

        human_probs.append(p_lab)
        llm_preds.append(y)

        tp += y * p_lab
        fp += y * (1.0 - p_lab)
        fn += (1.0 - y) * p_lab

    human_rate = float(np.mean(human_probs)) if human_probs else np.nan  # mean human probability over turns
    llm_rate = float(np.mean(llm_preds)) if llm_preds else np.nan        # fraction of turns LLM predicts label

    # Soft precision/recall-style:
    # precision = TP / (TP + FP) == sum(y*p) / sum(y)
    # recall    = TP / (TP + FN) == sum(y*p) / sum(p)
    denom_prec = (tp + fp)
    denom_rec = (tp + fn)

    soft_precision = float(tp / denom_prec) if denom_prec > 0 else np.nan
    soft_recall = float(tp / denom_rec) if denom_rec > 0 else np.nan
    soft_f1 = float(2 * soft_precision * soft_recall / (soft_precision + soft_recall)) if (
        soft_precision is not np.nan and soft_recall is not np.nan and (soft_precision + soft_recall) > 0
    ) else np.nan

    label_rows.append({
        "label": lab,
        "human_rate_mean_probability": human_rate,
        "llm_rate_fraction_of_turns_predicted": llm_rate,
        "soft_precision": soft_precision,
        "soft_recall": soft_recall,
        "soft_f1": soft_f1,
        "tp_expected": tp,
        "fp_expected": fp,
        "fn_expected": fn,
        "n_turns": n_turns_used
    })

df_label = pd.DataFrame(label_rows).sort_values("label")
df_label.to_csv(LABEL_OUT, index=False)
print(f"Wrote label-wise analysis to: {LABEL_OUT}")

print("\nDone.")
print("Key outputs:")
print(f"- {TURN_OUT}")
print(f"- {CHAT_OUT}")
print(f"- {OVERALL_OUT}")
print(f"- {LABEL_OUT}")
