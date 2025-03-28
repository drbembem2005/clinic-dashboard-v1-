# src/sidebar.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def render_sidebar(df_data):
    """
    Renders the sidebar filters and returns the filtered DataFrame and filter details.

    Args:
        df_data (pd.DataFrame): The original DataFrame.

    Returns:
        tuple: Contains the filtered DataFrame and a dictionary of filter details.
               (filtered_df, filter_details)
    """
    st.sidebar.header("🔍 Dashboard Filters")
    st.sidebar.divider()

    # Create filter container for better organization
    filter_container = st.sidebar.container()

    with filter_container:
        # Date range filter with presets
        with st.expander("📅 Date Range", expanded=True):
            date_preset = st.selectbox(
                "Quick Select",
                ["Custom", "Last 7 Days", "Last 30 Days", "Last 90 Days", "Year to Date", "All Time"],
                key="date_preset_select" # Added key
            )

            min_date_allowed = df_data["date"].min().date()
            max_date_allowed = df_data["date"].max().date()

            if date_preset == "Custom":
                date_range = st.date_input(
                    "Select Date Range",
                    value=(min_date_allowed, max_date_allowed),
                    min_value=min_date_allowed,
                    max_value=max_date_allowed,
                    key="custom_date_range" # Added key
                )
                if len(date_range) == 2:
                    start_date, end_date = date_range
                else: # Handle case where user might clear the input
                    start_date, end_date = min_date_allowed, max_date_allowed
            else:
                end_date = max_date_allowed
                if date_preset == "Last 7 Days":
                    start_date = max(end_date - timedelta(days=6), min_date_allowed) # Corrected logic for last 7 days inclusive
                elif date_preset == "Last 30 Days":
                    start_date = max(end_date - timedelta(days=29), min_date_allowed) # Corrected logic
                elif date_preset == "Last 90 Days":
                    start_date = max(end_date - timedelta(days=89), min_date_allowed) # Corrected logic
                elif date_preset == "Year to Date":
                    start_date = max(datetime(end_date.year, 1, 1).date(), min_date_allowed)
                else:  # All Time
                    start_date = min_date_allowed

            # Ensure start_date is not after end_date
            if start_date > end_date:
                start_date = end_date

            filtered_df = df_data[(df_data["date"].dt.date >= start_date) &
                                 (df_data["date"].dt.date <= end_date)].copy() # Use .copy()

        # Doctor filter with search
        with st.expander("👨‍⚕️ Doctors", expanded=True):
            doctor_search = st.text_input("Search Doctors", "", key="doctor_search_input")
            # Filter available doctors based on the *original* dataframe first
            available_doctors_all = sorted(df_data["Doctor"].unique())
            available_doctors = [d for d in available_doctors_all if doctor_search.lower() in d.lower()]

            all_doctors = st.checkbox("All Doctors", value=True, key="all_doctors_checkbox")
            if all_doctors or not available_doctors: # Handle empty search result
                selected_doctors = available_doctors
            else:
                # Use available_doctors for options, default to first 5 or all if less than 5
                default_selection = available_doctors[:min(5, len(available_doctors))]
                selected_doctors = st.multiselect(
                    "Select Doctors",
                    options=available_doctors,
                    default=default_selection,
                    key="doctor_multiselect"
                )
            # Apply doctor filter to the already date-filtered dataframe
            if selected_doctors:
                filtered_df = filtered_df[filtered_df["Doctor"].isin(selected_doctors)]
            else: # If no doctors selected (e.g., search yields nothing and 'All' unchecked)
                 filtered_df = filtered_df.iloc[0:0] # Return empty dataframe

        # Visit type filter with grouping
        with st.expander("🩺 Visit Types", expanded=True):
            # Get unique visit types from the original dataframe
            all_visit_types_unique = sorted(df_data["visit type"].unique())
            visit_categories = {
                "All": all_visit_types_unique,
                "Regular": [vt for vt in all_visit_types_unique if "regular" in vt.lower()],
                "Special": [vt for vt in all_visit_types_unique if "special" in vt.lower()],
                "Emergency": [vt for vt in all_visit_types_unique if "emergency" in vt.lower()]
            }
            # Filter out categories with no visit types
            visit_categories = {k: v for k, v in visit_categories.items() if v}

            if not visit_categories: # Handle case where no visit types exist
                 selected_visit_types = []
                 st.warning("No visit types found in the data.")
            else:
                visit_category = st.selectbox("Visit Category",
                                        list(visit_categories.keys()),
                                        key="visit_category_select")

                if visit_category == "All":
                    all_visit_types_selected = st.checkbox("All Visit Types",
                                                    value=True,
                                                    key="all_visit_types_checkbox")
                    if all_visit_types_selected:
                        selected_visit_types = all_visit_types_unique
                    else:
                        default_vtypes = all_visit_types_unique[:min(5, len(all_visit_types_unique))]
                        selected_visit_types = st.multiselect(
                            "Select Visit Types",
                            options=all_visit_types_unique,
                            default=default_vtypes,
                            key="visit_type_multiselect"
                        )
                else:
                    selected_visit_types = visit_categories[visit_category]

            # Apply visit type filter
            if selected_visit_types:
                filtered_df = filtered_df[filtered_df["visit type"].isin(selected_visit_types)]
            else:
                 filtered_df = filtered_df.iloc[0:0] # Return empty dataframe

        # Enhanced payment method filter
        with st.expander("💰 Payment Methods", expanded=True):
            # Display stats based on currently filtered data *before* applying payment filter
            if not filtered_df.empty:
                 payment_stats = filtered_df.groupby("payment_method").agg(
                     Total_Revenue=("gross income", "sum"),
                     Transaction_Count=("id", "count") # Use 'id' or another unique identifier
                 ).round(2)
                 # payment_stats.columns = ["Total Revenue", "Transaction Count"] # Renamed in agg
                 st.dataframe(payment_stats, use_container_width=True)
            else:
                 st.info("No data matches current filters to show payment stats.")

            all_payment_methods_selected = st.checkbox("All Payment Methods",
                                                value=True,
                                                key="all_payment_methods_checkbox")

            available_payment_methods = sorted(df_data['payment_method'].unique())
            selected_payment_methods = []

            if all_payment_methods_selected:
                selected_payment_methods = available_payment_methods
            else:
                # Dynamically create checkboxes for available methods
                cols = st.columns(len(available_payment_methods))
                for i, method in enumerate(available_payment_methods):
                    with cols[i]:
                        if st.checkbox(method, value=True, key=f"payment_{method}_checkbox"):
                            selected_payment_methods.append(method)

            # Apply payment method filter
            if selected_payment_methods:
                 filtered_df = filtered_df[filtered_df["payment_method"].isin(selected_payment_methods)]
            else:
                 filtered_df = filtered_df.iloc[0:0] # Return empty dataframe

        # Advanced filters
        with st.expander("🔍 Advanced Filters", expanded=False):
            # Revenue range filter
            st.subheader("Revenue Range")
            min_val_rev = float(df_data["gross income"].min())
            max_val_rev = float(df_data["gross income"].max())
            # Ensure min <= max, handle case where min == max
            if min_val_rev > max_val_rev:
                min_val_rev, max_val_rev = max_val_rev, min_val_rev
            elif min_val_rev == max_val_rev:
                 max_val_rev += 1 # Add a small amount to allow slider range

            min_income, max_income = st.slider(
                "Gross Income Range",
                min_value=min_val_rev,
                max_value=max_val_rev,
                value=(min_val_rev, max_val_rev),
                step=max(10.0, (max_val_rev - min_val_rev) / 100), # Dynamic step
                format="EGP%.2f",
                key="income_slider" # Added key
            )
            filtered_df = filtered_df[(filtered_df["gross income"] >= min_income) &
                                     (filtered_df["gross income"] <= max_income)]

            # Visit duration filter
            st.subheader("Visit Duration")
            min_val_dur = int(df_data["visit_duration_mins"].min())
            max_val_dur = int(df_data["visit_duration_mins"].max())
            if min_val_dur > max_val_dur:
                 min_val_dur, max_val_dur = max_val_dur, min_val_dur
            elif min_val_dur == max_val_dur:
                 max_val_dur += 1

            min_duration, max_duration = st.slider(
                "Visit Duration (minutes)",
                min_value=min_val_dur,
                max_value=max_val_dur,
                value=(min_val_dur, max_val_dur),
                key="duration_slider" # Added key
            )
            filtered_df = filtered_df[(filtered_df["visit_duration_mins"] >= min_duration) &
                                     (filtered_df["visit_duration_mins"] <= max_duration)]

            # Time of day filter
            st.subheader("Time of Day")
            hours = st.slider(
                "Hour Range",
                min_value=0,
                max_value=23,
                value=(0, 23),
                key="hour_slider" # Added key
            )
            filtered_df = filtered_df[(filtered_df["hour"] >= hours[0]) &
                                     (filtered_df["hour"] <= hours[1])]

    # Display filter summary
    st.sidebar.divider()
    with st.sidebar.expander("📊 Current Filter Summary", expanded=True):
        st.markdown(f"**📅 Date Range:** {start_date} to {end_date}")
        st.markdown(f"**👨‍⚕️ Doctors:** {len(selected_doctors)} selected")
        st.markdown(f"**🩺 Visit Types:** {len(selected_visit_types)} selected")
        st.markdown(f"**💰 Payment Methods:** {len(selected_payment_methods)} selected")

        total_records = len(df_data)
        filtered_records = len(filtered_df)
        percentage = (filtered_records / total_records * 100) if total_records > 0 else 0
        st.markdown(f"**📈 Filtered Records:** {filtered_records:,} of {total_records:,} ({percentage:.1f}%)")

        # Quick stats based on filtered data
        st.divider()
        st.markdown("### 📊 Quick Stats")
        if not filtered_df.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Revenue", f"EGP{filtered_df['gross income'].sum():,.2f}")
                st.metric("Unique Patients", f"{filtered_df['Patient'].nunique():,}")
            with col2:
                st.metric("Total Visits", f"{len(filtered_df):,}")
                st.metric("Avg Revenue/Visit", f"EGP{filtered_df['gross income'].mean():,.2f}")
        else:
            st.info("No data matches the current filters.")

    filter_details = {
        "start_date": start_date,
        "end_date": end_date,
        "selected_doctors": selected_doctors,
        "selected_visit_types": selected_visit_types,
        "selected_payment_methods": selected_payment_methods
    }

    return filtered_df, filter_details
