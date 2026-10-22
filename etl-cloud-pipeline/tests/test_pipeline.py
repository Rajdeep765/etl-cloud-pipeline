"""Comprehensive Unit Test Suite for ETL Pipeline Components.

Tests module functionalities including:
- Ingestion & file extraction (extractor.py)
- Data transformation, snake_case formatting, missing value handling, USD calculations, and edge cases (transformer.py)
- Relational SQLite persistence, truncate-append, and upsert modes (loader.py)
- Azure SQL configuration validation (azure_sql_reader.py)
- Azure Blob Storage loader configuration validation (azure_loader.py)
- Visual analytics and HTML report generation (viz.py)
- Emailer credential validation (emailer.py)
"""

import os
import sqlite3
import pandas as pd
import pytest

from etl.extractor import extract
from etl.transformer import transform, to_snake_case
from etl.loader import load
from etl.azure_sql_reader import read_from_azure_sql
from etl.azure_loader import upload_to_azure
from etl.viz import create_report
from etl.emailer import send_report_email


# -----------------------------------------------------------------------------
# Extractor Tests
# -----------------------------------------------------------------------------

def test_dummy_data_exists():
    """Verify that sample input CSV exists and contains expected columns."""
    csv_path = os.path.join("data", "dummy_data.csv")
    assert os.path.exists(csv_path), f"Sample data file missing at {csv_path}"

    df = extract(csv_path)
    expected_columns = {"transaction_id", "date", "customer_name", "amount", "currency", "region"}
    assert set(df.columns) == expected_columns
    assert len(df) >= 40


def test_extract_file_not_found():
    """Verify that extract raises FileNotFoundError for non-existent path."""
    with pytest.raises(FileNotFoundError):
        extract("non_existent_file.csv")


def test_extract_empty_file(tmp_path):
    """Verify that extract raises ValueError when reading an empty CSV file."""
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("")
    with pytest.raises(ValueError):
        extract(str(empty_file))


# -----------------------------------------------------------------------------
# Transformer Tests & Edge Cases
# -----------------------------------------------------------------------------

def test_transformer_to_snake_case():
    """Verify to_snake_case formatting utility handles spaces, symbols, and camelCase."""
    assert to_snake_case("Transaction ID") == "transaction_id"
    assert to_snake_case("Customer Name ($)") == "customer_name"
    assert to_snake_case("CreatedDate") == "created_date"
    assert to_snake_case("  Amount_USD  ") == "amount_usd"


def test_transformer_full_flow():
    """Verify transform function normalizes headers, handles nulls, and calculates amount_usd."""
    raw_data = {
        "Transaction ID": ["TXN101", "TXN102", "TXN102", "TXN103"],
        "Date": ["2026-01-01", "invalid_date", "invalid_date", None],
        "Customer Name": ["Alice", "Bob", "Bob", None],
        "Amount": [100.0, None, None, 250.5],
    }
    df = pd.DataFrame(raw_data)
    cleaned = transform(df, exchange_rate=1.1)

    assert "transaction_id" in cleaned.columns
    assert "customer_name" in cleaned.columns
    assert "amount_usd" in cleaned.columns

    # Check deduplication (rows index 1 and 2 were identical duplicates)
    assert len(cleaned) == 3

    # Check missing value handling (text -> 'unknown', numeric -> 0)
    assert (cleaned["customer_name"] == "unknown").any()
    assert (cleaned["amount"] == 0).any()

    # Check amount_usd calculation (100.0 * 1.1 = 110.0)
    assert cleaned.loc[cleaned["transaction_id"] == "TXN101", "amount_usd"].iloc[0] == 110.0


def test_transformer_empty_dataframe_edge_case():
    """Verify transform raises ValueError when passed an empty DataFrame."""
    empty_df = pd.DataFrame()
    with pytest.raises(ValueError, match="empty or None"):
        transform(empty_df)


def test_transformer_missing_amount_column_edge_case():
    """Verify transform processes DataFrames cleanly when 'amount' column is missing."""
    raw_df = pd.DataFrame({
        "Transaction ID": ["TXN101", "TXN102"],
        "Customer Name": ["Alice", "Bob"],
        "Region": ["North America", "Europe"]
    })
    cleaned = transform(raw_df)
    assert "transaction_id" in cleaned.columns
    assert "customer_name" in cleaned.columns
    assert "amount_usd" not in cleaned.columns
    assert len(cleaned) == 2


def test_transformer_missing_date_column_edge_case():
    """Verify transform processes DataFrames cleanly when no date-like column is present."""
    raw_df = pd.DataFrame({
        "Transaction ID": ["TXN101", "TXN102"],
        "Amount": [150.0, 200.0]
    })
    cleaned = transform(raw_df)
    assert "amount_usd" in cleaned.columns
    assert len(cleaned) == 2


def test_transformer_duplicate_rows_edge_case():
    """Verify transform drops fully duplicate rows."""
    raw_df = pd.DataFrame({
        "Transaction ID": ["TXN101", "TXN101", "TXN102"],
        "Amount": [100.0, 100.0, 200.0],
        "Customer Name": ["Alice", "Alice", "Bob"]
    })
    cleaned = transform(raw_df)
    assert len(cleaned) == 2


