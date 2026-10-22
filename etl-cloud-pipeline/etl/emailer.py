"""Automated SMTP Notification and Reporting Emailer Module.

Connects via secure SMTP relays to automatically deliver visual attachments and HTML reports to project stakeholders.
"""

from datetime import datetime
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Emailer")


def send_report_email(report_path: str, recipient: str) -> bool:
    """Compose and send an automated ETL report email with HTML report and PNG chart attachments.

    Reads `SMTP_USER` and `SMTP_PASS` from environment variables.
    Uses TLS encryption over port 587 (e.g., smtp.gmail.com).

    Args:
        report_path (str): File path to the generated HTML report file.
        recipient (str): Destination email address for the stakeholder recipient.

    Returns:
        bool: True if email dispatch succeeded, False if any error occurred (does NOT raise).
    """
    load_dotenv()

    smtp_user: Optional[str] = os.getenv("SMTP_USER")
    smtp_pass: Optional[str] = os.getenv("SMTP_PASS")
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))

    if not smtp_user or not smtp_pass:
        logger.warning(
            "SMTP credentials missing. Please define SMTP_USER and SMTP_PASS in your .env file."
        )
        return False

    if not os.path.exists(report_path):
        logger.error(f"HTML report file path does not exist: '{report_path}'")
        return False

    today_str = datetime.now().strftime("%Y-%m-%d")
    subject = f"ETL Pipeline Report - {today_str}"
    body = (
        "Hello Stakeholder,\n\n"
        "The automated ETL Pipeline has completed execution.\n"
        "Please find the summary HTML report and visual analytics charts attached.\n\n"
        "Best regards,\n"
        "Data Engineering Pipeline Automation"
    )

    try:
        logger.info(f"Composing report email to '{recipient}' via {smtp_server}:{smtp_port}...")
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = recipient
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        # Attach main HTML report file
        with open(report_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{os.path.basename(report_path)}"'
            )
            msg.attach(part)

        # Look for PNG chart images alongside the report in the same directory
        report_dir = os.path.dirname(report_path)
        if os.path.exists(report_dir):
            for file in os.listdir(report_dir):
                if file.endswith(".png") and ("chart_" in file or "histogram" in file or "bar" in file):
                    png_path = os.path.join(report_dir, file)
                    try:
                        with open(png_path, "rb") as pf:
                            chart_part = MIMEBase("image", "png")
                            chart_part.set_payload(pf.read())
                            encoders.encode_base64(chart_part)
                            chart_part.add_header(
                                "Content-Disposition",
                                f'attachment; filename="{file}"'
                            )
                            msg.attach(chart_part)
                            logger.info(f"Attached chart image: '{file}'")
                    except Exception as attach_err:
                        logger.warning(f"Could not attach PNG image '{file}': {attach_err}")

        # Connect to SMTP server and send email
        logger.info(f"Connecting to SMTP relay server '{smtp_server}:{smtp_port}'...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, recipient, msg.as_string())
        server.quit()

        logger.info(f"Successfully dispatched report email to '{recipient}'!")
        return True

    except smtplib.SMTPAuthenticationError as auth_err:
        logger.error(
            f"SMTP Authentication Error: {auth_err}. "
            "Hint: For Gmail, ensure 2-Step Verification is enabled and use a 16-character App Password "
            "instead of your primary account password in the SMTP_PASS variable."
        )
        return False

    except smtplib.SMTPException as smtp_err:
        logger.error(f"SMTP protocol error during email dispatch: {smtp_err}")
        return False

    except Exception as err:
        logger.error(f"Unexpected error sending report email to '{recipient}': {err}")
        return False

