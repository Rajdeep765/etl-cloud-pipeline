"""Azure SQL Server Extractor Module.

Establishes encrypted ODBC channels to remote servers to stream enterprise data packages down to the pipeline.
"""

import logging
import os
from typing import Optional
import pandas as pd
import pyodbc
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AzureSQLReader")


class AzureSQLConnectionError(Exception):
    """Custom exception raised when connection or query execution to Azure SQL fails."""
    pass


def read_from_azure_sql(table_name: str = "transactions") -> pd.DataFrame:
    """Connect to Azure SQL Server via pyodbc and read a target table into a pandas DataFrame.

    Reads connection credentials and configuration from environment variables:
    - AZURE_SQL_SERVER
    - AZURE_SQL_DATABASE
    - AZURE_SQL_USERNAME (or AZURE_SQL_USER)
    - AZURE_SQL_PASSWORD
    - AZURE_SQL_DRIVER (defaults to '{ODBC Driver 18 for SQL Server}')

    Args:
        table_name (str): Target table name to select from. Defaults to 'transactions'.

    Returns:
        pd.DataFrame: Query result set ingested as a pandas DataFrame.

    Raises:
        ValueError: If required environment variables are missing.
        AzureSQLConnectionError: If pyodbc connection fails or driver error occurs.
        RuntimeError: For unexpected execution errors.
    """
    load_dotenv()

    server: Optional[str] = os.getenv("AZURE_SQL_SERVER")
    database: Optional[str] = os.getenv("AZURE_SQL_DATABASE")
    username: Optional[str] = os.getenv("AZURE_SQL_USERNAME") or os.getenv("AZURE_SQL_USER")
    password: Optional[str] = os.getenv("AZURE_SQL_PASSWORD")
    driver: str = os.getenv("AZURE_SQL_DRIVER", "{ODBC Driver 18 for SQL Server}")

    if driver and not driver.startswith("{"):
        driver = f"{{{driver}}}"

    missing_vars = []
    if not server:
        missing_vars.append("AZURE_SQL_SERVER")
    if not database:
        missing_vars.append("AZURE_SQL_DATABASE")
    if not username:
        missing_vars.append("AZURE_SQL_USERNAME/AZURE_SQL_USER")
    if not password:
        missing_vars.append("AZURE_SQL_PASSWORD")

    if missing_vars:
        err_msg = f"Missing required Azure SQL environment variables: {', '.join(missing_vars)}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    conn_str = (
        f"DRIVER={driver};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )

    query = f"SELECT * FROM {table_name}"
    conn = None

    try:
        logger.info(f"Connecting to Azure SQL Server '{server}', DB '{database}' using driver '{driver}'...")
        conn = pyodbc.connect(conn_str)
        logger.info(f"Executing query: '{query}'")
        df = pd.read_sql(query, conn)
        logger.info(f"Successfully retrieved {len(df)} rows from Azure SQL table '{table_name}'.")
        return df

    except pyodbc.Error as odbc_err:
        err_str = str(odbc_err)
        logger.error(f"pyodbc database error encountered: {err_str}")

        if "IM002" in err_str:
            suggestion = (
                f"Data source name not found or no default driver specified (IM002). "
                f"Please verify that '{driver}' is installed on your system or update the "
                "AZURE_SQL_DRIVER environment variable."
            )
        else:
            suggestion = f"Failed to connect or query Azure SQL Server: {err_str}"

        raise AzureSQLConnectionError(suggestion) from odbc_err

    except Exception as err:
        err_msg = f"Unexpected error while reading from Azure SQL: {err}"
        logger.error(err_msg)
        raise RuntimeError(err_msg) from err

    finally:
        if conn:
            try:
                conn.close()
                logger.info("Azure SQL pyodbc database connection safely closed.")
            except Exception as close_err:
                logger.warning(f"Error while closing pyodbc connection: {close_err}")


def extract_from_azure_sql(
    server: Optional[str] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    driver: str = "{ODBC Driver 18 for SQL Server}",
    query: str = "SELECT * FROM transactions"
) -> pd.DataFrame:
    """Wrapper function to support parameterized invocation for orchestration components.

    Args:
        server (Optional[str]): Azure SQL Server endpoint.
        database (Optional[str]): Database name.
        user (Optional[str]): Username.
        password (Optional[str]): Password.
        driver (str): ODBC driver string.
        query (str): SQL query string.

    Returns:
        pd.DataFrame: Result DataFrame.
    """
    if server:
        os.environ["AZURE_SQL_SERVER"] = server
    if database:
        os.environ["AZURE_SQL_DATABASE"] = database
    if user:
        os.environ["AZURE_SQL_USERNAME"] = user
    if password:
        os.environ["AZURE_SQL_PASSWORD"] = password
    if driver:
        os.environ["AZURE_SQL_DRIVER"] = driver

    table_name = "transactions"
    if " FROM " in query.upper():
        table_name = query.upper().split(" FROM ")[1].strip().split()[0]

    return read_from_azure_sql(table_name=table_name)

