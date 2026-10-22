"""Data Extractor Module.

Handles ingestion of localized physical system files (CSV) into pandas DataFrames.
"""

import logging
import os
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Extractor")


def extract(csv_path: str) -> pd.DataFrame:
    """Extract raw transaction data from a CSV file into a pandas DataFrame.

    Args:
        csv_path (str): Relative or absolute path to the input CSV file.

    Returns:
        pd.DataFrame: Tabular transaction data ingested as a pandas DataFrame.

    Raises:
        FileNotFoundError: If the input CSV file path does not exist.
        ValueError: If the input CSV file is empty or contains no data.
        RuntimeError: If pandas encounters an unexpected error during CSV parsing.
    """
    if not os.path.exists(csv_path):
        err_msg = f"Target CSV file path does not exist: '{csv_path}'"
        logger.error(err_msg)
        raise FileNotFoundError(err_msg)

    if os.path.getsize(csv_path) == 0:
        err_msg = f"Target CSV file is empty (0 bytes): '{csv_path}'"
        logger.error(err_msg)
        raise ValueError(err_msg)

    try:
        logger.info(f"Ingesting CSV data from source path: '{csv_path}'")
        df = pd.read_csv(csv_path)

        if df.empty:
            err_msg = f"Ingested DataFrame is empty (no data rows): '{csv_path}'"
            logger.error(err_msg)
            raise ValueError(err_msg)

        logger.info(f"Successfully extracted {len(df)} rows and {len(df.columns)} columns from '{csv_path}'")
        return df

    except FileNotFoundError:
        raise
    except ValueError:
        raise
    except pd.errors.EmptyDataError as empty_err:
        err_msg = f"CSV file contains no readable tabular data: '{csv_path}'"
        logger.error(err_msg)
        raise ValueError(err_msg) from empty_err
    except Exception as err:
        err_msg = f"Unexpected error reading CSV file '{csv_path}': {err}"
        logger.error(err_msg)
        raise RuntimeError(err_msg) from err


def extract_csv(csv_path: str) -> pd.DataFrame:
    """Alias for extract() to support component interface compatibility.

    Args:
        csv_path (str): Path to CSV file.

    Returns:
        pd.DataFrame: Extracted pandas DataFrame.
    """
    return extract(csv_path)


if __name__ == "__main__":
    test_path = os.path.join("data", "dummy_data.csv")
    print(f"--- Standalone Extractor Test: '{test_path}' ---")
    try:
        extracted_df = extract(test_path)
        print(f"Success! Shape: {extracted_df.shape}")
        print("\nHead sample:")
        print(extracted_df.head())
    except Exception as e:
        print(f"Extractor Test Failed: {e}")

