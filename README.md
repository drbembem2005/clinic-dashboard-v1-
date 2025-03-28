# Advanced Clinic Financial Analytics Dashboard

This Streamlit dashboard provides comprehensive financial and operational analytics for a clinic, including AI-powered predictions.

## Features

*   **Executive Summary:** High-level KPIs and revenue trends.
*   **Financial Performance:** Detailed breakdown of revenue, profit, and commissions.
*   **Doctor Analytics:** Performance metrics, efficiency analysis, and trends per doctor.
*   **Patient Insights:** Segmentation, visit patterns, revenue analysis, and RFM loyalty analysis.
*   **Operational Metrics:** Visit distribution, duration analysis, and resource utilization estimates.
*   **AI Predictions:** Revenue/visit forecasting, pattern analysis, and ML model comparison.
*   **Detailed Reports:** Customizable and exportable reports (CSV, Excel).

## Setup

1.  **Clone the repository (if applicable):**
    ```bash
    git clone <repository-url>
    cd new-clinic-dashboard-main
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Prepare Data:**
    *   Ensure you have the `clinic_financial_ai.xlsx` file in the main project directory (`d:/new-clinic-dashboard-main`).
    *   The Excel file should contain a sheet named `data` with the necessary columns (e.g., `date`, `gross income`, `Doctor`, `Patient`, `visit type`, commission columns, etc.). Refer to `src/data_loader.py` for details on required and processed columns.

## Running the Dashboard

1.  **Activate the virtual environment (if not already active):**
    ```bash
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

2.  **Run the Streamlit app:**
    ```bash
    streamlit run main.py
    ```

3.  The dashboard should open automatically in your web browser.

## Project Structure

```
new-clinic-dashboard-main/
├── clinic_financial_ai.xlsx  # Input data file
├── main.py                   # Main Streamlit application script
├── README.md                 # This file
├── requirements.txt          # Python dependencies
└── src/                      # Source code directory
    ├── data_loader.py        # Data loading and preprocessing logic
    ├── sidebar.py            # Sidebar rendering logic
    └── tabs/                 # Directory for individual tab modules
        ├── __init__.py
        ├── ai_predictions.py
        ├── detailed_reports.py
        ├── doctor_analytics.py
        ├── executive_summary.py
        ├── financial_performance.py
        ├── operational_metrics.py
        └── patient_insights.py
