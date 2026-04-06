import pandas as pd
import sys

try:
    df = pd.read_excel('employee_work_shift.xlsx')
    print("--- HEAD ---")
    print(df.head())
    print("\n--- COLUMNS ---")
    print(df.columns.tolist())
    print("\n--- INFO ---")
    print(df.info())
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
