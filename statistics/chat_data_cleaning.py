import pandas as pd
import os

# -------------------------
# Paths
# -------------------------
BASE_DIR = "gform_csvs/"
RAW_DIR = BASE_DIR + "raw_data/"
PROCESSED_DIR = BASE_DIR + "processed_data/"

OUTPUT_FILE = PROCESSED_DIR + "chat_eval_clean.csv"


def extract_friendliness_letters(value):
    if pd.isna(value) or value == "":
        return ""

    # Split on semicolons, take the letter before the colon
    letters = []
    for part in str(value).split(";"):
        part = part.strip()
        if ":" in part:
            letters.append(part.split(":", 1)[0])

    return "".join(letters)


# -------------------------
# Collect files
# -------------------------
chat_files = [
    f for f in os.listdir(RAW_DIR)
    if f.startswith("chat_eval_") and f.endswith(".csv")
]

llm_files = [
    f for f in os.listdir(RAW_DIR)
    if f.startswith("llm_eval_") and f.endswith(".csv")
]

all_long_rows = []

# -------------------------
# Process each chat file
# -------------------------
for filename in chat_files:
    chat_id = filename.replace("chat_eval_", "").replace(".csv", "")
    llm_filename = f"llm_eval_{chat_id}.csv"
    llm_path = RAW_DIR + llm_filename

    df_llm = None
    if os.path.exists(llm_path):
        df_llm = pd.read_csv(llm_path)

    filepath = RAW_DIR + filename

    # Load raw CSV as-is
    df_raw = pd.read_csv(filepath)
    df_raw = df_raw.copy()

    # Assign rater (participant) IDs
    df_raw["rater"] = range(1, len(df_raw) + 1)
    # df_raw["rater"] = df_raw.iloc[:, 0]

    # Response columns: exclude timestamp (first) and participant (last)
    response_columns = df_raw.columns[1:-1]

    # Build long-format rows
    for _, row in df_raw.iterrows():
        rater = row["rater"]

        for idx, col in enumerate(response_columns):
            turn = (idx // 3) + 1

            if idx % 3 == 0:
                dimension = "nao_relevance_current"
            elif idx % 3 == 1:
                dimension = "nao_relevance_history"
            else:
                dimension = "user_friendliness_score"

            all_long_rows.append({
                "chat_id": chat_id,
                "rater": rater,
                "turn": turn,
                "dimension": dimension,
                "value": extract_friendliness_letters(row[col]) if dimension == "user_friendliness_score" else row[col]
            })
    # -------------------------
    # Add LLM friendliness scores
    # -------------------------
    if df_llm is not None:
        for turn_idx, llm_row in df_llm.iloc[1:].reset_index(drop=True).iterrows():
            all_long_rows.append({
                "chat_id": chat_id,
                "rater": "llm",
                "turn": turn_idx + 1,
                "dimension": "user_friendliness_score",
                "value": llm_row["user_friendliness_score"]
            })


# -------------------------
# Create long DataFrame
# -------------------------
df_long = pd.DataFrame(all_long_rows)

# -------------------------
# Minimal cleaning
# -------------------------
# Convert NAO relevance scores to numeric
mask_numeric = df_long["dimension"].isin([
    "nao_relevance_current",
    "nao_relevance_history"
])

df_long.loc[mask_numeric, "value"] = pd.to_numeric(
    df_long.loc[mask_numeric, "value"],
    errors="coerce"
)

# Ensure clean dtypes
df_long["turn"] = df_long["turn"].astype(int)
df_long["dimension"] = df_long["dimension"].astype("category")

# -------------------------
# Save canonical dataset
# -------------------------
df_long.to_csv(OUTPUT_FILE, index=False)

print(f"Clean dataset written to: {OUTPUT_FILE}")
print(f"Rows: {len(df_long)}")
print(df_long.head())
