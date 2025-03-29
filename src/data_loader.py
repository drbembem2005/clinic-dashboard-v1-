# src/data_loader.py
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta, date, time # Added date, time
import sqlite3 # Added for SQLite
import uuid # Added for generating unique IDs
import os # Added for constructing DB path

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


# --- Appointment Data Handling (SQLite) ---

APPOINTMENTS_DB_PATH = "clinic_appointments.db"

def connect_db():
    """Connects to the SQLite database."""
    conn = sqlite3.connect(APPOINTMENTS_DB_PATH)
    conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
    return conn

def create_appointments_table():
    """Creates the appointments table if it doesn't exist."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            AppointmentID TEXT PRIMARY KEY,
            PatientName TEXT NOT NULL,
            DoctorName TEXT NOT NULL,
            AppointmentDateTime TEXT NOT NULL, -- Store as ISO format string
            AppointmentType TEXT,
            AppointmentStatus TEXT DEFAULT 'Scheduled',
            BookingDateTime TEXT, -- Store as ISO format string
            CancellationDateTime TEXT, -- Store as ISO format string
            ConfirmationStatus TEXT,
            ReminderType TEXT,
            BookingChannel TEXT, -- Added
            ReferralSource TEXT, -- Added
            PatientArrivalTime TEXT, -- Added - Store as ISO time string HH:MM:SS
            AppointmentStartTime TEXT, -- Added - Store as ISO time string HH:MM:SS
            AppointmentEndTime TEXT -- Added - Store as ISO time string HH:MM:SS
        )
    """)
    conn.commit()
    conn.close()

# Ensure the table exists when the module is loaded and update schema if needed
# This simple check might not handle all schema migration scenarios robustly
def update_schema():
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # Check for one of the new columns
        cursor.execute("PRAGMA table_info(appointments)")
        columns = [info['name'] for info in cursor.fetchall()]
        if 'BookingChannel' not in columns:
            cursor.execute("ALTER TABLE appointments ADD COLUMN BookingChannel TEXT")
        if 'ReferralSource' not in columns:
            cursor.execute("ALTER TABLE appointments ADD COLUMN ReferralSource TEXT")
        if 'PatientArrivalTime' not in columns:
            cursor.execute("ALTER TABLE appointments ADD COLUMN PatientArrivalTime TEXT")
        if 'AppointmentStartTime' not in columns:
            cursor.execute("ALTER TABLE appointments ADD COLUMN AppointmentStartTime TEXT")
        if 'AppointmentEndTime' not in columns:
            cursor.execute("ALTER TABLE appointments ADD COLUMN AppointmentEndTime TEXT")
        conn.commit()
    except sqlite3.Error as e:
        st.warning(f"Could not update table schema: {e}") # Warn instead of error
    finally:
        conn.close()

create_appointments_table()
update_schema() # Attempt to update schema after ensuring table exists

