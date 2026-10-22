# ETL Pipeline with Cloud Integration & Automated Reporting

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PEP8](https://img.shields.io/badge/code%20style-pep8-green.svg)](https://www.python.org/dev/peps/pep-0008/)

An industrial-grade Extract-Transform-Load (ETL) data engineering capstone project demonstrating multi-source ingestion, pandas data cleaning, hybrid persistence (SQLite & Azure Blob Storage), Matplotlib visual analytics, and automated SMTP email report distribution.

---

## ⚡ Quickstart Guide

### 1. Prerequisites & Installation
Ensure Python **3.10+** is installed on your system.

```bash
# Clone or navigate to the project root directory
cd etl-cloud-pipeline

# Create a virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy the template configuration file to `.env`:

```bash
cp .env.example .env
```

Review `.env` settings (defaults run seamlessly locally without requiring cloud keys):
```env
CSV_PATH=data/dummy_data.csv
DB_PATH=data/etl.db
READ_FROM_AZURE_SQL=false
UPLOAD_TO_AZURE=false
SEND_EMAIL=false
```

### 3. Run Pipeline & Verification
Execute the main ETL pipeline orchestrator:

```bash
python run_etl.py
```

Verify inserted SQLite database records:

```bash
python verify_db.py
```

Run the pytest unit test suite:

```bash
pytest
```

---

## 📁 Repository Structure

```text
etl-cloud-pipeline/
├── etl/
│   ├── __init__.py           # Package exports
│   ├── extractor.py          # Local CSV ingestion module
│   ├── azure_sql_reader.py   # Azure SQL Server pyodbc extraction module
│   ├── transformer.py        # Cleaning, snake_case, ISO datetimes, USD calculations
│   ├── loader.py             # SQLite relational database loader (append & upsert)
│   ├── azure_loader.py       # Azure Blob Storage in-memory CSV uploader
│   ├── viz.py                # Visual chart generator & HTML report builder
│   └── emailer.py            # Automated SMTP email notification module
├── data/
│   └── dummy_data.csv        # Synthetic transaction dataset (~50 records)
├── reports/                  # Generated PNG charts and HTML reports (git-ignored)
├── logs/                     # Execution log outputs (git-ignored)
├── tests/                    # Pytest unit testing suite
│   ├── __init__.py
│   └── test_pipeline.py      # Unit test suite covering all modules & edge cases
├── run_etl.py                # Main pipeline orchestrator script
├── verify_db.py              # SQLite database verification script
├── requirements.txt          # Pinned dependencies
├── .env.example              # Environment variables template with comments
├── .gitignore                # Git exclusions (.env, *.db, reports/, logs/, etc.)
├── CAPSTONE_PROJECT.md       # Capstone learning guide, rubric & troubleshooting
└── README.md                 # Quickstart guide
```
