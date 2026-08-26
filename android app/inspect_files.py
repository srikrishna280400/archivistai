import pandas as pd
import os

def inspect():
    files = ["pocket_articles.xlsx", "instapaper_export.xlsx"]
    for file in files:
        if os.path.exists(file):
            print(f"=== {file} ===")
            df = pd.read_excel(file)
            print("Shape:", df.shape)
            print("Columns:", list(df.columns))
            print("First 3 rows:")
            print(df.head(3))
            print("\n")
        else:
            print(f"File {file} not found!")

if __name__ == "__main__":
    inspect()
