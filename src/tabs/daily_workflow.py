# src/tabs/daily_workflow.py
import streamlit as st
import pandas as pd
from datetime import datetime, date, time

# Import database functions from data_loader
try:
    # Use relative import if data_loader is in the parent directory
    from ..data_loader import get_appointments, update_appointment, get_distinct_doctors
except ImportError:
    from data_loader import get_appointments, update_appointment, get_distinct_doctors

# Define appointment statuses constant here as well, adding the new status
APPOINTMENT_STATUSES = ["Scheduled", "Confirmed", "Checked-in", "Appointment Started", "Completed", "Cancelled", "No-Show"]
# Define custom sort order for statuses (Lower numbers appear first)
STATUS_SORT_ORDER = {
    "Appointment Started": 0,
    "Checked-in": 1,
    "Scheduled": 2,
    "Confirmed": 3,
    "Completed": 4,
    "Cancelled": 5,
    "No-Show": 6
}


def render_daily_workflow_tab(df_financial_data): # df_financial_data is needed for doctor filter
    """Renders the Daily Workflow tab for managing today's appointments."""
    st.header(f"⏱️ Daily Workflow - {date.today().strftime('%Y-%m-%d')}")

    today = date.today()

    # --- Fetch all of today's appointments first to determine doctors and counts ---
    df_all_today = get_appointments(start_date_filter=today, end_date_filter=today)

    if df_all_today.empty:
        st.info("No appointments scheduled for today.")
        return

    # --- Display Status Counts ---
    st.subheader("Today's Summary")
    status_counts = df_all_today['AppointmentStatus'].value_counts()
    # Ensure all statuses are represented, even if count is 0
    status_metrics = {status: status_counts.get(status, 0) for status in APPOINTMENT_STATUSES}
    cols_counts = st.columns(len(status_metrics))
    for i, (status_name, count) in enumerate(status_metrics.items()):
         with cols_counts[i]:
            st.metric(label=status_name, value=count)
    st.divider()


    # --- Add Filters & Sorting ---
    st.subheader("Filters & Sorting")
    # Get distinct doctors *only from today's appointments*
    doctors_today = sorted(df_all_today['DoctorName'].dropna().unique().tolist())
    if not doctors_today:
        st.warning("No doctors found in today's appointments.")
        doctors_today = []

    filter_col1, filter_col2, sort_col = st.columns(3) # Add column for sorting
    with filter_col1:
        # Use the filtered list of doctors for the dropdown
        filter_doctor = st.selectbox("Filter by Doctor", ["All"] + doctors_today, key="workflow_filter_doctor")
    with filter_col2:
        filter_status = st.selectbox("Filter by Status", ["All"] + APPOINTMENT_STATUSES, key="workflow_filter_status")
    with sort_col:
        # Add sorting dropdown
        sort_by = st.selectbox(
            "Sort by",
            ["Status (Default)", "Time", "Doctor"],
            key="workflow_sort"
        )

    # --- Apply Filters to the DataFrame ---
    df_today_filtered = df_all_today.copy()
    if filter_doctor != "All":
        df_today_filtered = df_today_filtered[df_today_filtered['DoctorName'] == filter_doctor]
    if filter_status != "All":
        df_today_filtered = df_today_filtered[df_today_filtered['AppointmentStatus'] == filter_status]


    if df_today_filtered.empty:
        st.info("No appointments found matching the filter criteria for today.")
        return

    # --- Apply Sorting ---
    if sort_by == "Status (Default)":
        # Custom sort by status order, then by time
        df_today_filtered['status_sort_key'] = df_today_filtered['AppointmentStatus'].map(STATUS_SORT_ORDER).fillna(99) # Handle potential missing statuses
        df_today_filtered = df_today_filtered.sort_values(by=['status_sort_key', 'AppointmentDateTime'])
    elif sort_by == "Doctor":
        df_today_filtered = df_today_filtered.sort_values(by=['DoctorName', 'AppointmentDateTime'])
    else: # Default to Time
        df_today_filtered = df_today_filtered.sort_values(by='AppointmentDateTime')


    st.info("Click buttons to update appointment status and record times.")

    # Display appointments and action buttons (iterate over the filtered DataFrame)
    for index, appointment in df_today_filtered.iterrows():
        appt_id = appointment['AppointmentID']
        appt_time_str = appointment['AppointmentDateTime'].strftime('%H:%M')
        status = appointment.get('AppointmentStatus', 'Scheduled') # Default if missing
        appt_type = appointment.get('AppointmentType', 'N/A')

        # Use a container with a border for each appointment
        with st.container(border=True):
            # Adjust column ratios for better spacing
            col1, col2, col3 = st.columns([2.5, 3.5, 4])

            with col1:
                # Larger time, slightly different color
                st.markdown(f"<span style='font-size: 1.7em; '>{appt_time_str}</span>", unsafe_allow_html=True)
                # Status with color coding and formatting
                status_color = "inherit" # Default color
                status_style = "normal" # Default style
                status_prefix = ""
                status_weight = "normal"

                if status == 'Completed':
                    status_color = "green"
                    status_prefix = "✅ "
                    status_weight = "bold"
                elif status == 'Cancelled' or status == 'No-Show':
                    status_color = "red"
                    status_prefix = "❌ "
                    status_style = "italic"
                elif status == 'Appointment Started':
                    status_color = "yellow" # Changed to yellow
                    status_prefix = "🚀 "
                    status_weight = "bold"
                elif status == 'Checked-in':
                    status_color = "orange" # Keep orange for Checked-in
                    status_prefix = "▶️ "
                    status_weight = "bold"
                elif status == 'Confirmed':
                     status_color = "#666" # Grey
                     status_prefix = "👍 "
                elif status == 'Scheduled':
                     status_color = "#AAA" # Lighter Grey
                     status_prefix = "🗓️ "
                     status_weight = "bold" # Make Scheduled bold

                st.markdown(f"<span style='color: {status_color}; font-weight: {status_weight}; font-style: {status_style};'>{status_prefix}{status}</span>", unsafe_allow_html=True)


            with col2:
                # Display Patient, Doctor, Type with enhanced styling and icons
                st.markdown(
                    f"""
                    <div style='line-height: 120%; padding: 8px;'>
                        <p style='font-size: 1.2em; font-weight: bold; margin-bottom: 1.3em; '>
                            👤 {appointment.get('PatientName', 'N/A')}
                        </p>
                        <p style='margin-bottom: 1.3em; font-size: 1.2em; '>
                            🩺 Dr. {appointment.get('DoctorName', 'N/A')}
                        </p>
                        <p style='margin-bottom: 0; font-size: 1em; border-radius: 6px; display: inline-block;'>
                            🏥 {appt_type}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                # st.caption(f"ID: ...{appt_id[-6:]}") # Optional: Hide ID


            with col3:
                # --- Action Buttons --- Corrected Indentation Starts Here ---
                button_key_prefix = f"btn_{appt_id}" # Unique key prefix for buttons
                start_time_recorded = pd.notna(appointment.get('AppointmentStartTime'))
                end_time_recorded = pd.notna(appointment.get('AppointmentEndTime'))

                # Use nested columns for button layout
                btn_col1, btn_col2 = st.columns(2)

                with btn_col1: # Primary workflow button
                    action_button_displayed = False
                    # 1. Patient Arrived
                    if status in ['Scheduled', 'Confirmed'] and not action_button_displayed:
                        if st.button("Patient Arrived", key=f"{button_key_prefix}_arrived", use_container_width=True):
                            now = datetime.now().time()
                            updates = {"PatientArrivalTime": now, "AppointmentStatus": "Checked-in"}
                            if update_appointment(appt_id, updates):
                                st.success(f"Patient arrival time recorded for {appointment.get('PatientName', '')}.")
                                st.rerun()
                            else:
                                st.error("Failed to update arrival time.")
                        action_button_displayed = True

                    # 2. Start Appointment -> Sets status to "Appointment Started"
                    if status == 'Checked-in' and not start_time_recorded and not action_button_displayed:
                        if st.button("Start Appointment", key=f"{button_key_prefix}_start", use_container_width=True):
                            now = datetime.now().time()
                            updates = {"AppointmentStartTime": now, "AppointmentStatus": "Appointment Started"} # New Status
                            if pd.isna(appointment.get('PatientArrivalTime')):
                                 updates["PatientArrivalTime"] = now # Record arrival if missed
                            if update_appointment(appt_id, updates):
                                st.success(f"Appointment started for {appointment.get('PatientName', '')}.")
                                st.rerun()
                            else:
                                st.error("Failed to update start time.")
                        action_button_displayed = True

                    # 3. End Appointment -> Triggers from "Appointment Started"
                    # Corrected condition: Should appear when status is 'Appointment Started'
                    if status == 'Appointment Started' and not end_time_recorded and not action_button_displayed:
                         if st.button("End Appointment", key=f"{button_key_prefix}_end", use_container_width=True):
                            now = datetime.now().time()
                            updates = {"AppointmentEndTime": now, "AppointmentStatus": "Completed"}
                            if update_appointment(appt_id, updates):
                                st.success(f"Appointment completed for {appointment.get('PatientName', '')}.")
                                st.rerun()
                            else:
                                st.error("Failed to update end time.")
                         action_button_displayed = True

                with btn_col2: # Secondary actions
                    # Button: Mark No-Show
                    if status in ['Scheduled', 'Confirmed']:
                         if st.button("No-Show", key=f"{button_key_prefix}_noshow", type="secondary", use_container_width=True):
                            updates = {"AppointmentStatus": "No-Show"}
                            if update_appointment(appt_id, updates):
                                st.warning(f"Appointment marked as No-Show for {appointment.get('PatientName', '')}.")
                                st.rerun()
                            else:
                                st.error("Failed to mark as No-Show.")

                    # Button: Cancel Appointment
                    if status not in ['Completed', 'Cancelled', 'No-Show']:
                         if st.button("Cancel", key=f"{button_key_prefix}_cancel", type="primary", use_container_width=True):
                            updates = {"AppointmentStatus": "Cancelled"} # Backend handles timestamp
                            if update_appointment(appt_id, updates):
                                st.error(f"Appointment Cancelled for {appointment.get('PatientName', '')}.")
                                st.rerun()
                            else:
                                st.error("Failed to cancel appointment.")

                # Display recorded times as metrics below buttons
                st.write("---") # Small separator
                metric_cols = st.columns(4) # Create 4 columns for metrics

                # Helper to format time string HH:MM:SS to HH:MM
                def format_hhmm(time_str):
                    try:
                        return time.fromisoformat(time_str).strftime('%H:%M')
                    except (TypeError, ValueError):
                        return "--:--" # Return placeholder if invalid

                arrival_time_str = format_hhmm(appointment.get('PatientArrivalTime'))
                start_time_str = format_hhmm(appointment.get('AppointmentStartTime'))
                end_time_str = format_hhmm(appointment.get('AppointmentEndTime'))
                duration_display = "--" # Default duration

                # Calculate duration
                if start_time_recorded and end_time_recorded:
                    try:
                        start_dt = datetime.combine(today, time.fromisoformat(appointment['AppointmentStartTime']))
                        end_dt = datetime.combine(today, time.fromisoformat(appointment['AppointmentEndTime']))
                        duration = end_dt - start_dt
                        duration_total_seconds = duration.total_seconds()
                        if duration_total_seconds < 0:
                            duration_display = "Invalid"
                        elif duration_total_seconds < 60:
                            duration_display = "< 1 min"
                        else:
                            duration_mins = int(duration_total_seconds / 60)
                            duration_display = f"{duration_mins} min"
                    except (TypeError, ValueError):
                        duration_display = "Error"

                # Display metrics only if relevant data exists
                with metric_cols[0]:
                    if pd.notna(appointment.get('PatientArrivalTime')):
                        st.metric("Arrived", arrival_time_str)
                    elif status == 'Cancelled' and pd.notna(appointment.get('CancellationDateTime')):
                         st.metric("Cancelled", appointment['CancellationDateTime'].strftime('%H:%M'))

                with metric_cols[1]:
                     if start_time_recorded:
                         st.metric("Started", start_time_str)

                with metric_cols[2]:
                     if end_time_recorded:
                         st.metric("Ended", end_time_str)

    st.set_page_config(layout="wide")
    # Requires dummy financial data if get_distinct_doctors needs it
    dummy_financial_data = pd.DataFrame({'Doctor': []})
    render_daily_workflow_tab(dummy_financial_data)
