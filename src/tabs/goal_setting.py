# src/tabs/goal_setting.py
import streamlit as st
import pandas as pd
from datetime import date, datetime
import sys
import os
import numpy as np # For mean calculation

# Add src directory to Python path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    # Import necessary functions from data_loader
    from data_loader import add_goal, get_goals, update_goal, get_costs, load_data
except ImportError as e:
    st.error(f"Could not import database functions from data_loader.py: {e}")
    st.stop()

# Define metrics available for goal setting
AVAILABLE_METRICS = [
    "Total Revenue",
    "Profit",
    "Total Visits",
    "Avg Revenue per Visit",
    "New Patient Count"
]

TIME_PERIODS = ["Monthly", "Quarterly", "Yearly", "Custom Range"]

# Helper function to calculate historical monthly average
# Uses st.cache_data for efficiency
@st.cache_data
def calculate_monthly_average(metric_name, df_all_data, df_all_costs):
    """Calculates the historical monthly average for a given metric."""
    try:
        df = df_all_data.copy()
        df['month_year'] = df['date'].dt.to_period('M')

        if metric_name == "Total Revenue":
            monthly_data = df.groupby('month_year')['gross income'].sum()
            return monthly_data.mean() if not monthly_data.empty else 0.0
        elif metric_name == "Profit":
            # Requires cost data - align costs to revenue data by month
            if df_all_costs.empty:
                st.warning("Cost data is needed to calculate average profit, but none found.")
                return 0.0
            df_costs = df_all_costs.copy()
            df_costs['expense_date'] = pd.to_datetime(df_costs['expense_date'])
            df_costs['month_year'] = df_costs['expense_date'].dt.to_period('M')
            monthly_costs = df_costs.groupby('month_year')['amount'].sum()
            monthly_revenue = df.groupby('month_year')['gross income'].sum()
            monthly_profit = monthly_revenue.subtract(monthly_costs, fill_value=0)
            return monthly_profit.mean() if not monthly_profit.empty else 0.0
        elif metric_name == "Total Visits":
            # Assuming one row per visit in df_all_data
            monthly_data = df.groupby('month_year').size()
            return monthly_data.mean() if not monthly_data.empty else 0.0
        elif metric_name == "Avg Revenue per Visit":
            monthly_revenue = df.groupby('month_year')['gross income'].sum()
            monthly_visits = df.groupby('month_year').size()
            # Avoid division by zero
            monthly_avg = monthly_revenue / monthly_visits.replace(0, np.nan)
            return monthly_avg.mean() if not monthly_avg.empty else 0.0
        elif metric_name == "New Patient Count":
            # This is harder to calculate a meaningful historical average for monthly goals
            # Maybe calculate avg new patients per month across the whole dataset?
            df['first_visit_date'] = df.groupby('Patient')['date'].transform('min')
            df['is_new'] = df['date'] == df['first_visit_date']
            monthly_new = df[df['is_new']].groupby('month_year').size()
            return monthly_new.mean() if not monthly_new.empty else 0.0
        else:
            return 0.0
    except Exception as e:
        st.error(f"Error calculating monthly average for {metric_name}: {e}")
        return 0.0

