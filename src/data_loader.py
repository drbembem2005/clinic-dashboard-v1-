# src/data_loader.py
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta

@st.cache_data(ttl=3600)
def load_data():
    """
    Loads and preprocesses data from the clinic_financial_ai.xlsx file.

    Returns:
        pd.DataFrame: The preprocessed DataFrame.
    """
    try:
        file_path = "clinic_financial_ai.xlsx"
        xls = pd.ExcelFile(file_path)
        df_data = pd.read_excel(xls, sheet_name="data")
    except FileNotFoundError:
        st.error(f"Error: The file {file_path} was not found.")
        st.stop()
    except Exception as e:
        st.error(f"Error loading data from {file_path}: {e}")
        st.stop()

    # --- Data Preprocessing ---
    # Convert date column
    df_data["date"] = pd.to_datetime(df_data["date"], errors='coerce')
    df_data.dropna(subset=["date"], inplace=True) # Remove rows where date conversion failed

    # Fill missing numeric values with 0 - Be cautious with this approach
    numeric_cols = df_data.select_dtypes(include=np.number).columns
    df_data[numeric_cols] = df_data[numeric_cols].fillna(0)

    # --- Commission Calculations ---
    # Ensure commission columns exist and are numeric
    commission_cols = [
        "doctor comission payed", "com to be payed", "T.doc.com", "com pay", "gross income"
    ]
    for col in commission_cols:
        if col not in df_data.columns:
            st.warning(f"Column '{col}' not found in data. Filling with 0.")
            df_data[col] = 0
        else:
            df_data[col] = pd.to_numeric(df_data[col], errors='coerce').fillna(0)

    # If "com to be payed" has value, doctor receives monthly commission only
    df_data["commission_paid_daily"] = df_data["doctor comission payed"]  # Daily commission for doctors
    df_data["commission_paid_monthly"] = df_data["com to be payed"]  # Monthly commission for doctors
    df_data["total_commission"] = df_data["T.doc.com"] # Total doctor commission

    # Handle advertising company commissions
    df_data["advertising_commission"] = df_data["com pay"]

    # --- Profit Calculation ---
    df_data["total_deductions"] = df_data["total_commission"] + df_data["advertising_commission"]
    df_data["profit"] = df_data["gross income"] - df_data["total_deductions"]

    # Avoid division by zero for profit margin
    df_data["profit_margin_pct"] = np.where(
        df_data["gross income"] > 0,
        (df_data["profit"] / df_data["gross income"]) * 100,
        0
    )

    # --- Derived Date/Time Columns ---
    df_data["month"] = df_data["date"].dt.month
    df_data["month_name"] = df_data["date"].dt.month_name()
    df_data["month_year"] = df_data["date"].dt.strftime('%Y-%m')
    df_data["day"] = df_data["date"].dt.day
    df_data["day_of_week"] = df_data["date"].dt.day_name()
    # Use .astype(int) after ensuring the Series contains only valid integer representations or NaNs handled
    df_data["week"] = df_data["date"].dt.isocalendar().week.fillna(0).astype(int) # Fill NA before converting
    df_data["hour"] = df_data["date"].dt.hour

    # --- Categorical Columns ---
    # Payment method categorization
    df_data["payment_method"] = np.where(df_data["cash pay"] > 0, "Cash",
                                np.where(df_data["visa pay"] > 0, "Visa", "Other"))

    # Ensure 'visit type' exists
    if "visit type" not in df_data.columns:
        st.warning("Column 'visit type' not found. Using 'Unknown'.")
        df_data["visit type"] = "Unknown"
    else:
        df_data["visit type"] = df_data["visit type"].fillna("Unknown").astype(str)

    # Ensure 'Doctor' exists
    if "Doctor" not in df_data.columns:
        st.warning("Column 'Doctor' not found. Using 'Unknown'.")
        df_data["Doctor"] = "Unknown"
    else:
        df_data["Doctor"] = df_data["Doctor"].fillna("Unknown").astype(str)

    # Ensure 'Patient' exists
    if "Patient" not in df_data.columns:
        st.warning("Column 'Patient' not found. Using 'Unknown'.")
        df_data["Patient"] = "Unknown" # Or generate unique IDs if needed
    else:
        # Ensure Patient IDs are consistent, maybe string type
        df_data["Patient"] = df_data["Patient"].fillna("Unknown").astype(str)

    # --- Simulated Data (Placeholder) ---
    # Calculate visit duration (random for demonstration - replace if real data exists)
    np.random.seed(42)
    df_data["visit_duration_mins"] = np.random.randint(15, 60, size=len(df_data))

    # --- Final Checks ---
    # Ensure essential columns are present
    essential_cols = ["date", "gross income", "profit", "Doctor", "Patient", "visit type", "id"]
    for col in essential_cols:
        if col not in df_data.columns:
            # If 'id' is missing, try to create a unique identifier
            if col == 'id':
                st.warning("Column 'id' not found. Creating a unique ID from index.")
                df_data['id'] = df_data.index.astype(str)
            else:
                st.error(f"Essential column '{col}' is missing after preprocessing. Stopping.")
                st.stop()

    # Convert 'id' to string if it's potentially numeric to avoid issues
    if 'id' in df_data.columns and pd.api.types.is_numeric_dtype(df_data['id']):
        df_data['id'] = df_data['id'].astype(str)


    return df_data
