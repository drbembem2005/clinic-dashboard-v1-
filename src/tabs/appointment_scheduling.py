# src/tabs/appointment_scheduling.py
import streamlit as st
import pandas as pd
from datetime import datetime, date, time

# Import database functions from data_loader
try:
    # Use relative import if data_loader is in the parent directory
    from ..data_loader import (
        add_appointment,
        get_appointments,
        update_appointment,
        delete_appointment,
        get_distinct_doctors,
        get_distinct_patients
    )
except ImportError:
    # Fallback for direct execution or different structure
    from data_loader import (
        add_appointment,
        get_appointments,
        update_appointment,
        delete_appointment,
        get_distinct_doctors,
        get_distinct_patients
    )

# --- Constants ---
APPOINTMENT_TYPES = ["New Patient", "Follow-up", "Consultation", "Check-up", "Procedure", "Other"]
APPOINTMENT_STATUSES = ["Scheduled", "Confirmed", "Checked-in", "Completed", "Cancelled", "No-Show"]
CONFIRMATION_STATUSES = ["Not Confirmed", "Confirmed", "Reminder Sent"]
REMINDER_TYPES = ["None", "SMS", "Email", "Phone Call"]
# Define some common options, but allow free text too
BOOKING_CHANNELS = ["Online Portal", "Phone", "In-Person", "Referral", "Other"]
REFERRAL_SOURCES = ["Website", "GP Referral", "Existing Patient", "Advertisement", "Walk-in", "Other"]


# --- Helper Functions ---
def combine_date_time(date_part, time_part):
    """Combines date and time objects into a datetime object."""
    if date_part and time_part:
        return datetime.combine(date_part, time_part)
    return None