# -----------------------------------------------------------------------------
# Loader Tests (Using tmp_path Fixture)
# -----------------------------------------------------------------------------

def test_loader_append_mode(tmp_path):
    """Verify load function in mode='append' (truncate-append) using SQLite temporary database."""
    db_file = str(tmp_path / "test_etl.db")
    df1 = pd.DataFrame({
        "transaction_id": ["TXN1", "TXN2"],
        "amount_usd": [100.0, 200.0]
    })

    # Initial load
    load(df1, table_name="data_table", db_path=db_file, mode="append")

    conn = sqlite3.connect(db_file)
    res = pd.read_sql("SELECT * FROM data_table", conn)
    assert len(res) == 2

    # Truncate-append re-run
    load(df1, table_name="data_table", db_path=db_file, mode="append")
    res_after = pd.read_sql("SELECT * FROM data_table", conn)
    conn.close()

    assert len(res_after) == 2


def test_loader_upsert_mode(tmp_path):
    """Verify load function in mode='upsert' (delta update based on primary key)."""
    db_file = str(tmp_path / "test_etl.db")
    df1 = pd.DataFrame({
        "transaction_id": ["TXN1", "TXN2"],
        "amount_usd": [100.0, 200.0]
    })
    load(df1, table_name="data_table", db_path=db_file, mode="append")

    # Upsert with updated TXN2 value and new TXN3 record
    df2 = pd.DataFrame({
        "transaction_id": ["TXN2", "TXN3"],
        "amount_usd": [250.0, 300.0]
    })
    load(df2, table_name="data_table", db_path=db_file, mode="upsert")

    conn = sqlite3.connect(db_file)
    res = pd.read_sql("SELECT * FROM data_table", conn)
    conn.close()

    assert len(res) == 3
    assert res.loc[res["transaction_id"] == "TXN2", "amount_usd"].iloc[0] == 250.0


def test_loader_empty_dataframe_edge_case(tmp_path):
    """Verify loader raises ValueError when trying to load an empty DataFrame."""
    db_file = str(tmp_path / "test_etl.db")
    empty_df = pd.DataFrame()
    with pytest.raises(ValueError, match="empty or None"):
        load(empty_df, table_name="data_table", db_path=db_file)


def test_loader_unsupported_mode_edge_case(tmp_path):
    """Verify loader raises ValueError when given an invalid mode."""
    db_file = str(tmp_path / "test_etl.db")
    df = pd.DataFrame({"col": [1, 2]})
    with pytest.raises(ValueError, match="Unsupported load mode"):
        load(df, table_name="data_table", db_path=db_file, mode="invalid_mode")


# -----------------------------------------------------------------------------
# Azure SQL & Blob Reader Configuration Tests
# -----------------------------------------------------------------------------

def test_azure_sql_reader_missing_env_vars(monkeypatch):
    """Verify read_from_azure_sql raises ValueError when env vars are missing."""
    import etl.azure_sql_reader
    # Prevent load_dotenv() from reading local .env file during test isolation
    monkeypatch.setattr("etl.azure_sql_reader.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("AZURE_SQL_SERVER", raising=False)
    monkeypatch.delenv("AZURE_SQL_DATABASE", raising=False)
    monkeypatch.delenv("AZURE_SQL_USERNAME", raising=False)
    monkeypatch.delenv("AZURE_SQL_USER", raising=False)
    monkeypatch.delenv("AZURE_SQL_PASSWORD", raising=False)
    with pytest.raises(ValueError, match="Missing required Azure SQL environment variables"):
        etl.azure_sql_reader.read_from_azure_sql()


def test_azure_loader_missing_conn_string(monkeypatch):
    """Verify upload_to_azure raises ValueError when connection string is missing."""
    import etl.azure_loader
    # Prevent load_dotenv() from reading local .env file during test isolation
    monkeypatch.setattr("etl.azure_loader.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("AZURE_STORAGE_CONNECTION_STRING", raising=False)
    df = pd.DataFrame({"col": [1, 2]})
    with pytest.raises(ValueError, match="AZURE_STORAGE_CONNECTION_STRING environment variable is missing"):
        etl.azure_loader.upload_to_azure(df, "test-container", "test-blob.csv")



# -----------------------------------------------------------------------------
# Reporting & Emailer Tests
# -----------------------------------------------------------------------------

def test_create_report(tmp_path):
    """Verify create_report generates HTML report file and PNG charts."""
    out_dir = str(tmp_path / "reports")
    df = pd.DataFrame({
        "transaction_id": ["TX1", "TX2", "TX3"],
        "amount_usd": [100.5, 250.0, 50.0],
        "region": ["North America", "Europe", "North America"]
    })

    report_file = create_report(df, output_dir=out_dir)
    assert os.path.exists(report_file)
    assert report_file.endswith(".html")

    with open(report_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "ETL Pipeline Automated Summary Report" in content
    assert "Amount Distribution" in content
    assert "Regional Breakdown" in content


def test_emailer_missing_credentials(monkeypatch):
    """Verify send_report_email returns False gracefully when credentials are missing."""
    import etl.emailer
    # Prevent load_dotenv() from reading local .env file during test isolation
    monkeypatch.setattr("etl.emailer.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    res = etl.emailer.send_report_email("dummy.html", "user@example.com")
    assert res is False

