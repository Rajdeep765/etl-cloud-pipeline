# ETL Pipeline with Cloud Integration & Automated Reporting
## Comprehensive Capstone Project Implementation & Student Learning Guide
*DATA ENGINEERING FRAMEWORK • ACADEMIC VERSION 1.0 • MAY 2026*

---

## 1. Project Overview & System Architecture

This capstone project guides you through constructing a robust, industrial-grade **Extract-Transform-Load (ETL) pipeline**. In modern data systems, raw info resides across varying physical environments—ranging from locally maintained spreadsheets to cloud-hosted transactional environments. This project simulates a live data architecture scenario where data must be consolidated, transformed, persisted securely, visually reported, and automatically distributed via corporate messaging infrastructure.

### 1.1 High-Level Architecture Diagram

```text
+-----------------------------------------------------------------------------------+
|                                 INPUT DATA SOURCES                                |
|   +------------------------------------+    +---------------------------------+   |
|   | Local File System (data/*.csv)     |    | Azure SQL Server (pyodbc)       |   |
|   +------------------------------------+    +---------------------------------+   |
+---------------------------------+-------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------------------+
|                         EXTRACTION LAYER (extractor.py / azure_sql_reader.py)     |
|   - Ingests raw tabular data into unified pandas.DataFrame                        |
|   - Validates non-empty datasets & handles connection/file missing errors          |
+---------------------------------+-------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------------------+
|                         TRANSFORMATION LAYER (transformer.py)                    |
|   - Header Normalization (snake_case)                                             |
|   - ISO Datetime Parsing (pd.to_datetime with NaT error coercion)                 |
|   - Deduplication (drops fully duplicate rows)                                    |
|   - Missing Value Imputation (numeric -> 0, text -> 'unknown')                    |
|   - Derived Metric Computation (amount_usd = amount * exchange_rate)              |
+---------------------------------+-------------------------------------------------+
                                  |
            +---------------------+---------------------+
            |                                           |
            v                                           v
+-----------------------+                   +-----------------------+
|  LOCAL PERSISTENCE    |                   |   CLOUD PERSISTENCE   |
|     (loader.py)       |                   |  (azure_loader.py)    |
| - Local SQLite DB     |                   | - In-Memory CSV Stream |
| - Append/Upsert Modes |                   | - Azure Blob Storage  |
+-----------+-----------+                   +-----------+-----------+
            |                                           |
            +---------------------+---------------------+
                                  |
                                  v
+-----------------------------------------------------------------------------------+
|                         REPORTING & ANALYTICS LAYER (viz.py)                      |
|   - Summary Statistics Matrix (df.describe())                                     |
|   - Visual Analytics (Matplotlib Distribution Histogram & Regional Bar Chart)     |
|   - Presentation Layer (Responsive HTML Report: report_<timestamp>.html)          |
+---------------------------------+-------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------------------+
|                     AUTOMATION & DISTRIBUTION LAYER (emailer.py)                   |
|   - Secure TLS Relay Dispatch (smtp.gmail.com:587)                                |
|   - Stakeholder Mail Delivery (Attaches HTML Report & Chart PNG Assets)           |
+-----------------------------------------------------------------------------------+
```

---

## 2. Architectural Module Matrix & Responsibilities