# --- Main Tab Rendering Function ---
# Modified to accept the financial data DataFrame
def render_appointment_scheduling_tab(df_financial_data):
    """Renders the Appointment Scheduling tab content."""
    st.header("📅 Appointment Scheduling")

    # --- Fetch Initial Data ---
    # Get distinct doctors from the financial data
    # Use session state to store doctors/patients to avoid repeated DB calls
    # We pass df_financial_data now
    if 'distinct_doctors' not in st.session_state or st.session_state.get('doctor_list_source') != 'financial':
        st.session_state.distinct_doctors = get_distinct_doctors(df_financial_data)
        st.session_state.doctor_list_source = 'financial' # Mark the source

    if 'distinct_patients' not in st.session_state:
        st.session_state.distinct_patients = get_distinct_patients() # Fetch patients for potential future use

    distinct_doctors = st.session_state.distinct_doctors
    # Handle case where doctor list might be empty
    if not distinct_doctors:
        st.warning("Could not retrieve doctor list from financial data. Please ensure 'Doctor' column exists and has data.")
        distinct_doctors = [] # Prevent errors in selectbox

    # --- Add New Appointment Form ---
    st.subheader("Add New Appointment")
    with st.form("add_appointment_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3) # Use 3 columns for more fields
        with col1:
            patient_name = st.text_input("Patient Name*", key="add_patient_name")
            appointment_date = st.date_input("Appointment Date*", key="add_date", value=date.today())
            appointment_time = st.time_input("Appointment Time*", key="add_time", value=time(9, 0))
            appointment_type = st.selectbox("Appointment Type", APPOINTMENT_TYPES, key="add_type")

        with col2:
            # Allow adding new doctors if needed, or just select existing
            doctor_name = st.selectbox("Doctor Name*", distinct_doctors + ["Add New Doctor..."], key="add_doctor_name")
            if doctor_name == "Add New Doctor...":
                doctor_name = st.text_input("Enter New Doctor Name", key="add_new_doctor_name")

            # Use selectbox for booking channel and referral source
            booking_channel = st.selectbox("Booking Channel", BOOKING_CHANNELS, key="add_booking_channel")
            referral_source = st.selectbox("Referral Source", REFERRAL_SOURCES, key="add_referral_source")
            confirmation_status = st.selectbox("Confirmation Status", CONFIRMATION_STATUSES, key="add_confirm_status")

        with col3:
            # Time Tracking Inputs (Optional on Add)
            patient_arrival_time = st.time_input("Patient Arrival Time", value=None, key="add_arrival_time")
            appointment_start_time = st.time_input("Appointment Start Time", value=None, key="add_start_time")
            appointment_end_time = st.time_input("Appointment End Time", value=None, key="add_end_time")
            reminder_type = st.selectbox("Reminder Type", REMINDER_TYPES, key="add_reminder_type")

        submitted = st.form_submit_button("Add Appointment")
        if submitted:
            # Basic Validation
            if not patient_name or not doctor_name or not appointment_date or not appointment_time:
                st.error("Please fill in all required fields (*).")
            else:
                appointment_datetime = combine_date_time(appointment_date, appointment_time)
                if appointment_datetime:
                    # Add booking time automatically
                    booking_datetime = datetime.now()
                    success = add_appointment(
                        patient_name=patient_name,
                        doctor_name=doctor_name,
                        appointment_datetime=appointment_datetime,
                        appointment_type=appointment_type,
                        booking_datetime=booking_datetime,
                        confirmation_status=confirmation_status,
                        reminder_type=reminder_type,
                        booking_channel=booking_channel, # Pass new fields
                        referral_source=referral_source,
                        patient_arrival_time=patient_arrival_time,
                        appointment_start_time=appointment_start_time,
                        appointment_end_time=appointment_end_time
                    )
                    if success:
                        st.success("Appointment added successfully!")
                        # Refresh doctor list (re-fetch from financial data) if a new one was added
                        # Note: This assumes adding a new doctor via text input should ideally update the source data,
                        # but for now, we just refresh the list from the existing financial data.
                        # A better approach might be to manage doctors in a separate table.
                        if doctor_name not in st.session_state.distinct_doctors:
                             st.session_state.distinct_doctors = get_distinct_doctors(df_financial_data)
                             st.session_state.doctor_list_source = 'financial'
                        st.rerun() # Rerun to update the view table
                    else:
                        st.error("Failed to add appointment.")
                else:
                    st.error("Invalid date or time.")

    st.divider()

    # --- View, Edit, Delete Appointments ---
    st.subheader("Manage Appointments")

    # Filters
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        filter_start_date = st.date_input("Start Date", value=None, key="filter_start")
    with col_f2:
        filter_end_date = st.date_input("End Date", value=None, key="filter_end")
    with col_f3:
        filter_doctor = st.selectbox("Filter by Doctor", ["All"] + distinct_doctors, key="filter_doctor")
    with col_f4:
        filter_status = st.selectbox("Filter by Status", ["All"] + APPOINTMENT_STATUSES, key="filter_status")

    # Fetch and display appointments
    df_appointments = get_appointments(
        start_date_filter=filter_start_date,
        end_date_filter=filter_end_date,
        doctor_filter=filter_doctor,
        status_filter=filter_status
    )

    if df_appointments.empty:
        st.info("No appointments found matching the criteria.")
    else:
        # Prepare DataFrame for display (format dates, select columns)
        df_display = df_appointments.copy()
        if 'AppointmentDateTime' in df_display.columns:
            df_display['Date'] = df_display['AppointmentDateTime'].dt.strftime('%Y-%m-%d')
            df_display['Time'] = df_display['AppointmentDateTime'].dt.strftime('%H:%M')
            # Add new columns to display if they exist
            df_display['Arrival'] = df_display['PatientArrivalTime'].astype(str).replace('NaT', '') if 'PatientArrivalTime' in df_display else ''
            df_display['Start'] = df_display['AppointmentStartTime'].astype(str).replace('NaT', '') if 'AppointmentStartTime' in df_display else ''
            df_display['End'] = df_display['AppointmentEndTime'].astype(str).replace('NaT', '') if 'AppointmentEndTime' in df_display else ''
            df_display['Cancelled'] = df_display['CancellationDateTime'].dt.strftime('%Y-%m-%d %H:%M') if 'CancellationDateTime' in df_display and pd.notna(df_display['CancellationDateTime']).any() else ''


        display_cols = [
            'Date', 'Time', 'PatientName', 'DoctorName', 'AppointmentType', 'AppointmentStatus',
            'Arrival', 'Start', 'End', 'Cancelled', # Added time tracking and cancellation
            'BookingChannel', 'ReferralSource', # Added channel/source
            'ConfirmationStatus', 'ReminderType', 'AppointmentID'
        ]
        # Filter out columns that might not exist if the table schema changes or data is missing
        display_cols_exist = [col for col in display_cols if col in df_display.columns]
        st.dataframe(df_display[display_cols_exist], hide_index=True, use_container_width=True)

        st.divider()

        # --- Edit/Delete Section ---
        st.subheader("Edit or Delete Appointment")
        appointment_ids = df_appointments['AppointmentID'].tolist()
        selected_appointment_id = st.selectbox("Select Appointment to Modify", options=[""] + appointment_ids, format_func=lambda x: f"ID: ...{x[-6:]}" if x else "Select...", key="select_edit_delete")

        if selected_appointment_id:
            appointment_to_edit = df_appointments[df_appointments['AppointmentID'] == selected_appointment_id].iloc[0]

            # Convert potential NaT/None to appropriate values for inputs
            edit_date_val = appointment_to_edit['AppointmentDateTime'].date() if pd.notna(appointment_to_edit.get('AppointmentDateTime')) else None
            edit_time_val = appointment_to_edit['AppointmentDateTime'].time() if pd.notna(appointment_to_edit.get('AppointmentDateTime')) else None
            # Helper to safely convert stored time string (HH:MM:SS) back to time object, handling None/errors
            def safe_str_to_time(time_str):
                if isinstance(time_str, str):
                    try:
                        return time.fromisoformat(time_str)
                    except (ValueError, TypeError):
                        return None
                return None # Return None if not a string or other issue

            edit_arrival_time_val = safe_str_to_time(appointment_to_edit.get('PatientArrivalTime'))
            edit_start_time_val = safe_str_to_time(appointment_to_edit.get('AppointmentStartTime'))
            edit_end_time_val = safe_str_to_time(appointment_to_edit.get('AppointmentEndTime'))


            with st.form("edit_appointment_form"):
                st.write(f"Editing Appointment ID: {selected_appointment_id}")
                edit_col1, edit_col2, edit_col3 = st.columns(3) # Use 3 columns
                with edit_col1:
                    edit_patient_name = st.text_input("Patient Name*", value=appointment_to_edit.get('PatientName', ''), key="edit_patient_name")
                    edit_appointment_date = st.date_input("Appointment Date*", value=edit_date_val, key="edit_date")
                    edit_appointment_time = st.time_input("Appointment Time*", value=edit_time_val, key="edit_time")
                    edit_appointment_type = st.selectbox("Appointment Type", APPOINTMENT_TYPES, index=APPOINTMENT_TYPES.index(appointment_to_edit.get('AppointmentType')) if appointment_to_edit.get('AppointmentType') in APPOINTMENT_TYPES else 0, key="edit_type")
                    edit_appointment_status = st.selectbox("Appointment Status", APPOINTMENT_STATUSES, index=APPOINTMENT_STATUSES.index(appointment_to_edit.get('AppointmentStatus')) if appointment_to_edit.get('AppointmentStatus') in APPOINTMENT_STATUSES else 0, key="edit_status")

                with edit_col2:
                    edit_doctor_name = st.selectbox("Doctor Name*", distinct_doctors, index=distinct_doctors.index(appointment_to_edit.get('DoctorName')) if appointment_to_edit.get('DoctorName') in distinct_doctors else 0, key="edit_doctor_name")
                    # Use selectbox for booking channel and referral source in edit form
                    edit_booking_channel = st.selectbox("Booking Channel", BOOKING_CHANNELS, index=BOOKING_CHANNELS.index(appointment_to_edit.get('BookingChannel')) if appointment_to_edit.get('BookingChannel') in BOOKING_CHANNELS else 0, key="edit_booking_channel")
                    edit_referral_source = st.selectbox("Referral Source", REFERRAL_SOURCES, index=REFERRAL_SOURCES.index(appointment_to_edit.get('ReferralSource')) if appointment_to_edit.get('ReferralSource') in REFERRAL_SOURCES else 0, key="edit_referral_source")
                    edit_confirmation_status = st.selectbox("Confirmation Status", CONFIRMATION_STATUSES, index=CONFIRMATION_STATUSES.index(appointment_to_edit.get('ConfirmationStatus')) if appointment_to_edit.get('ConfirmationStatus') in CONFIRMATION_STATUSES else 0, key="edit_confirm_status")
                    edit_reminder_type = st.selectbox("Reminder Type", REMINDER_TYPES, index=REMINDER_TYPES.index(appointment_to_edit.get('ReminderType')) if appointment_to_edit.get('ReminderType') in REMINDER_TYPES else 0, key="edit_reminder_type")

                with edit_col3:
                    # Time Tracking Inputs
                    edit_patient_arrival_time = st.time_input("Patient Arrival Time", value=edit_arrival_time_val, key="edit_arrival_time")
                    edit_appointment_start_time = st.time_input("Appointment Start Time", value=edit_start_time_val, key="edit_start_time")
                    edit_appointment_end_time = st.time_input("Appointment End Time", value=edit_end_time_val, key="edit_end_time")
                    # Display Cancellation Time if it exists (read-only)
                    cancellation_time = appointment_to_edit.get('CancellationDateTime')
                    if pd.notna(cancellation_time):
                        st.text(f"Cancelled: {cancellation_time.strftime('%Y-%m-%d %H:%M')}")


                edit_submitted = st.form_submit_button("Update Appointment")
                if edit_submitted:
                    if not edit_patient_name or not edit_doctor_name or not edit_appointment_date or not edit_appointment_time:
                        st.error("Please fill in all required fields (*).")
                    else:
                        edit_appointment_datetime = combine_date_time(edit_appointment_date, edit_appointment_time)
                        if edit_appointment_datetime:
                            updates = {
                                "PatientName": edit_patient_name,
                                "DoctorName": edit_doctor_name,
                                "AppointmentDateTime": edit_appointment_datetime,
                                "AppointmentType": edit_appointment_type,
                                "AppointmentStatus": edit_appointment_status, # This will trigger cancellation time update in backend if 'Cancelled'
                                "ConfirmationStatus": edit_confirmation_status,
                                "ReminderType": edit_reminder_type,
                                "BookingChannel": edit_booking_channel, # Add new fields
                                "ReferralSource": edit_referral_source,
                                "PatientArrivalTime": edit_patient_arrival_time,
                                "AppointmentStartTime": edit_appointment_start_time,
                                "AppointmentEndTime": edit_appointment_end_time
                            }
                            # Remove None values so they don't overwrite existing data unintentionally if not provided in form
                            updates = {k: v for k, v in updates.items() if v is not None}

                            success = update_appointment(selected_appointment_id, updates)
                            if success:
                                st.success(f"Appointment {selected_appointment_id} updated successfully!")
                                st.rerun()
                            else:
                                st.error(f"Failed to update appointment {selected_appointment_id}.")
                        else:
                            st.error("Invalid date or time for update.")

            # Delete Button (outside the edit form)
            if st.button("Delete Selected Appointment", key="delete_button", type="primary"):
                if delete_appointment(selected_appointment_id):
                    st.success(f"Appointment {selected_appointment_id} deleted successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to delete appointment {selected_appointment_id}.")

# Example usage (if run directly)
# Example usage (if run directly - requires dummy data for df_financial_data)
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    # Create dummy financial data for direct execution testing
    dummy_financial_data = pd.DataFrame({
        'Doctor': ['Dr. Smith', 'Dr. Jones', 'Dr. Smith']
    })
    render_appointment_scheduling_tab(dummy_financial_data)