def add_appointment(patient_name, doctor_name, appointment_datetime, appointment_type,
                    booking_datetime=None, confirmation_status=None, reminder_type=None,
                    booking_channel=None, referral_source=None, patient_arrival_time=None,
                    appointment_start_time=None, appointment_end_time=None): # Added new params
    """Adds a new appointment to the database."""
    conn = connect_db()
    cursor = conn.cursor()
    appointment_id = str(uuid.uuid4()) # Generate a unique ID
    booking_dt_str = booking_datetime.isoformat() if booking_datetime else None
    appointment_dt_str = appointment_datetime.isoformat()
    # Convert time objects to ISO strings
    arrival_time_str = patient_arrival_time.isoformat() if isinstance(patient_arrival_time, time) else patient_arrival_time
    start_time_str = appointment_start_time.isoformat() if isinstance(appointment_start_time, time) else appointment_start_time
    end_time_str = appointment_end_time.isoformat() if isinstance(appointment_end_time, time) else appointment_end_time


    try:
        cursor.execute("""
            INSERT INTO appointments (
                AppointmentID, PatientName, DoctorName, AppointmentDateTime, AppointmentType,
                AppointmentStatus, BookingDateTime, ConfirmationStatus, ReminderType,
                BookingChannel, ReferralSource, PatientArrivalTime, AppointmentStartTime, AppointmentEndTime
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            appointment_id, patient_name, doctor_name, appointment_dt_str, appointment_type,
            'Scheduled', booking_dt_str, confirmation_status, reminder_type,
            booking_channel, referral_source, arrival_time_str, start_time_str, end_time_str
        ))
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Database error adding appointment: {e}")
        return False
    finally:
        conn.close()

def get_appointments(start_date_filter=None, end_date_filter=None, doctor_filter=None, status_filter=None):
    """Retrieves appointments from the database, optionally filtered."""
    conn = connect_db()
    cursor = conn.cursor()
    query = "SELECT * FROM appointments"
    filters = []
    params = []

    if start_date_filter:
        # Assuming start_date_filter is a date object
        start_dt_str = datetime.combine(start_date_filter, time.min).isoformat()
        filters.append("AppointmentDateTime >= ?")
        params.append(start_dt_str)
    if end_date_filter:
        # Assuming end_date_filter is a date object
        end_dt_str = datetime.combine(end_date_filter, time.max).isoformat()
        filters.append("AppointmentDateTime <= ?")
        params.append(end_dt_str)
    if doctor_filter and doctor_filter != "All":
        filters.append("DoctorName = ?")
        params.append(doctor_filter)
    if status_filter and status_filter != "All":
        filters.append("AppointmentStatus = ?")
        params.append(status_filter)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY AppointmentDateTime ASC" # Order by date/time

    try:
        cursor.execute(query, params)
        appointments = cursor.fetchall()
        # Convert to DataFrame
        df_appointments = pd.DataFrame([dict(row) for row in appointments])
        # Convert datetime columns back from string
        if not df_appointments.empty:
            for col in ['AppointmentDateTime', 'BookingDateTime', 'CancellationDateTime']:
                if col in df_appointments.columns:
                    df_appointments[col] = pd.to_datetime(df_appointments[col], errors='coerce')
        return df_appointments
    except sqlite3.Error as e:
        st.error(f"Database error getting appointments: {e}")
        return pd.DataFrame() # Return empty DataFrame on error
    finally:
        conn.close()


def update_appointment(appointment_id, updates):
    """Updates an existing appointment."""
    conn = connect_db()
    cursor = conn.cursor()
    set_clauses = []
    params = []
    current_time_str = datetime.now().isoformat()

    # Handle Cancellation Time automatically if status is set to Cancelled
    if updates.get('AppointmentStatus') == 'Cancelled' and 'CancellationDateTime' not in updates:
        updates['CancellationDateTime'] = current_time_str
    # Clear cancellation time if status is changed away from Cancelled
    elif 'AppointmentStatus' in updates and updates['AppointmentStatus'] != 'Cancelled':
         updates['CancellationDateTime'] = None # Set to NULL in DB

    # Convert datetime/time objects to ISO strings for storage
    if 'AppointmentDateTime' in updates and isinstance(updates['AppointmentDateTime'], datetime):
        updates['AppointmentDateTime'] = updates['AppointmentDateTime'].isoformat()
    if 'BookingDateTime' in updates and isinstance(updates['BookingDateTime'], datetime):
        updates['BookingDateTime'] = updates['BookingDateTime'].isoformat()
    # CancellationDateTime is handled above or passed as string
    if 'PatientArrivalTime' in updates and isinstance(updates['PatientArrivalTime'], time):
        updates['PatientArrivalTime'] = updates['PatientArrivalTime'].isoformat()
    if 'AppointmentStartTime' in updates and isinstance(updates['AppointmentStartTime'], time):
        updates['AppointmentStartTime'] = updates['AppointmentStartTime'].isoformat()
    if 'AppointmentEndTime' in updates and isinstance(updates['AppointmentEndTime'], time):
        updates['AppointmentEndTime'] = updates['AppointmentEndTime'].isoformat()


    for key, value in updates.items():
        # Ensure we only try to update valid columns
        valid_columns = [
            "PatientName", "DoctorName", "AppointmentDateTime", "AppointmentType",
            "AppointmentStatus", "BookingDateTime", "CancellationDateTime",
            "ConfirmationStatus", "ReminderType", "BookingChannel", "ReferralSource",
            "PatientArrivalTime", "AppointmentStartTime", "AppointmentEndTime"
        ]
        if key in valid_columns:
            set_clauses.append(f"{key} = ?")
            params.append(value)

    if not set_clauses:
        st.warning("No valid fields provided for update.")
        conn.close()
        return False

    params.append(appointment_id) # For the WHERE clause
    query = f"UPDATE appointments SET {', '.join(set_clauses)} WHERE AppointmentID = ?"

    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0 # Return True if a row was updated
    except sqlite3.Error as e:
        st.error(f"Database error updating appointment {appointment_id}: {e}")
        return False
    finally:
        conn.close()

def delete_appointment(appointment_id):
    """Deletes an appointment from the database."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM appointments WHERE AppointmentID = ?", (appointment_id,))
        conn.commit()
        return cursor.rowcount > 0 # Return True if a row was deleted
    except sqlite3.Error as e:
        st.error(f"Database error deleting appointment {appointment_id}: {e}")
        return False
    finally:
        conn.close()

# Modified to get doctors from the main financial DataFrame
def get_distinct_doctors(df_financial_data):
    """Gets a list of distinct doctor names from the financial data DataFrame."""
    if df_financial_data is not None and "Doctor" in df_financial_data.columns:
        try:
            # Get unique, non-null doctor names and sort them
            doctors = df_financial_data["Doctor"].dropna().unique().tolist()
            doctors.sort()
            return doctors
        except Exception as e:
            st.error(f"Error getting distinct doctors from DataFrame: {e}")
            return []
    else:
        st.warning("Financial data or 'Doctor' column not available for fetching doctor list.")
        return []


def get_distinct_patients():
    """Gets a list of distinct patient names from the appointments table."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT PatientName FROM appointments ORDER BY PatientName")
        patients = [row['PatientName'] for row in cursor.fetchall()]
        return patients
    except sqlite3.Error as e:
        st.error(f"Database error getting distinct patients: {e}")
        return []
    finally:
        conn.close()
