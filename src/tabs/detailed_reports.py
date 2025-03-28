# src/tabs/detailed_reports.py
import streamlit as st
import pandas as pd
import numpy as np # Added numpy
import io # For Excel export

def render_detailed_reports_tab(filtered_df, start_date, end_date):
    """
    Renders the Detailed Reports tab content.

    Args:
        filtered_df (pd.DataFrame): The filtered DataFrame based on sidebar selections.
        start_date (datetime.date): The start date from the filter.
        end_date (datetime.date): The end date from the filter.
    """
    st.header("Detailed Reports")

    # Report Type Selection
    report_type = st.selectbox(
        "Select Report Type",
        options=[
            "Financial Summary",
            "Doctor Performance",
            "Patient Analytics",
            "Operational Metrics",
            "Raw Data Export", # Added Raw Data option
            "Custom Report"
        ],
        key="report_type_select"
    )

    # Get min and max dates from the already filtered_df for the report range selector
    # This ensures the report range is within the main filter range
    min_date_report = filtered_df["date"].dt.date.min() if not filtered_df.empty else start_date
    max_date_report = filtered_df["date"].dt.date.max() if not filtered_df.empty else end_date

    # Date Range for Report (defaulting to the filtered range)
    report_date_range = st.date_input(
        "Select Report Date Range (within filtered period)",
        value=(min_date_report, max_date_report),
        min_value=min_date_report,
        max_value=max_date_report,
        key="report_date_input"
    )

    report_df = filtered_df # Start with the main filtered data
    report_start = start_date
    report_end = end_date

    if len(report_date_range) == 2:
        report_start, report_end = report_date_range
        # Further filter the report_df based on the report-specific date range
        report_df = report_df[
            (report_df["date"].dt.date >= report_start) &
            (report_df["date"].dt.date <= report_end)
        ].copy() # Use copy to avoid SettingWithCopyWarning

    st.divider()

    # --- Generate Report Based on Selection ---
    display_df = pd.DataFrame() # Initialize dataframe for display and export

    if report_df.empty:
        st.warning("No data available for the selected report criteria.")
        # Still allow export of empty structure if needed, or just return
        # return
    elif report_type == "Financial Summary":
        st.subheader("📊 Financial Summary Report")

        # Financial Overview Metrics
        total_revenue_rep = report_df["gross income"].sum()
        total_profit_rep = report_df["profit"].sum()
        total_commission_rep = report_df["total_commission"].sum()
        avg_revenue_visit_rep = report_df["gross income"].mean()
        profit_margin_rep = (total_profit_rep / total_revenue_rep * 100) if total_revenue_rep > 0 else 0
        cash_sum = report_df["cash pay"].sum()
        visa_sum = report_df["visa pay"].sum()
        total_paid_rep = cash_sum + visa_sum
        cash_ratio_rep = (cash_sum / total_paid_rep * 100) if total_paid_rep > 0 else 0

        fin_metrics = {
            "Total Revenue": total_revenue_rep,
            "Total Profit": total_profit_rep,
            "Total Commission": total_commission_rep,
            "Average Revenue per Visit": avg_revenue_visit_rep,
            "Profit Margin (%)": profit_margin_rep,
            "Cash Payment Ratio (%)": cash_ratio_rep
        }
        fin_summary_df = pd.DataFrame(fin_metrics.items(), columns=["Metric", "Value"])
        st.dataframe(
            fin_summary_df.style.format({"Value": "{:,.2f}"}), # Apply formatting
            hide_index=True,
            use_container_width=True
        )
        display_df = fin_summary_df # For potential export

        # Daily Breakdown Table
        st.subheader("Daily Financial Breakdown")
        daily_breakdown = report_df.groupby(report_df["date"].dt.date).agg(
            Revenue=('gross income', 'sum'),
            Profit=('profit', 'sum'),
            Commission=('total_commission', 'sum'),
            Visits=('id', 'count')
        ).reset_index()
        daily_breakdown.columns = ["Date", "Revenue", "Profit", "Commission", "Visits"]
        st.dataframe(
            daily_breakdown,
            column_config={
                "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                "Revenue": st.column_config.NumberColumn("Revenue", format="EGP %.2f"),
                "Profit": st.column_config.NumberColumn("Profit", format="EGP %.2f"),
                "Commission": st.column_config.NumberColumn("Commission", format="EGP %.2f"),
                "Visits": st.column_config.NumberColumn("Visits", format="%d")
            },
            use_container_width=True
        )
        # display_df = daily_breakdown # Or combine/choose which to export

    elif report_type == "Doctor Performance":
        st.subheader("👨‍⚕️ Doctor Performance Report")

        # Aggregate performance by doctor
        doc_report = report_df.groupby('Doctor').agg(
            Total_Revenue=('gross income', 'sum'),
            Total_Patients=('Patient', 'nunique'),
            Total_Visits=('id', 'count'),
            Total_Commission=('total_commission', 'sum'),
            Avg_Visit_Duration=('visit_duration_mins', 'mean')
        ).reset_index()

        # Calculate derived metrics
        doc_report['Avg_Revenue_per_Visit'] = (doc_report['Total_Revenue'] / doc_report['Total_Visits']).fillna(0)
        doc_report['Commission_Rate (%)'] = (doc_report['Total_Commission'] / doc_report['Total_Revenue'] * 100).fillna(0)

        # Reorder columns for better readability
        doc_report = doc_report[[
            'Doctor', 'Total_Revenue', 'Total_Visits', 'Total_Patients',
            'Avg_Revenue_per_Visit', 'Total_Commission', 'Commission_Rate (%)',
            'Avg_Visit_Duration'
        ]].sort_values('Total_Revenue', ascending=False)

        st.dataframe(
            doc_report,
            column_config={
                "Total_Revenue": st.column_config.NumberColumn("Total Revenue", format="EGP %.2f"),
                "Total_Visits": st.column_config.NumberColumn("Total Visits", format="%d"),
                "Total_Patients": st.column_config.NumberColumn("Unique Patients", format="%d"),
                "Avg_Revenue_per_Visit": st.column_config.NumberColumn("Avg Revenue/Visit", format="EGP %.2f"),
                "Total_Commission": st.column_config.NumberColumn("Total Commission", format="EGP %.2f"),
                "Commission_Rate (%)": st.column_config.NumberColumn("Commission Rate", format="%.1f%%"),
                "Avg_Visit_Duration": st.column_config.NumberColumn("Avg Duration (mins)", format="%.1f")
            },
            use_container_width=True
        )
        display_df = doc_report

    elif report_type == "Patient Analytics":
        st.subheader("👥 Patient Analytics Report")

        # Aggregate metrics by patient
        patient_report = report_df.groupby("Patient").agg(
            Total_Visits=('id', 'count'),
            Total_Revenue=('gross income', 'sum'),
            First_Visit=('date', 'min'),
            Last_Visit=('date', 'max'),
            Avg_Visit_Duration=('visit_duration_mins', 'mean')
        ).reset_index()

        # Calculate derived metrics
        patient_report['Avg_Revenue_per_Visit'] = (patient_report['Total_Revenue'] / patient_report['Total_Visits']).fillna(0)
        patient_report['Days_Since_Last_Visit'] = (pd.to_datetime(report_end) - patient_report['Last_Visit']).dt.days

        # Reorder columns
        patient_report = patient_report[[
            'Patient', 'Total_Visits', 'Total_Revenue', 'Avg_Revenue_per_Visit',
            'First_Visit', 'Last_Visit', 'Days_Since_Last_Visit', 'Avg_Visit_Duration'
        ]].sort_values('Total_Revenue', ascending=False)

        st.dataframe(
            patient_report,
            column_config={
                "Total_Visits": st.column_config.NumberColumn("Total Visits", format="%d"),
                "Total_Revenue": st.column_config.NumberColumn("Total Revenue", format="EGP %.2f"),
                "Avg_Revenue_per_Visit": st.column_config.NumberColumn("Avg Revenue/Visit", format="EGP %.2f"),
                "First_Visit": st.column_config.DateColumn("First Visit", format="YYYY-MM-DD"),
                "Last_Visit": st.column_config.DateColumn("Last Visit", format="YYYY-MM-DD"),
                "Days_Since_Last_Visit": st.column_config.NumberColumn("Days Since Last Visit", format="%d"),
                "Avg_Visit_Duration": st.column_config.NumberColumn("Avg Duration (mins)", format="%.1f")
            },
            use_container_width=True
        )
        display_df = patient_report

    elif report_type == "Operational Metrics":
        st.subheader("⚡ Operational Metrics Report")

        # Aggregate operational metrics
        total_visits_rep = len(report_df)
        days_count_rep = (report_end - report_start).days + 1
        avg_daily_visits_rep = total_visits_rep / days_count_rep if days_count_rep > 0 else 0
        avg_duration_rep = report_df["visit_duration_mins"].mean()
        peak_hour_rep = report_df.groupby("hour")["id"].count().idxmax() if not report_df.empty else 'N/A'
        busiest_day_rep = report_df.groupby("day_of_week")["id"].count().idxmax() if not report_df.empty else 'N/A'

        op_metrics = {
            "Total Visits": total_visits_rep,
            "Average Daily Visits": avg_daily_visits_rep,
            "Average Visit Duration (mins)": avg_duration_rep,
            "Peak Hour": f"{peak_hour_rep:02d}:00" if isinstance(peak_hour_rep, (int, np.integer)) else peak_hour_rep,
            "Busiest Day of Week": busiest_day_rep
        }
        op_summary_df = pd.DataFrame(op_metrics.items(), columns=["Metric", "Value"])
        st.dataframe(
            op_summary_df.style.format({"Value": "{:,.1f}"}, subset=pd.IndexSlice[op_summary_df['Metric'].isin(["Average Daily Visits", "Average Visit Duration (mins)"]), 'Value']),
            hide_index=True,
            use_container_width=True
        )
        display_df = op_summary_df

        # Hourly Distribution Table
        st.subheader("Hourly Visit Distribution")
        hourly_dist_rep = report_df.groupby("hour")["id"].count().reset_index()
        hourly_dist_rep.columns = ["Hour", "Visit Count"]
        st.dataframe(hourly_dist_rep, hide_index=True, use_container_width=True)
        # display_df = hourly_dist_rep # Or combine

    elif report_type == "Raw Data Export":
         st.subheader("📋 Raw Data Export")
         st.info(f"Displaying the first 100 rows of the filtered data for the period {report_start} to {report_end}.")
         st.dataframe(report_df.head(100)) # Show a preview
         display_df = report_df # Set the full report_df for export

    elif report_type == "Custom Report":
        st.subheader("🔍 Custom Report Builder")

        # Select Metrics
        available_metrics = report_df.select_dtypes(include=np.number).columns.tolist()
        # Add common non-numeric aggregations if needed
        available_metrics.extend(['id', 'Patient']) # For count/nunique

        selected_metrics = st.multiselect(
            "Select Metrics/Columns",
            options=report_df.columns.tolist(), # Allow selecting any column
            default=["gross income", "id", "profit"] # Sensible defaults
        )

        # Select Grouping
        grouping_cols = st.multiselect(
            "Group By (Optional)",
            options=[col for col in report_df.columns if col not in selected_metrics], # Exclude selected metrics from grouping
            default=["Doctor"]
        )

        # Select Aggregation Functions
        agg_funcs = {}
        if grouping_cols: # Only ask for aggregation if grouping
            st.write("Select Aggregation for Numeric Metrics:")
            default_agg = 'sum'
            for metric in report_df[selected_metrics].select_dtypes(include=np.number).columns:
                 agg_choice = st.selectbox(f"Aggregation for '{metric}':",
                                           options=['sum', 'mean', 'median', 'min', 'max', 'count', 'nunique'],
                                           index=0, # Default to 'sum'
                                           key=f"agg_{metric}")
                 agg_funcs[metric] = agg_choice
            # Handle non-numeric differently if needed (e.g., count, nunique)
            for metric in report_df[selected_metrics].select_dtypes(exclude=np.number).columns:
                 agg_choice = st.selectbox(f"Aggregation for '{metric}':",
                                           options=['count', 'nunique', 'first', 'last'], # Sensible options for non-numeric
                                           index=0, # Default to 'count'
                                           key=f"agg_{metric}")
                 agg_funcs[metric] = agg_choice

        # Generate Custom Report
        try:
            if grouping_cols and agg_funcs:
                custom_report = report_df.groupby(grouping_cols).agg(agg_funcs).reset_index()
            elif not grouping_cols: # No grouping, just select columns
                 custom_report = report_df[selected_metrics]
            else: # Grouping but no aggregations selected (show first entry per group?)
                 custom_report = report_df.groupby(grouping_cols).first().reset_index()[grouping_cols + selected_metrics]

            st.dataframe(custom_report, use_container_width=True)
            display_df = custom_report
        except Exception as e:
            st.error(f"Error generating custom report: {e}")
            st.info("Ensure selected aggregations are valid for the chosen metrics.")
            display_df = pd.DataFrame() # Ensure display_df is empty on error


    # --- Export Options ---
    if not display_df.empty:
        st.divider()
        st.subheader("📥 Export Options")

        export_col1, export_col2 = st.columns(2)
        file_prefix = f"clinic_report_{report_type.lower().replace(' ', '_')}_{report_start}_to_{report_end}"

        # CSV Export
        with export_col1:
            try:
                csv_data = display_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download as CSV",
                    data=csv_data,
                    file_name=f"{file_prefix}.csv",
                    mime="text/csv",
                    key="csv_download_button"
                )
            except Exception as e:
                st.error(f"Error preparing CSV: {e}")

        # Excel Export
        with export_col2:
            try:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    display_df.to_excel(writer, index=False, sheet_name='ReportData')
                excel_data = buffer.getvalue()
                st.download_button(
                    "Download as Excel",
                    data=excel_data,
                    file_name=f"{file_prefix}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="excel_download_button"
                )
            except Exception as e:
                st.error(f"Error preparing Excel: {e}")
    elif report_type != "Custom Report": # Don't show export if custom report failed or no data
         pass # Already showed warning above
