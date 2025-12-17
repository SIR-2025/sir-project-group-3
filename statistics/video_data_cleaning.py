import pandas as pd

# -------------------------
# Paths
# -------------------------
BASE_DIR = "gform_csvs/"
RAW_DIR = BASE_DIR + "raw_data/"
PROCESSED_DIR = BASE_DIR + "processed_data/"

INPUT_FILE = RAW_DIR + "voice_gesture_eval.csv"
OUTPUT_FILE = PROCESSED_DIR + "voice_gesture_eval_clean.csv"

# -------------------------
# 1. Load raw CSV as-is
# -------------------------
df_raw = pd.read_csv(INPUT_FILE)

# Preserve original column order explicitly
df_raw = df_raw.copy()

# -------------------------
# 2. Create participant identifier
# Assign participant numbers
df_raw["participant"] = range(1, len(df_raw) + 1)
# df_raw["participant"] = df_raw.iloc[:, 0]


# -------------------------
# 3. Ignore column names temporarily
#    Treat columns 2..N as a sequence
# -------------------------
response_columns = df_raw.columns[1:-1]  # exclude timestamp and participant

# -------------------------
# 4. Build long-format rows
# -------------------------
long_rows = []

for _, row in df_raw.iterrows():
    participant = row["participant"]

    for idx, col in enumerate(response_columns):
        # Determine repetition and question type
        repetition = (idx // 2) + 1
        question = "voice" if idx % 2 == 0 else "gesture"

        long_rows.append({
            "participant": participant,
            "repetition": repetition,
            "question": question,
            "score": row[col]
        })

# -------------------------
# 5. Create long DataFrame
# -------------------------
df_long = pd.DataFrame(long_rows)

# -------------------------
# 6. Clean further
# -------------------------
# Convert scores to numeric
df_long["score"] = pd.to_numeric(df_long["score"], errors="coerce")

# Optional: drop missing responses
# df_long = df_long.dropna(subset=["score"])

# Ensure clean dtypes
df_long["repetition"] = df_long["repetition"].astype(int)
df_long["question"] = df_long["question"].astype("category")

# -------------------------
# 7. Save canonical clean dataset
# -------------------------
df_long.to_csv(OUTPUT_FILE, index=False)

print(f"Clean dataset written to: {OUTPUT_FILE}")
print(f"Rows: {len(df_long)}")
print(df_long.head())
