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
    # Ensure 'profit' column exists or calculate it
    if 'profit' not in df_data.columns:
        df_data["total_deductions"] = df_data["total_commission"] + df_data["advertising_commission"]
        df_data["profit"] = df_data["gross income"] - df_data["total_deductions"]
    else:
        # Ensure profit is numeric if it exists
        df_data['profit'] = pd.to_numeric(df_data['profit'], errors='coerce').fillna(0)


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
    if "visit_duration_mins" not in df_data.columns:
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
            # Skip profit check here as we calculate it above if missing
            elif col != 'profit':
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


# --- Cost Data Handling (SQLite) ---

def create_costs_table():
    """Creates the costs table if it doesn't exist."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date TEXT NOT NULL, -- Renamed from entry_date (Date cost incurred)
                payment_date TEXT,          -- Date cost was paid (can be NULL if not yet paid)
                category TEXT NOT NULL,
                item TEXT NOT NULL,
                amount REAL NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit() # Commit table creation first

        # Now, attempt to create indexes separately
        try:
            cursor.execute("DROP INDEX IF EXISTS idx_costs_entry_date") # Drop old index if exists
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_costs_expense_date ON costs (expense_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_costs_payment_date ON costs (payment_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_costs_category ON costs (category)")
            conn.commit() # Commit index creation
        except sqlite3.Error as e_index:
            # Warn if index creation fails, but don't stop the app
            st.warning(f"Database warning creating indexes for costs table: {e_index}")

    except sqlite3.Error as e_table:
        st.error(f"Database error creating costs table: {e_table}")
    finally:
        conn.close()

def update_costs_schema():
    """Adds new columns to the costs table if they don't exist."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(costs)")
        columns = [info['name'] for info in cursor.fetchall()]
        if 'expense_date' not in columns:
            # If expense_date doesn't exist, assume entry_date might, try renaming first
            try:
                cursor.execute("ALTER TABLE costs RENAME COLUMN entry_date TO expense_date")
                st.info("Renamed 'entry_date' column to 'expense_date' in costs table.")
            except sqlite3.Error:
                # If rename fails (e.g., entry_date also doesn't exist), add expense_date
                cursor.execute("ALTER TABLE costs ADD COLUMN expense_date TEXT")
                st.info("Added 'expense_date' column to costs table.")
        if 'payment_date' not in columns:
            cursor.execute("ALTER TABLE costs ADD COLUMN payment_date TEXT")
            st.info("Added 'payment_date' column to costs table.")
        conn.commit()
    except sqlite3.Error as e:
        st.warning(f"Could not update costs table schema: {e}")
    finally:
        conn.close()

# Ensure the costs table exists and schema is updated when the module is loaded
create_costs_table()
update_costs_schema() # Call the new schema update function

def add_cost(expense_date, payment_date, category, item, amount):
    """Adds a new cost entry to the database."""
    conn = connect_db()
    cursor = conn.cursor()
    # Ensure dates are stored in YYYY-MM-DD format
    expense_date_str = expense_date.isoformat() if isinstance(expense_date, date) else str(expense_date)
    # Payment date can be None
    payment_date_str = payment_date.isoformat() if isinstance(payment_date, date) else None
    try:
        cursor.execute("""
            INSERT INTO costs (expense_date, payment_date, category, item, amount)
            VALUES (?, ?, ?, ?, ?)
        """, (expense_date_str, payment_date_str, category, item, amount))
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Database error adding cost: {e}")
        return False
    finally:
        conn.close()

def get_costs(start_date_filter=None, end_date_filter=None, date_column='expense_date'):
    """
    Retrieves cost entries from the database, optionally filtered by a specified date column.

    Args:
        start_date_filter (date, optional): Start date for filtering.
        end_date_filter (date, optional): End date for filtering.
        date_column (str, optional): The date column to filter on ('expense_date' or 'payment_date').
                                     Defaults to 'expense_date'.
    """
    conn = connect_db()
    cursor = conn.cursor()
    # Select all relevant columns
    query = "SELECT id, expense_date, payment_date, category, item, amount, recorded_at FROM costs"
    filters = []
    params = []

    # Validate date_column input
    if date_column not in ['expense_date', 'payment_date']:
        st.warning(f"Invalid date column '{date_column}' specified for filtering costs. Defaulting to 'expense_date'.")
        date_column = 'expense_date'

    if start_date_filter:
        start_date_str = start_date_filter.isoformat() if isinstance(start_date_filter, date) else str(start_date_filter)
        filters.append(f"{date_column} >= ?")
        params.append(start_date_str)
    if end_date_filter:
        end_date_str = end_date_filter.isoformat() if isinstance(end_date_filter, date) else str(end_date_filter)
        filters.append(f"{date_column} <= ?")
        params.append(end_date_str)

    # Ensure filtering by payment_date doesn't exclude unpaid items unless intended
    # If filtering by payment_date, we might only want rows where payment_date is not NULL
    # However, the current logic includes NULLs if they fall outside the date range, which might be okay.
    # Add this if you only want paid items within the range when filtering by payment_date:
    # if date_column == 'payment_date':
    #     filters.append("payment_date IS NOT NULL")


    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += f" ORDER BY {date_column} DESC, recorded_at DESC" # Order by the filtered date column

    try:
        cursor.execute(query, params)
        costs = cursor.fetchall()
        # Convert to DataFrame
        df_costs = pd.DataFrame([dict(row) for row in costs])
        # Convert date columns back from string
        if not df_costs.empty:
            df_costs['expense_date'] = pd.to_datetime(df_costs['expense_date'], errors='coerce').dt.date
            # payment_date might be NaT if NULL in DB
            df_costs['payment_date'] = pd.to_datetime(df_costs['payment_date'], errors='coerce').dt.date
            df_costs['recorded_at'] = pd.to_datetime(df_costs['recorded_at'], errors='coerce')
        return df_costs
    except sqlite3.Error as e:
        st.error(f"Database error getting costs: {e}")
        return pd.DataFrame() # Return empty DataFrame on error
    finally:
        conn.close()

