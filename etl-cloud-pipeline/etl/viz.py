"""Reporting and Visual Analytics Module.

Performs quick analytical queries, extracts key statistical metrics (e.g. df.describe()),
builds visual charts via matplotlib, and produces presentation-ready HTML reports.
"""

from datetime import datetime
import logging
import os
from typing import List, Tuple
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless file rendering
import matplotlib.pyplot as plt
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Visualizer")


def generate_charts(df: pd.DataFrame, output_dir: str, timestamp_str: str) -> Tuple[str, str]:
    """Generate matplotlib statistical visual charts and save as PNG images.

    Args:
        df (pd.DataFrame): Transformed transaction DataFrame.
        output_dir (str): Destination directory for PNG chart assets.
        timestamp_str (str): Datetime string tag for unique filenames.

    Returns:
        Tuple[str, str]: Filenames (basenames) of (1) histogram chart and (2) bar chart.
    """
    os.makedirs(output_dir, exist_ok=True)

    hist_filename = f"chart_histogram_{timestamp_str}.png"
    bar_filename = f"chart_region_bar_{timestamp_str}.png"

    hist_path = os.path.join(output_dir, hist_filename)
    bar_path = os.path.join(output_dir, bar_filename)

    # 1. Histogram of amount / amount_usd
    target_amount_col = "amount_usd" if "amount_usd" in df.columns else ("amount" if "amount" in df.columns else None)

    plt.figure(figsize=(8, 5))
    if target_amount_col and target_amount_col in df.columns:
        plt.hist(df[target_amount_col].dropna(), bins=15, color="#2b5c8f", edgecolor="#ffffff", alpha=0.85)
        plt.title(f"Distribution of Transaction Amounts ({target_amount_col.upper()})", fontsize=14, pad=12)
        plt.xlabel("Amount ($)", fontsize=11)
        plt.ylabel("Frequency / Count", fontsize=11)
    else:
        plt.text(0.5, 0.5, "No Numeric Amount Column Found", horizontalalignment='center', verticalalignment='center')

    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(hist_path, dpi=150)
    plt.close()
    logger.info(f"Saved histogram chart image: '{hist_path}'")

    # 2. Bar chart of counts by region
    region_col = "region" if "region" in df.columns else None
    plt.figure(figsize=(8, 5))
    if region_col:
        region_counts = df[region_col].value_counts()
        bars = plt.bar(region_counts.index.astype(str), region_counts.values, color="#10b981", edgecolor="#ffffff", alpha=0.85)
        plt.title("Transaction Count by Region", fontsize=14, pad=12)
        plt.xlabel("Region", fontsize=11)
        plt.ylabel("Number of Transactions", fontsize=11)
        plt.xticks(rotation=30, ha="right")

        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.2, int(yval), ha='center', va='bottom', fontsize=9)
    else:
        plt.text(0.5, 0.5, "No Region Category Column Found", horizontalalignment='center', verticalalignment='center')

    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(bar_path, dpi=150)
    plt.close()
    logger.info(f"Saved region bar chart image: '{bar_path}'")

    return hist_filename, bar_filename


def create_report(df: pd.DataFrame, output_dir: str = "reports") -> str:
    """Execute reporting workflow: compute describe(), generate charts, build HTML report.

    Args:
        df (pd.DataFrame): Transformed DataFrame containing transaction data.
        output_dir (str): Directory where charts and HTML report will be saved. Defaults to 'reports'.

    Returns:
        str: Absolute or full path to the generated report_<timestamp>.html file.

    Raises:
        ValueError: If df is empty or None.
        RuntimeError: If report generation fails.
    """
    if df is None or df.empty:
        err_msg = "Input DataFrame for visual reporting is empty or None."
        logger.error(err_msg)
        raise ValueError(err_msg)

    try:
        os.makedirs(output_dir, exist_ok=True)
        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        formatted_time = now.strftime("%B %d, %Y - %H:%M:%S")

        logger.info(f"Computing statistical summary (df.describe()) for {len(df)} records...")
        summary_stats = df.describe(include="all").fillna("-")

        # Render summary_stats as HTML table
        describe_html = summary_stats.to_html(classes="stats-table", border=0)

        # Generate Matplotlib PNG visuals
        hist_fname, bar_fname = generate_charts(df, output_dir, timestamp_str)

        report_filename = f"report_{timestamp_str}.html"
        report_path = os.path.abspath(os.path.join(output_dir, report_filename))

        usd_total_str = f"${df['amount_usd'].sum():,.2f}" if "amount_usd" in df.columns else "N/A"

        # Build clean responsive HTML document
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ETL Pipeline Execution Summary Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f8fafc;
            color: #1e293b;
            margin: 0;
            padding: 30px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            padding: 32px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        }}
        .header {{
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 20px;
            margin-bottom: 24px;
        }}
        .header h1 {{
            margin: 0 0 8px 0;
            color: #0f172a;
            font-size: 26px;
        }}
        .header .meta {{
            color: #64748b;
            font-size: 14px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }}
        .card {{
            background: #f1f5f9;
            padding: 16px;
            border-radius: 8px;
            text-align: center;
        }}
        .card .value {{
            font-size: 24px;
            font-weight: 700;
            color: #2563eb;
        }}
        .card .label {{
            font-size: 12px;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .charts-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .chart-box {{
            flex: 1 1 450px;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }}
        .chart-box img {{
            max-width: 100%;
            height: auto;
            border-radius: 6px;
        }}
        .table-container {{
            overflow-x: auto;
            margin-top: 24px;
        }}
        table.stats-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        table.stats-table th, table.stats-table td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        table.stats-table th {{
            background-color: #f8fafc;
            color: #334155;
            font-weight: 600;
        }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            font-size: 12px;
            color: #94a3b8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 ETL Pipeline Automated Summary Report</h1>
            <div class="meta">Generated on <strong>{formatted_time}</strong> | Ingested Dataset Size: <strong>{len(df)} Records</strong></div>
        </div>

        <div class="metrics-grid">
            <div class="card">
                <div class="value">{len(df)}</div>
                <div class="label">Total Records</div>
            </div>
            <div class="card">
                <div class="value">{len(df.columns)}</div>
                <div class="label">Total Attributes</div>
            </div>
            <div class="card">
                <div class="value">{usd_total_str}</div>
                <div class="label">Total USD Volume</div>
            </div>
        </div>

        <h2>Visual Analytics</h2>
        <div class="charts-container">
            <div class="chart-box">
                <h3>Amount Distribution</h3>
                <img src="{hist_fname}" alt="Amount Distribution Histogram">
            </div>
            <div class="chart-box">
                <h3>Regional Breakdown</h3>
                <img src="{bar_fname}" alt="Regional Transaction Count Bar Chart">
            </div>
        </div>

        <h2>Statistical Summary (df.describe)</h2>
        <div class="table-container">
            {describe_html}
        </div>

        <div class="footer">
            <p>ETL Pipeline Capstone Framework • Automated Cloud & Reporting Engine</p>
        </div>
    </div>
</body>
</html>
"""

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Successfully generated HTML report at: '{report_path}'")
        return report_path

    except Exception as err:
        err_msg = f"Unexpected error building visual report: {err}"
        logger.error(err_msg)
        raise RuntimeError(err_msg) from err

