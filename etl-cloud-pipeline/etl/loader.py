"""Local Relational Database Loader Module.

Establishes SQLite operational connections to store persistent structural outputs locally.
"""

import logging
import os
import sqlite3
from typing import Optional
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Loader")


def load(df: pd.DataFrame, table_name: str, db_path: str, mode: str = "append") -> None:
    """Persist transformed DataFrame records into a local SQLite database table.

    Supports two operation modes:
    - 'append' (Truncate-Append): Clears existing table rows if table exists, then inserts DataFrame records.
    - 'upsert' (Safe Delta Update): Updates/replaces matching records based on primary key column
      (e.g., 'transaction_id'), and inserts new records without overwriting non-matching existing data.

    Args:
        df (pd.DataFrame): Transformed DataFrame containing records to persist.
        table_name (str): Name of target table inside SQLite database.
        db_path (str): Local filesystem path to target SQLite database file (.db).
        mode (str): Load mode strategy ('append' or 'upsert'). Defaults to 'append'.

    Raises:
        ValueError: If df is empty/None or if mode is unsupported.
        RuntimeError: If SQLite operational or connection error occurs.
    """
    if df is None or df.empty:
        err_msg = "Input DataFrame for loading is empty or None."
        logger.error(err_msg)
        raise ValueError(err_msg)

    if mode not in ("append", "upsert"):
        err_msg = f"Unsupported load mode '{mode}'. Supported modes are 'append' and 'upsert'."
        logger.error(err_msg)
        raise ValueError(err_msg)

    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created parent directory for database path: '{db_dir}'")

    conn: Optional[sqlite3.Connection] = None
    try:
        logger.info(f"Connecting to SQLite database at '{db_path}'...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table already exists in SQLite
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
            (table_name,)
        )
        table_exists = cursor.fetchone() is not None

        if mode == "append":
            # Truncate-Append: If table exists, delete existing rows before inserting
            if table_exists:
                logger.info(f"Mode 'append' (Truncate-Append): Clearing existing rows from table '{table_name}'...")
                cursor.execute(f"DELETE FROM {table_name}")
                conn.commit()

            df.to_sql(table_name, conn, if_exists="append", index=False)
            logger.info(f"Successfully loaded {len(df)} rows into SQLite table '{table_name}' (mode='append').")

        elif mode == "upsert":
            if not table_exists:
                logger.info(f"Mode 'upsert': Table '{table_name}' does not exist. Creating new table...")
                df.to_sql(table_name, conn, if_exists="replace", index=False)
            else:
                # Identify primary key column
                pk_col = None
                if "transaction_id" in df.columns:
                    pk_col = "transaction_id"
                else:
                    id_cols = [c for c in df.columns if c.endswith("_id") or c == "id"]
                    if id_cols:
                        pk_col = id_cols[0]

                if pk_col:
                    logger.info(f"Mode 'upsert': Performing delta update using primary key column '{pk_col}'...")
                    pk_values = df[pk_col].dropna().astype(str).tolist()
                    if pk_values:
                        placeholders = ",".join(["?"] * len(pk_values))
                        cursor.execute(f"DELETE FROM {table_name} WHERE {pk_col} IN ({placeholders})", pk_values)
                        conn.commit()
                        logger.info(f"Deleted existing matching records for primary key '{pk_col}'.")

                df.to_sql(table_name, conn, if_exists="append", index=False)
            logger.info(f"Successfully upserted {len(df)} rows into SQLite table '{table_name}' (mode='upsert').")

    except sqlite3.Error as sql_err:
        err_msg = f"SQLite database operational error: {sql_err}"
        logger.error(err_msg)
        raise RuntimeError(err_msg) from sql_err
    except Exception as err:
        err_msg = f"Unexpected error loading data into SQLite database '{db_path}': {err}"
        logger.error(err_msg)
        raise RuntimeError(err_msg) from err
    finally:
        if conn:
            try:
                conn.close()
                logger.info("SQLite database connection safely closed.")
            except Exception as close_err:
                logger.warning(f"Error while closing SQLite database connection: {close_err}")


def load_to_sqlite(df: pd.DataFrame, table_name: str, db_path: str, mode: str = "append") -> None:
    """Alias for load() to support component interface compatibility."""
    load(df=df, table_name=table_name, db_path=db_path, mode=mode)

