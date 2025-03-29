# main.py
import streamlit as st
import pandas as pd # Keep pandas for potential use
import sys # To modify path for imports
import os # To construct path

# Add src directory to Python path
# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)


# Import modules
# Use absolute imports relative to the src directory structure
try:
    from data_loader import load_data
    from sidebar import render_sidebar
    from tabs.executive_summary import render_executive_summary_tab
    from tabs.financial_performance import render_financial_performance_tab
    from tabs.doctor_analytics import render_doctor_analytics_tab
    from tabs.patient_insights import render_patient_insights_tab
    from tabs.operational_metrics import render_operational_metrics_tab
    from tabs.ai_predictions import render_ai_predictions_tab
    from tabs.detailed_reports import render_detailed_reports_tab
    from tabs.appointment_scheduling import render_appointment_scheduling_tab
    from tabs.daily_workflow import render_daily_workflow_tab # Added import for daily workflow
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.error(f"Current sys.path: {sys.path}")
    st.error("Please ensure the 'src' directory and its contents are structured correctly relative to main.py.")
    st.stop()


# --- Page Configuration ---
st.set_page_config(
    page_title="Advanced Clinic Financial Analytics Dashboard",
    page_icon="💉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Main Header ---
st.title("Advanced Clinic Financial Analytics Dashboard")

# --- Load Data ---
# This now calls the function from data_loader.py
df_data = load_data()

# --- Render Sidebar and Get Filtered Data ---
# This calls the function from sidebar.py
# It returns the filtered dataframe and details about the filters applied
filtered_df, filter_details = render_sidebar(df_data)

# Extract filter details for use in tabs if needed
start_date = filter_details["start_date"]
end_date = filter_details["end_date"]
# selected_doctors = filter_details["selected_doctors"]
# selected_visit_types = filter_details["selected_visit_types"]
# selected_payment_methods = filter_details["selected_payment_methods"]

# --- Main Content Area with Tabs ---
tab_list = [
    "📈 Executive Summary",
    "💰 Financial Performance",
    "👨‍⚕️ Doctor Analytics",
    "👥 Patient Insights",
    "🔍 Operational Metrics",
    "⏱️ Daily Workflow", # Added new tab
    "📅 Appointment Scheduling",
    "🤖 AI Predictions & Analytics",
    "📋 Detailed Reports"
]
tabs = st.tabs(tab_list)

# --- Render Tab Content ---
# Each 'with' block now calls the corresponding render function from the tabs module

with tabs[0]:
    render_executive_summary_tab(filtered_df, df_data, start_date, end_date)

with tabs[1]:
    render_financial_performance_tab(filtered_df)

with tabs[2]:
    render_doctor_analytics_tab(filtered_df)

with tabs[3]:
    render_patient_insights_tab(filtered_df, df_data, start_date, end_date) # Pass df_data, start/end dates if needed for comparisons

with tabs[4]:
    render_operational_metrics_tab(filtered_df, start_date, end_date) # Pass start/end dates for calculations like avg daily visits

# Corrected indices and calls for subsequent tabs
with tabs[5]:
    render_daily_workflow_tab(df_data) # Call to render the new daily workflow tab

with tabs[6]:
    # Pass the main financial data DataFrame to the scheduling tab
    render_appointment_scheduling_tab(df_data)

with tabs[7]:
    render_ai_predictions_tab(filtered_df)

with tabs[8]:
    render_detailed_reports_tab(filtered_df, start_date, end_date) # Pass start/end dates for report range default

# --- Footer or Final Message (Optional) ---
st.sidebar.markdown("---")
st.sidebar.info("Dashboard Refactored & Enhanced by Cline.")

# print("Dashboard structure updated successfully.") # Optional: for local debugging
