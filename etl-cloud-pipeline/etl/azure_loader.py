"""Azure Blob Storage Loader Module.

Streams output data in-memory directly upstream to cloud-managed object storage containers inside Azure Blob Storage.
"""

import io
import logging
import os
from typing import Optional
import pandas as pd
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AzureLoader")


class AzureUploadError(Exception):
    """Custom exception raised when in-memory CSV upload to Azure Blob Storage fails."""
    pass


def upload_to_azure(df: pd.DataFrame, container_name: str, blob_name: str) -> str:
    """Upload a pandas DataFrame as an in-memory CSV stream directly to an Azure Blob Storage container.

    Reads `AZURE_STORAGE_CONNECTION_STRING` from environment variables.
    Automatically creates the destination container if it does not already exist.

    Args:
        df (pd.DataFrame): Input DataFrame to upload.
        container_name (str): Destination Azure Blob container name.
        blob_name (str): Target blob name (path inside container).

    Returns:
        str: Public or accessible URL of the uploaded blob artifact on success.

    Raises:
        ValueError: If df is empty/None or AZURE_STORAGE_CONNECTION_STRING is missing.
        AzureUploadError: If Azure Blob Storage upload fails.
        RuntimeError: For unexpected execution errors.
    """
    load_dotenv()

    if df is None or df.empty:
        err_msg = "Input DataFrame for Azure Blob upload is empty or None."
        logger.error(err_msg)
        raise ValueError(err_msg)

    conn_str: Optional[str] = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str:
        err_msg = "AZURE_STORAGE_CONNECTION_STRING environment variable is missing or empty."
        logger.error(err_msg)
        raise ValueError(err_msg)

    try:
        logger.info(f"Converting DataFrame ({len(df)} rows) to in-memory CSV stream...")
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_bytes = csv_buffer.getvalue().encode("utf-8")

        logger.info(f"Initializing Azure BlobServiceClient for container '{container_name}'...")
        blob_service_client = BlobServiceClient.from_connection_string(conn_str)
        container_client = blob_service_client.get_container_client(container_name)

        # Create container if it does not exist
        if not container_client.exists():
            logger.info(f"Container '{container_name}' does not exist. Creating container...")
            container_client.create_container()

        blob_client = container_client.get_blob_client(blob_name)
        logger.info(f"Uploading in-memory CSV payload ({len(csv_bytes)} bytes) to blob '{blob_name}'...")
        blob_client.upload_blob(csv_bytes, overwrite=True)

        blob_url = blob_client.url
        logger.info(f"Successfully uploaded blob to Azure Storage! Blob URL: {blob_url}")
        return blob_url

    except AzureError as azure_err:
        err_msg = f"Azure Blob Storage upload error for blob '{blob_name}': {azure_err}"
        logger.error(err_msg)
        raise AzureUploadError(err_msg) from azure_err
    except Exception as err:
        err_msg = f"Unexpected error during Azure Blob upload: {err}"
        logger.error(err_msg)
        raise RuntimeError(err_msg) from err


def upload_to_azure_blob(
    file_path: str,
    container_name: str,
    connection_string: str,
    blob_name: Optional[str] = None
) -> bool:
    """Wrapper function to support file-path-based upload for existing callers.

    Args:
        file_path (str): Path to file.
        container_name (str): Container name.
        connection_string (str): Connection string.
        blob_name (Optional[str]): Target blob name.

    Returns:
        bool: True if uploaded.
    """
    os.environ["AZURE_STORAGE_CONNECTION_STRING"] = connection_string
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File path '{file_path}' does not exist.")

    target_blob = blob_name if blob_name else os.path.basename(file_path)
    df = pd.read_csv(file_path)
    url = upload_to_azure(df, container_name, target_blob)
    return bool(url)

