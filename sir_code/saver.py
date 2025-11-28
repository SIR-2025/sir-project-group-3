from pathlib import Path
from typing import Optional

import pandas as pd

CSV_FILE_PATH = Path(__file__).parent / 'static'
assert CSV_FILE_PATH.exists(), f"Dir '{CSV_FILE_PATH}' does not exist"

class Saver:
    def __init__(self, csv_name: str):
        self.csv_name = csv_name
        self.df = pd.DataFrame(columns=["user_text", "nao_text", "user_friendliness_score", "nao_respond_time"])

    def update(self, user_text: str, nao_text: str,
             user_friendliness_score: Optional[str] = None, nao_respond_time: Optional[float] = None):
        self.df.loc[len(self.df)] = [user_text, nao_text,
                                     user_friendliness_score, nao_respond_time]

    def save(self):
        self.df.to_csv(CSV_FILE_PATH / self.csv_name, index=False)

