"""Pipeline Verification Script (verify_db.py).

Interfaces with the local SQLite pipeline database to inspect stored tables,
verify schema, and validate record insertion.
"""

import logging
import os
import sqlite3
from typing import Optional
from dotenv import load_dotenv
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def verify_database(db_path: Optional[str] = None, table_name: str = "data_table", limit: int = 5) -> pd.DataFrame:
    """Connect to local SQLite tracking instance and display top N records.

    Args:
        db_path (Optional[str]): Path to SQLite DB file. Defaults to DB_PATH env var or 'data/etl.db'.
        table_name (str): Table name to query. Defaults to 'data_table'.
        limit (int): Number of sample records to inspect. Defaults to 5.

    Returns:
        pd.DataFrame: Sample query result set as pandas DataFrame.
    """
    load_dotenv()
    if db_path is None:
        db_path = os.getenv("DB_PATH", "data/etl.db")

    if not os.path.exists(db_path):
        logging.warning(f"Database file does not exist yet at '{db_path}'. Run run_etl.py first.")
        return pd.DataFrame()

    try:
        logging.info(f"Connecting to database at '{db_path}'...")
        connection = sqlite3.connect(db_path)
        query = f"SELECT * FROM {table_name} LIMIT {limit};"
        extracted_sample = pd.read_sql(query, connection)

        print("\n--- PIPELINE VERIFICATION RUN RESULT ---")
        print(extracted_sample)
        print("----------------------------------------\n")

        connection.close()
        return extracted_sample
    except sqlite3.Error as sql_err:
        logging.error(f"Failed to query database '{db_path}': {sql_err}")
        raise RuntimeError(f"Database verification query failed: {sql_err}") from sql_err
    except Exception as err:
        logging.error(f"Unexpected error during DB verification: {err}")
        raise RuntimeError(f"DB verification failed: {err}") from err


if __name__ == "__main__":
    verify_database()
