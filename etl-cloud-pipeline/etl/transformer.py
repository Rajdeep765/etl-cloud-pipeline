"""Data Transformer Module.

Executes standard operational data cleaning logic:
- Normalizes column names into lower snake_case format.
- Validates schema, drops duplicates, and handles missing data fields.
- Parses string dates into explicit ISO datetime signatures.
- Computes uniform normalized monetary valuations (e.g. amount_usd = amount * exchange_rate).
"""

import logging
import re
from typing import Dict, List, Optional
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Transformer")

# Standard currency exchange rates to USD for normalization fallback
EXCHANGE_RATES: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "CAD": 0.74,
    "JPY": 0.0067,
}


def to_snake_case(col_name: str) -> str:
    """Convert an arbitrary column name string to clean snake_case format.

    Args:
        col_name (str): Original column header string.

    Returns:
        str: Normalized snake_case column header.
    """
    s = str(col_name).strip()
    s = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', s)
    s = re.sub(r'[^a-zA-Z0-9]+', '_', s)
    s = s.lower().strip('_')
    return s


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataFrame column headers to lowercase snake_case format.

    Args:
        df (pd.DataFrame): Input raw DataFrame.

    Returns:
        pd.DataFrame: DataFrame with normalized column headers.
    """
    df_copy = df.copy()
    renamed_cols = {col: to_snake_case(col) for col in df_copy.columns}
    df_copy = df_copy.rename(columns=renamed_cols)
    logger.info(f"Normalized column headers to snake_case: {list(df_copy.columns)}")
    return df_copy


def transform(df: pd.DataFrame, exchange_rate: float = 1.0) -> pd.DataFrame:
    """Execute complete data transformation pipeline sequence on raw DataFrame.

    Requirements implemented:
    1. Normalize column names to snake_case.
    2. Detect and cast date-like columns to datetime, coercing errors to NaT and logging warnings.
    3. Drop fully-duplicate rows.
    4. Handle missing values (numeric filled with 0, text filled with 'unknown').
    5. Compute derived column `amount_usd = amount * exchange_rate` if 'amount' column exists.

    Args:
        df (pd.DataFrame): Ingested raw DataFrame.
        exchange_rate (float): Currency conversion rate multiplier for USD calculation. Defaults to 1.0.

    Returns:
        pd.DataFrame: Fully cleaned and transformed DataFrame.

    Raises:
        ValueError: If input DataFrame is None or empty.
        RuntimeError: If transformation phase fails.
    """
    if df is None or df.empty:
        err_msg = "Input DataFrame for transformation is empty or None."
        logger.error(err_msg)
        raise ValueError(err_msg)

    try:
        logger.info("Starting data transformation sequence...")
        cleaned_df = df.copy()

        # 1. Normalize all column names to snake_case
        cleaned_df = normalize_column_names(cleaned_df)

        # 2. Detect and cast date-like text columns into proper datetime
        for col in cleaned_df.columns:
            if "date" in col or "time" in col or "timestamp" in col:
                if not pd.api.types.is_datetime64_any_dtype(cleaned_df[col]):
                    initial_nulls = cleaned_df[col].isnull().sum()
                    converted_dates = pd.to_datetime(cleaned_df[col], errors="coerce")
                    final_nulls = converted_dates.isnull().sum()
                    failed_rows = final_nulls - initial_nulls

                    if failed_rows > 0:
                        logger.warning(f"Date parsing in column '{col}' produced {failed_rows} NaT parsing failures.")

                    cleaned_df[col] = converted_dates
                    logger.info(f"Cast column '{col}' to datetime64 dtype.")

        # 3. Drop fully-duplicate rows
        initial_count = len(cleaned_df)
        cleaned_df = cleaned_df.drop_duplicates()
        duplicates_removed = initial_count - len(cleaned_df)
        if duplicates_removed > 0:
            logger.info(f"Dropped {duplicates_removed} fully-duplicate rows.")

        # 4. Handle missing values: numeric -> 0, text -> "unknown"
        numeric_cols = cleaned_df.select_dtypes(include=["number"]).columns
        for num_col in numeric_cols:
            missing_count = cleaned_df[num_col].isnull().sum()
            if missing_count > 0:
                logger.info(f"Filling {missing_count} missing values in numeric column '{num_col}' with 0")
                cleaned_df[num_col] = cleaned_df[num_col].fillna(0)

        object_cols = cleaned_df.select_dtypes(include=["object", "string"]).columns
        for txt_col in object_cols:
            missing_count = cleaned_df[txt_col].isnull().sum()
            if missing_count > 0:
                logger.info(f"Filling {missing_count} missing values in text column '{txt_col}' with 'unknown'")
                cleaned_df[txt_col] = cleaned_df[txt_col].fillna("unknown")

        # 5. Compute amount_usd = amount * exchange_rate if 'amount' column exists
        if "amount" in cleaned_df.columns:
            cleaned_df["amount"] = pd.to_numeric(cleaned_df["amount"], errors="coerce").fillna(0)
            cleaned_df["amount_usd"] = (cleaned_df["amount"] * exchange_rate).round(2)
            logger.info(f"Computed derived 'amount_usd' column using exchange_rate = {exchange_rate}.")

        logger.info(f"Data transformation sequence successfully completed. Final shape: {cleaned_df.shape}")
        return cleaned_df

    except Exception as err:
        err_msg = f"Unexpected error during data transformation: {err}"
        logger.error(err_msg)
        raise RuntimeError(err_msg) from err