def render_goal_setting_tab():
    """Renders the goal setting form and table."""
    st.header("🎯 Goal Setting")
    st.markdown("Define and manage performance targets for the clinic.")

    # Load necessary data for average calculation
    try:
        df_all_data = load_data() # Use the main data loader
        df_all_costs = get_costs() # Get all costs
    except Exception as e:
        st.error(f"Failed to load data needed for goal setting: {e}")
        df_all_data = pd.DataFrame()
        df_all_costs = pd.DataFrame()


    with st.form("goal_setting_form", clear_on_submit=True):
        st.subheader("Define New Goal")
        col1, col2 = st.columns(2)

        with col1:
            metric_name = st.selectbox("Select Metric", options=AVAILABLE_METRICS)
            time_period = st.selectbox("Time Period", options=TIME_PERIODS)

            # Calculate suggested target if Monthly
            suggested_target = 0.0
            if time_period == "Monthly" and not df_all_data.empty:
                 suggested_target = calculate_monthly_average(metric_name, df_all_data, df_all_costs)

            target_value = st.number_input(
                "Target Value",
                min_value=0.0,
                value=suggested_target, # Pre-fill with average if monthly
                step=100.0,
                format="%.2f",
                help=f"Suggested monthly average: {suggested_target:,.2f}" if time_period == "Monthly" else None
            )


        with col2:
            start_date_custom = None
            end_date_custom = None
            if time_period == "Custom Range":
                start_date_custom = st.date_input("Start Date")
                end_date_custom = st.date_input("End Date")

            is_active = st.checkbox("Set as Active Goal", value=True)

        submitted = st.form_submit_button("Add Goal")

        if submitted:
            # Validation
            # Get the *actual* value entered by the user from the number_input widget
            user_entered_target = target_value # Assign the widget's current value
            if not metric_name:
                st.warning("Please select a metric.")
            elif user_entered_target <= 0: # Validate the user-entered value
                st.warning("Please enter a positive target value.")
            elif time_period == "Custom Range" and (not start_date_custom or not end_date_custom):
                st.warning("Please select both Start and End dates for Custom Range.")
            elif time_period == "Custom Range" and start_date_custom >= end_date_custom:
                st.warning("End Date must be after Start Date for Custom Range.")
            else:
                # Use the user_entered_target when adding the goal
                success = add_goal(
                    metric_name,
                    user_entered_target, # Use the value captured from the input
                    time_period,
                    start_date=start_date_custom,
                    end_date=end_date_custom,
                    is_active=1 if is_active else 0
                )
                if success:
                    st.success(f"Goal '{metric_name}' added successfully!")
                    # Clear cache for average calculation if data might change often
                    # calculate_monthly_average.clear() # Optional: uncomment if needed
                else:
                    st.error("Failed to add goal to the database.")

    st.divider()

    # Display existing goals
    st.subheader("Manage Existing Goals")
    try:
        df_goals = get_goals(active_only=False) # Get all goals

        if not df_goals.empty:
            # Prepare dataframe for display (using st.data_editor for potential edits)
            df_goals['is_active'] = df_goals['is_active'].astype(bool) # For checkbox
            # Format dates for display, handle NaT
            for col in ['start_date', 'end_date']:
                 if col in df_goals.columns:
                     df_goals[col] = pd.to_datetime(df_goals[col]).dt.strftime('%Y-%m-%d').replace('NaT', '')

            # Select and rename columns for clarity
            display_cols = {
                "id": "ID",
                "metric_name": "Metric",
                "target_value": "Target",
                "time_period": "Period",
                "start_date": "Start Date",
                "end_date": "End Date",
                "is_active": "Active",
                "created_at": "Created At"
            }
            df_display = df_goals[list(display_cols.keys())].rename(columns=display_cols)

            # Use st.data_editor to allow toggling 'Active' status
            edited_df = st.data_editor(
                df_display,
                key="goals_editor",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn(disabled=True),
                    "Metric": st.column_config.TextColumn(disabled=True),
                    "Target": st.column_config.NumberColumn(format="%.2f", disabled=True),
                    "Period": st.column_config.TextColumn(disabled=True),
                    "Start Date": st.column_config.TextColumn(disabled=True),
                    "End Date": st.column_config.TextColumn(disabled=True),
                    "Active": st.column_config.CheckboxColumn(default=True), # Allow editing active status
                    "Created At": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm", disabled=True)
                },
                num_rows="dynamic" # Allow deleting rows (future enhancement?)
            )

            # --- Logic to handle edits (specifically toggling active status) ---
            # Compare original df_goals with edited_df to find changes
            # Note: This requires careful comparison as data types might change via editor
            # For simplicity, we'll just focus on the 'Active' toggle for now.

            # Create a mapping from display df index to original goal ID
            original_ids = df_goals['id'].tolist()

            if st.button("Save Goal Status Changes"):
                changes_saved = 0
                errors = 0
                for i, edited_row in enumerate(edited_df.itertuples()):
                    original_goal_id = original_ids[i]
                    original_active_status = df_goals.loc[df_goals['id'] == original_goal_id, 'is_active'].iloc[0]
                    edited_active_status = edited_row.Active # Access by column name used in editor

                    if bool(original_active_status) != bool(edited_active_status):
                        success = update_goal(original_goal_id, {"is_active": 1 if edited_active_status else 0})
                        if success:
                            changes_saved += 1
                        else:
                            errors += 1
                if changes_saved > 0:
                    st.success(f"{changes_saved} goal status updates saved successfully!")
                    st.rerun() # Rerun to reflect changes immediately
                if errors > 0:
                    st.error(f"Failed to save {errors} goal status updates.")
                if changes_saved == 0 and errors == 0:
                     st.info("No changes detected in goal statuses.")


        else:
            st.info("No goals defined yet. Use the form above to add one.")

    except Exception as e:
        st.error(f"An error occurred while fetching or displaying goals: {e}")
        st.exception(e) # Show traceback for debugging
