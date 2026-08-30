import os
import pandas as pd
from app.database.postgres import engine, Base

def init_db_and_load_csvs():
    Base.metadata.create_all(bind=engine)
    print("[+] SQL Tables verified/created.")

    files = {
        "handles": "data/handles.csv",
        "wallets": "data/wallets.csv",
        "marketplaces": "data/marketplaces.csv"
    }

    for table_name, file_path in files.items():
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                df.to_sql(table_name, con=engine, if_exists="replace", index=False)
                print(f"[+] Loaded {len(df)} records into '{table_name}' from {file_path}")
            except Exception as e:
                print(f"[-] Error loading {file_path}: {e}")
        else:
            print(f"[*] Notice: {file_path} not found in data/ folder. Skipping auto-load.")