| File Name | Function Signature | Architectural Responsibility & Module Design |
| :--- | :--- | :--- |
| `run_etl.py` | `main() -> None` | Ingests `.env` configurations, manages dual logging (`logs/etl.log`), sequences extraction, transformation, SQLite storage, Azure Blob upload, visual reporting, and automated email dispatch. |
| `extractor.py` | `extract(csv_path: str) -> pd.DataFrame`<br>`extract_csv(csv_path: str) -> pd.DataFrame` | Ingests raw tabular rows out of localized physical system paths, validates non-empty contents, and returns pandas DataFrame. |
| `azure_sql_reader.py` | `read_from_azure_sql(table_name: str = "transactions") -> pd.DataFrame` | Establishes encrypted ODBC channels to remote Azure SQL servers to stream enterprise data packages down to the pipeline. |
| `transformer.py` | `transform(df: pd.DataFrame, exchange_rate: float = 1.0) -> pd.DataFrame`<br>`to_snake_case(col_name: str) -> str` | Executes standard operational logic: `snake_case` formatting, schema validation, ISO datetime parsing, deduplication, missing value imputation, and `amount_usd` calculation. |
| `loader.py` | `load(df: pd.DataFrame, table_name: str, db_path: str, mode: str = "append") -> None` | Establishes SQLite operational connections to store persistent structural outputs locally. Supports `mode="append"` (truncate-append) and `mode="upsert"` (primary key delta update). |
| `azure_loader.py` | `upload_to_azure(df: pd.DataFrame, container_name: str, blob_name: str) -> str` | Streams output data in-memory directly upstream to cloud-managed object paths inside Azure Blob Storage containers. |
| `viz.py` | `create_report(df: pd.DataFrame, output_dir: str = "reports") -> str` | Performs quick analytical queries (`df.describe()`), builds Matplotlib visual charts (histogram & bar chart), and produces presentation-ready HTML reports (`report_<timestamp>.html`). |
| `emailer.py` | `send_report_email(report_path: str, recipient: str) -> bool` | Connects via secure TLS SMTP relays (`smtp.gmail.com:587`) to automatically deliver HTML reports and PNG chart attachments to project stakeholders. |

---

## 3. Setup & Local Execution Guide

### 3.1 Prerequisites
- **Python 3.10+** installed on your system.
- Git or access to project files.

### 3.2 Installation & Virtual Environment
Create and activate a isolated virtual environment, then install dependencies:

```bash
# Navigate to project directory
cd etl-cloud-pipeline

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3.3 Environment Setup
Copy the template `.env.example` file to create your active `.env` file:

```bash
cp .env.example .env
```

Default local testing configuration:
```env
CSV_PATH=data/dummy_data.csv
DB_PATH=data/etl.db
READ_FROM_AZURE_SQL=false
UPLOAD_TO_AZURE=false
SEND_EMAIL=false
```

---

## 4. How to Run Pipeline & Verification

### 4.1 Running the Main ETL Pipeline
Execute the main orchestrator script:

```bash
python run_etl.py
```

Expected Output Summary:
```text
==================================================
         🎉 ETL PIPELINE EXECUTION SUMMARY         
==================================================
  • Rows Processed : 50
  • SQLite Database: C:\...\data\etl.db
  • Summary Report : C:\...\reports\report_20260802_143000.html
  • Azure Upload   : Disabled
  • Email Status   : Disabled (SEND_EMAIL=false)
==================================================
```

### 4.2 Verifying Database Content
Verify rows stored inside SQLite:

```bash
python verify_db.py
```

### 4.3 How to Run Automated Unit Tests
Run the pytest test suite:

```bash
pytest
```

To run with verbose output:
```bash
pytest -v
```

---

## 5. Troubleshooting Common Errors

| Observed Error Signature | Root Cause Analysis | Recommended Technical Solution |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'etl'` | Python execution is running out-of-context from a sub-directory block. | Change your current working directory to the absolute project root folder where `run_etl.py` resides. Ensure virtual environment is activated. |
| `smtplib.SMTPAuthenticationError` | Gmail security settings or invalid password credentials are blocking SMTP connection. | 1. Enable 2-Step Verification on your Google Account.<br>2. Generate a unique 16-character **App Password** under Account Security.<br>3. Use the App Password in your `.env` file under `SMTP_PASS`. |
| `pyodbc.Error: IM002 Data source name not found` | The local system does not have the required Microsoft SQL Server ODBC driver installed. | 1. Download and install **Microsoft ODBC Driver 18 for SQL Server** from Microsoft's official download page.<br>2. Verify spelling of `AZURE_SQL_DRIVER` in `.env`. |

---

## 6. Known Limitations

> [!IMPORTANT]
> **Cloud Credentials Dependency**: Live integration testing for Azure SQL Server (`READ_FROM_AZURE_SQL=true`) and Azure Blob Storage (`UPLOAD_TO_AZURE=true`) requires valid, active Azure credentials and an installed Microsoft ODBC Driver 18 for SQL Server. When running locally without active cloud subscriptions, set `READ_FROM_AZURE_SQL=false` and `UPLOAD_TO_AZURE=false` in your `.env` file to execute the local file ingestion and SQLite pipeline seamlessly.
