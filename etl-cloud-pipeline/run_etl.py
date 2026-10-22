"""Main Pipeline Orchestrator (run_etl.py).

Loads system configurations via python-dotenv, sets up dual console and file logging (logs/etl.log),
sequences extraction, transformation, SQLite storage, Azure Blob upload, visual reporting, and automated email dispatch.
"""

import logging
import os
import sys
import traceback
from typing import Optional
from dotenv import load_dotenv

from etl.extractor import extract
from etl.azure_sql_reader import read_from_azure_sql
from etl.transformer import transform
from etl.loader import load
from etl.azure_loader import upload_to_azure
from etl.viz import create_report
from etl.emailer import send_report_email


def setup_logging(log_dir: str = "logs", log_file: str = "etl.log") -> logging.Logger:
    """Set up logging to output to both console and a timestamped file in log_dir.

    Args:
        log_dir (str): Directory for log files. Defaults to 'logs'.
        log_file (str): Log filename. Defaults to 'etl.log'.

    Returns:
        logging.Logger: Configured logger instance.
    """
    os.makedirs(log_dir, exist_ok=True)
    full_log_path = os.path.join(log_dir, log_file)

    log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove pre-existing handlers to prevent duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler(full_log_path, mode="a", encoding="utf-8")
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    logger = logging.getLogger("ETLOrchestrator")
    logger.info(f"Logging initialized. Output target file: '{full_log_path}'")
    return logger


def main() -> None:
    """Main orchestration workflow for ETL pipeline execution."""
    logger = setup_logging()
    logger.info("==================================================")
    logger.info("Starting ETL Pipeline Execution Sequence...")
    logger.info("==================================================")

    # 1. Load environment configuration
    load_dotenv()

    # 2. Read config & toggles
    csv_path: str = os.getenv("CSV_PATH", "data/dummy_data.csv")
    db_path: str = os.getenv("DB_PATH", "data/etl.db")
    read_from_azure_sql_flag: bool = os.getenv("READ_FROM_AZURE_SQL", "false").lower() == "true"
    upload_to_azure_flag: bool = os.getenv("UPLOAD_TO_AZURE", "false").lower() == "true"
    send_email_flag: bool = os.getenv("SEND_EMAIL", "false").lower() == "true"
    recipient_email: str = os.getenv("RECIPIENT_EMAIL", "stakeholder@example.com")
    azure_container: str = os.getenv("AZURE_CONTAINER_NAME", "etl-reports")

    logger.info("Configuration Settings:")
    logger.info(f"  - CSV_PATH: {csv_path}")
    logger.info(f"  - DB_PATH: {db_path}")
    logger.info(f"  - READ_FROM_AZURE_SQL: {read_from_azure_sql_flag}")
    logger.info(f"  - UPLOAD_TO_AZURE: {upload_to_azure_flag}")
    logger.info(f"  - SEND_EMAIL: {send_email_flag} ({recipient_email})")

    # 3. Extraction
    try:
        if read_from_azure_sql_flag:
            logger.info("READ_FROM_AZURE_SQL is true. Ingesting data from Azure SQL Server...")
            raw_df = read_from_azure_sql(table_name="transactions")
        else:
            logger.info(f"Ingesting local CSV file from path: '{csv_path}'...")
            raw_df = extract(csv_path)

        logger.info(f"Extraction successful. Ingested {len(raw_df)} raw records.")

    except Exception as extract_err:
        logger.error(f"Extraction Stage Failed: {extract_err}")
        logger.error("Pipeline execution halted gracefully due to extraction error.")
        sys.exit(1)

    # 4. Transformation
    logger.info("Transforming ingested dataset (snake_case, datetimes, deduplication, USD amounts)...")
    cleaned_df = transform(raw_df)
    logger.info(f"Transformation complete. Clean record count: {len(cleaned_df)}")

    # 5. Local SQLite Storage (Always executed)
    logger.info(f"Loading clean records into local SQLite database at '{db_path}'...")
    load(cleaned_df, table_name="data_table", db_path=db_path, mode="append")

    # 6. Azure Blob Storage Upload (Toggled)
    azure_blob_url: Optional[str] = None
    if upload_to_azure_flag:
        logger.info("UPLOAD_TO_AZURE is true. Uploading dataset to Azure Blob Storage...")
        try:
            blob_name = f"transactions_{os.path.basename(csv_path)}"
            azure_blob_url = upload_to_azure(cleaned_df, container_name=azure_container, blob_name=blob_name)
            logger.info(f"Azure Blob upload successful: {azure_blob_url}")
        except Exception as azure_err:
            logger.error(f"Azure Blob Storage upload failed: {azure_err}")
            logger.warning("Continuing pipeline execution despite Azure Blob upload failure...")

    # 7. Visual Analytics & HTML Report Generation
    logger.info("Generating statistical visual summary charts and HTML report...")
    report_path = create_report(cleaned_df, output_dir="reports")
    logger.info(f"HTML report successfully created at: '{report_path}'")

    # 8. Automated Email Notification (Toggled)
    email_status_str = "Disabled (SEND_EMAIL=false)"
    if send_email_flag:
        logger.info(f"SEND_EMAIL is true. Dispatching report email to '{recipient_email}'...")
        try:
            email_success = send_report_email(report_path=report_path, recipient=recipient_email)
            if email_success:
                email_status_str = f"Successfully Sent to {recipient_email}"
            else:
                email_status_str = f"Failed to send to {recipient_email} (check logs)"
        except Exception as email_err:
            logger.error(f"Email dispatch stage encountered error: {email_err}")
            email_status_str = f"Error: {email_err}"
            logger.warning("Pipeline proceeding normally despite email dispatch failure.")

    # 9. Clean Final Execution Summary
    print("\n==================================================")
    print("         🎉 ETL PIPELINE EXECUTION SUMMARY         ")
    print("==================================================")
    print(f"  • Rows Processed : {len(cleaned_df)}")
    print(f"  • SQLite Database: {os.path.abspath(db_path)}")
    print(f"  • Summary Report : {os.path.abspath(report_path)}")
    print(f"  • Azure Upload   : {azure_blob_url if azure_blob_url else ('Disabled' if not upload_to_azure_flag else 'Failed')}")
    print(f"  • Email Status   : {email_status_str}")
    print("==================================================\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as unhandled_err:
        logging.error("Unhandled Top-Level Pipeline Exception Detected:")
        logging.error(traceback.format_exc())
        print(f"\n[CRITICAL ERROR] Pipeline terminated unexpectedly: {unhandled_err}")
        sys.exit(1)