# --- Goal Setting Data Handling (SQLite) ---

def create_goals_table():
    """Creates the goals table if it doesn't exist."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                target_value REAL NOT NULL,
                time_period TEXT NOT NULL, -- 'Monthly', 'Quarterly', 'Yearly', 'Custom Range'
                start_date TEXT,          -- YYYY-MM-DD, only for 'Custom Range'
                end_date TEXT,            -- YYYY-MM-DD, only for 'Custom Range'
                is_active INTEGER DEFAULT 1, -- 1 for active, 0 for inactive
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        # Add indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_goals_metric_name ON goals (metric_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_goals_is_active ON goals (is_active)")
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Database error creating goals table: {e}")
    finally:
        conn.close()

def update_goals_schema():
    """Adds new columns to the goals table if they don't exist (for future use)."""
    # Placeholder for future schema changes if needed
    pass

# Ensure the goals table exists and schema is updated
create_goals_table()
update_goals_schema()

def add_goal(metric_name, target_value, time_period, start_date=None, end_date=None, is_active=1):
    """Adds a new goal to the database."""
    conn = connect_db()
    cursor = conn.cursor()
    start_date_str = start_date.isoformat() if isinstance(start_date, date) else None
    end_date_str = end_date.isoformat() if isinstance(end_date, date) else None
    try:
        cursor.execute("""
            INSERT INTO goals (metric_name, target_value, time_period, start_date, end_date, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (metric_name, target_value, time_period, start_date_str, end_date_str, is_active))
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Database error adding goal: {e}")
        return False
    finally:
        conn.close()

def get_goals(active_only=False):
    """Retrieves goals from the database."""
    conn = connect_db()
    cursor = conn.cursor()
    query = "SELECT * FROM goals"
    params = []
    if active_only:
        query += " WHERE is_active = ?"
        params.append(1)
    query += " ORDER BY created_at DESC"
    try:
        cursor.execute(query, params)
        goals = cursor.fetchall()
        df_goals = pd.DataFrame([dict(row) for row in goals])
        # Convert date columns if they exist
        if not df_goals.empty:
            for col in ['start_date', 'end_date', 'created_at']:
                 if col in df_goals.columns:
                     df_goals[col] = pd.to_datetime(df_goals[col], errors='coerce')
                     # Convert start/end date back to date only if needed, handle NaT
                     if col in ['start_date', 'end_date']:
                         df_goals[col] = df_goals[col].dt.date
        return df_goals
    except sqlite3.Error as e:
        st.error(f"Database error getting goals: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def update_goal(goal_id, updates):
    """Updates an existing goal (e.g., toggle active status, change target)."""
    conn = connect_db()
    cursor = conn.cursor()
    set_clauses = []
    params = []

    # Convert dates to strings if present
    if 'start_date' in updates and isinstance(updates['start_date'], date):
        updates['start_date'] = updates['start_date'].isoformat()
    if 'end_date' in updates and isinstance(updates['end_date'], date):
        updates['end_date'] = updates['end_date'].isoformat()

    for key, value in updates.items():
        # Ensure we only try to update valid columns
        valid_columns = [
            "metric_name", "target_value", "time_period",
            "start_date", "end_date", "is_active"
        ]
        if key in valid_columns:
            set_clauses.append(f"{key} = ?")
            params.append(value)

    if not set_clauses:
        st.warning("No valid fields provided for goal update.")
        conn.close()
        return False

    params.append(goal_id) # For the WHERE clause
    query = f"UPDATE goals SET {', '.join(set_clauses)} WHERE id = ?"

    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0 # Return True if a row was updated
    except sqlite3.Error as e:
        st.error(f"Database error updating goal {goal_id}: {e}")
        return False
    finally:
        conn.close()
