# src/tabs/operational_metrics.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Define a consistent color palette/template
PLOTLY_TEMPLATE = "plotly_white"

def render_operational_metrics_tab(filtered_df, start_date, end_date):
    """
    Renders the Operational Metrics tab content.

    Args:
        filtered_df (pd.DataFrame): The filtered DataFrame based on sidebar selections.
        start_date (datetime.date): The start date from the filter.
        end_date (datetime.date): The end date from the filter.
    """
    st.header("Operational Metrics")

    if filtered_df.empty:
        st.warning("No data available for the selected filters.")
        return # Stop rendering if no data

    # --- Overview metrics ---
    st.subheader("📊 Overview")
    overview_col1, overview_col2, overview_col3, overview_col4 = st.columns(4)

    days_count = (end_date - start_date).days + 1
    total_visits = len(filtered_df)

    with overview_col1:
        avg_visits_per_day = total_visits / days_count if days_count > 0 else 0
        st.metric("Avg. Daily Visits", f"{avg_visits_per_day:.1f}")

    with overview_col2:
        avg_duration = filtered_df['visit_duration_mins'].mean()
        st.metric("Avg. Visit Duration", f"{avg_duration:.1f} mins")

    with overview_col3:
        peak_hour_series = filtered_df.groupby('hour')['id'].count()
        peak_hour = peak_hour_series.idxmax() if not peak_hour_series.empty else "N/A"
        st.metric("Peak Hour", f"{peak_hour:02d}:00" if isinstance(peak_hour, (int, np.integer)) else peak_hour)

    with overview_col4:
        # Assuming 12 operational hours per day for utilization calculation
        # This could be made more dynamic if clinic hours vary
        operational_hours_per_day = 12
        total_possible_slots = days_count * operational_hours_per_day # Simplified view
        # A more realistic utilization might consider doctor availability, rooms etc.
        # For now, using a simple visits / (days * hours) ratio
        utilization_rate = (total_visits / (days_count * operational_hours_per_day) * 100) if days_count > 0 else 0
        st.metric("Est. Daily Utilization", f"{utilization_rate:.1f}%", help="Based on avg visits vs 12 operational hours/day.")

    st.divider()

    # --- Detailed Analysis Section ---
    st.subheader("📈 Detailed Time-based Analysis")

    # Time-based Analysis
    time_col1, time_col2 = st.columns(2)

    with time_col1:
        # Hourly Distribution
        hourly_visits = filtered_df.groupby('hour')['id'].count().reset_index()
        hourly_visits.columns = ['Hour', 'Visit Count']
        fig = px.bar(
            hourly_visits,
            x='Hour',
             y='Visit Count',
             title='Hourly Visit Distribution',
             labels={'Hour': 'Hour of Day', 'Visit Count': 'Number of Visits'},
             template=PLOTLY_TEMPLATE # Apply template
        )
        fig.update_layout(height=400, margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True, key="ops_hourly_dist")

    with time_col2:
        # Daily Distribution
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        daily_visits = filtered_df.groupby('day_of_week')['id'].count().reindex(day_order).reset_index()
        daily_visits.columns = ['Day of Week', 'Visit Count']
        fig = px.bar(
            daily_visits,
            x='Day of Week',
             y='Visit Count',
             title='Daily Visit Distribution',
             labels={'Day of Week': 'Day of Week', 'Visit Count': 'Number of Visits'},
             template=PLOTLY_TEMPLATE # Apply template
        )
        fig.update_layout(height=400, margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True, key="ops_daily_dist")

    st.divider()
    st.subheader("⏱️ Visit Duration Analysis")
    # Visit Duration Analysis
    duration_col1, duration_col2 = st.columns(2)

    with duration_col1:
        # Visit Duration Distribution Histogram
        fig = px.histogram(
            filtered_df,
            x='visit_duration_mins',
             nbins=20,
             title='Visit Duration Distribution',
             labels={'visit_duration_mins': 'Duration (minutes)', 'count': 'Number of Visits'},
             template=PLOTLY_TEMPLATE # Apply template
        )
        fig.update_layout(height=400, margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True, key="ops_duration_dist")

    with duration_col2:
        # Average Duration by Visit Type
        avg_duration_by_type = filtered_df.groupby('visit type')['visit_duration_mins'].mean().reset_index().sort_values('visit_duration_mins', ascending=False)
        avg_duration_by_type.columns = ['Visit Type', 'Average Duration (mins)']
        fig = px.bar(
            avg_duration_by_type,
            x='Visit Type',
            y='Average Duration (mins)',
             title='Average Duration by Visit Type',
             labels={'Visit Type': 'Visit Type', 'Average Duration (mins)': 'Average Duration (minutes)'},
             color='Average Duration (mins)',
             color_continuous_scale=px.colors.sequential.Plasma,
             template=PLOTLY_TEMPLATE # Apply template
        )
        fig.update_layout(height=400, coloraxis_showscale=False, margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True, key="ops_type_duration")

    st.divider()
    # --- Efficiency Metrics ---
    st.subheader("⚡ Efficiency Metrics")

    efficiency_col1, efficiency_col2 = st.columns(2)

    with efficiency_col1:
        # Revenue per Hour
        hourly_revenue = filtered_df.groupby('hour')['gross income'].sum().reset_index()
        hourly_revenue.columns = ['Hour', 'Total Revenue']

        fig = px.line(
            hourly_revenue,
            x='Hour',
             y='Total Revenue',
             title='Total Revenue by Hour of Day',
             labels={'Hour': 'Hour of Day', 'Total Revenue': 'Total Revenue (EGP)'},
             markers=True, # Add markers to the line
             template=PLOTLY_TEMPLATE # Apply template
        )
        fig.update_layout(height=400, margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True, key="ops_hourly_revenue")

    with efficiency_col2:
        # Average Daily Visits per Doctor
        # Need to group by date first, then doctor, then average
        visits_per_doc_daily = filtered_df.groupby([filtered_df['date'].dt.date, 'Doctor'])['id'].count().reset_index()
        visits_per_doc_avg = visits_per_doc_daily.groupby('Doctor')['id'].mean().sort_values(ascending=True).reset_index()
        visits_per_doc_avg.columns = ['Doctor', 'Average Daily Visits']

        fig = px.bar(
            visits_per_doc_avg.tail(15), # Show bottom 15 for potentially less busy doctors
            y='Doctor',
            x='Average Daily Visits',
             orientation='h',
             title='Average Daily Visits per Doctor (Bottom 15)',
             labels={'Doctor': '', 'Average Daily Visits': 'Average Visits per Day'},
             text='Average Daily Visits',
             template=PLOTLY_TEMPLATE # Apply template
        )
        fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig.update_layout(height=400, yaxis_categoryorder='total ascending', margin=dict(t=40, l=10))
        st.plotly_chart(fig, use_container_width=True, key="ops_doc_visits")

    st.divider()
    # --- Resource Utilization ---
    st.subheader("📊 Resource Utilization (Estimates)")

    util_col1, util_col2 = st.columns(2)

    with util_col1:
        # Daily Utilization Rate (based on visits vs. operational hours)
        daily_util = filtered_df.groupby(filtered_df['date'].dt.date)['id'].count().reset_index()
        daily_util.columns = ['Date', 'Visit Count']
        daily_util['utilization'] = (daily_util['Visit Count'] / operational_hours_per_day) * 100 # Simple ratio
        daily_util['Date'] = pd.to_datetime(daily_util['Date']) # Ensure datetime

        fig = px.line(
            daily_util,
            x='Date',
             y='utilization',
             title='Estimated Daily Utilization Rate',
             labels={'Date': 'Date', 'utilization': 'Utilization Rate (%)'},
             markers=True,
             template=PLOTLY_TEMPLATE # Apply template
        )
        fig.update_layout(height=400, margin=dict(t=40), yaxis_ticksuffix='%')
        st.plotly_chart(fig, use_container_width=True, key="ops_daily_util")

    with util_col2:
        # Average Concurrent Visits by Hour (Proxy for peak load)
        visit_overlap = filtered_df.groupby(['date', 'hour'])['id'].count().reset_index()
        avg_concurrent = visit_overlap.groupby('hour')['id'].mean().reset_index()
        avg_concurrent.columns = ['Hour', 'Average Concurrent Visits']

        fig = px.bar(
            avg_concurrent,
            x='Hour',
             y='Average Concurrent Visits',
             title='Average Concurrent Visits by Hour',
             labels={'Hour': 'Hour of Day', 'Average Concurrent Visits': 'Avg. Concurrent Visits'},
             template=PLOTLY_TEMPLATE # Apply template
        )
        fig.update_layout(height=400, margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True, key="ops_concurrent_visits")
