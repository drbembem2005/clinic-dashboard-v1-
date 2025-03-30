# src/tabs/goal_tracking.py
import streamlit as st
import pandas as pd
from datetime import date, datetime
import sys
import os
import numpy as np
import plotly.graph_objects as go # For gauge charts

# Add src directory to Python path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    # Import necessary functions from data_loader
    from data_loader import get_goals, get_costs
except ImportError as e:
    st.error(f"Could not import database functions from data_loader.py: {e}")
    st.stop()

# --- Helper Functions for Calculating Actual Values ---

def get_period_dates(time_period, goal_start, goal_end, filter_start, filter_end):
    """Determines the actual start and end dates for calculation based on goal period and filter."""
    # Use the intersection of the goal period (if custom) and the filter period
    actual_start = filter_start
    actual_end = filter_end

    if time_period == "Custom Range" and goal_start and goal_end:
        actual_start = max(filter_start, goal_start)
        actual_end = min(filter_end, goal_end)
    elif time_period == "Monthly":
        # Use the filter period directly, assuming it represents a month or part of it
        pass # Use filter_start, filter_end
    elif time_period == "Quarterly":
        # Use the filter period directly
        pass # Use filter_start, filter_end
    elif time_period == "Yearly":
        # Use the filter period directly
        pass # Use filter_start, filter_end

    # Ensure start is not after end
    if actual_start > actual_end:
        return None, None # Invalid period intersection

    return actual_start, actual_end

def calculate_actual_value(metric_name, time_period, goal_start, goal_end, target_value,
                           df_filtered_revenue, df_all_data, df_filtered_costs,
                           filter_start_date, filter_end_date):
    """Calculates the actual value for a given metric and period."""

    actual_start, actual_end = get_period_dates(time_period, goal_start, goal_end, filter_start_date, filter_end_date)

    if actual_start is None:
        st.warning(f"Goal period for '{metric_name}' does not overlap with the selected filter dates.")
        return 0, 0 # Return 0 actual, 0 progress

    # Filter the main dataframe further based on the actual calculation period
    mask = (df_filtered_revenue['date'].dt.date >= actual_start) & (df_filtered_revenue['date'].dt.date <= actual_end)
    df_period_revenue = df_filtered_revenue[mask]

    actual_value = 0.0

    try:
        if metric_name == "Total Revenue":
            actual_value = df_period_revenue['gross income'].sum()
        elif metric_name == "Profit":
            if df_filtered_costs.empty:
                st.warning(f"Cannot calculate actual Profit for '{metric_name}' goal: No cost data found for the filter period.")
                return 0, 0
            # Filter costs based on the *cost analysis* date range (assuming expense_date for profit calc)
            cost_mask = (df_filtered_costs['expense_date'] >= actual_start) & (df_filtered_costs['expense_date'] <= actual_end)
            period_costs = df_filtered_costs[cost_mask]['amount'].sum()
            period_revenue = df_period_revenue['gross income'].sum()
            actual_value = period_revenue - period_costs
        elif metric_name == "Total Visits":
            actual_value = len(df_period_revenue)
        elif metric_name == "Avg Revenue per Visit":
            period_revenue = df_period_revenue['gross income'].sum()
            period_visits = len(df_period_revenue)
            actual_value = (period_revenue / period_visits) if period_visits > 0 else 0
        elif metric_name == "New Patient Count":
            # Requires looking at all data to determine first visit date
            if df_all_data.empty:
                 st.warning("Cannot calculate New Patient Count goal: Full dataset not available.")
                 return 0, 0

            df_all = df_all_data.copy()
            df_all['date_only'] = df_all['date'].dt.date
            # Find first visit date for each patient in the whole dataset
            df_all['first_visit_date'] = df_all.groupby('Patient')['date_only'].transform('min')
            # Filter for visits within the actual calculation period
            df_period_all = df_all[(df_all['date_only'] >= actual_start) & (df_all['date_only'] <= actual_end)]
            # Count patients whose first *ever* visit falls within this period
            actual_value = df_period_all[df_period_all['first_visit_date'] >= actual_start]['Patient'].nunique()

        # Calculate progress percentage
        progress = (actual_value / target_value * 100) if target_value > 0 else 0
        return actual_value, progress

    except Exception as e:
        st.error(f"Error calculating actual value for {metric_name}: {e}")
        return 0, 0


# --- Main Render Function ---

def render_goal_tracking_tab(df_filtered_revenue, df_all_data, filter_start_date, filter_end_date):
    """Renders the goal tracking visualization tab."""
    st.header("📊 Goal Tracking")
    st.markdown("Monitor progress towards your active clinic goals based on the main sidebar filters.")

    try:
        df_goals = get_goals(active_only=True)
        df_filtered_costs = get_costs(start_date_filter=filter_start_date, end_date_filter=filter_end_date, date_column='expense_date') # Get costs based on sidebar filter for profit calc consistency
    except Exception as e:
        st.error(f"Failed to load goals or cost data: {e}")
        return

    if df_goals.empty:
        st.info("No active goals found. Please define some in the 'Goal Setting' tab.")
        return

    st.markdown(f"**Analysis Period (from Sidebar):** {filter_start_date.strftime('%Y-%m-%d')} to {filter_end_date.strftime('%Y-%m-%d')}")
    st.divider()

    # Display goals in columns for better layout
    num_goals = len(df_goals)
    cols = st.columns(min(num_goals, 3)) # Max 3 columns

    goal_index = 0
    for _, goal in df_goals.iterrows():
        metric = goal['metric_name']
        target = goal['target_value']
        period = goal['time_period']
        goal_start = goal['start_date'] # Might be NaT
        goal_end = goal['end_date'] # Might be NaT

        # Ensure dates are actual date objects or None
        goal_start_dt = pd.to_datetime(goal_start).date() if pd.notna(goal_start) else None
        goal_end_dt = pd.to_datetime(goal_end).date() if pd.notna(goal_end) else None


        actual, progress = calculate_actual_value(
            metric, period, goal_start_dt, goal_end_dt, target,
            df_filtered_revenue, df_all_data, df_filtered_costs,
            filter_start_date, filter_end_date
        )

        with cols[goal_index % len(cols)]:
            st.subheader(f"{metric}")
            period_str = f"{period}"
            if period == "Custom Range" and goal_start_dt and goal_end_dt:
                period_str += f" ({goal_start_dt.strftime('%Y-%m-%d')} to {goal_end_dt.strftime('%Y-%m-%d')})"
            st.caption(period_str)

            # Display using st.metric with custom color logic via Markdown
            delta_val = actual - target

            # Determine color based on 5-level progress
            if progress >= 100:
                color = "green"
            elif progress >= 90:
                color = "blue"
            elif progress >= 75:
                color = "orange" # Using orange for 75-89 instead of yellow for better visibility maybe? Let's try orange.
            elif progress >= 50:
                color = "gold" # Using gold for yellow
            else:
                color = "red"

            # Format value and delta with inline HTML/CSS for color
            # Need to use unsafe_allow_html=True with st.markdown if st.metric doesn't render it.
            # Let's try passing markdown directly first. -> This didn't work.
            # Display metric value without delta
            value_str = f"{actual:,.2f}"
            st.metric(
                label=f"Target: {target:,.2f}",
                value=value_str,
                delta=None # Remove delta from metric
            )

            # Use st.markdown to display colored progress/delta
            delta_sign = "+" if delta_val >= 0 else ""
            st.markdown(f"**Progress:** <span style='color:{color}; font-weight:bold;'>{progress:.1f}%</span> ({delta_sign}{delta_val:,.2f})", unsafe_allow_html=True)


            # Color code the progress bar as well (using standard progress bar)
            # We need to map progress to a color string for st.progress CSS hack (if desired)
            # Simple approach: just use the bar as is.
            # More complex: Use markdown with HTML/CSS for colored bars (can be brittle)
            progress_value = min(progress / 100.0, 1.0) # Cap at 1.0 for progress bar
            st.progress(progress_value)

            # --- Optional Gauge Chart (keeping commented for now) ---
            # try:
            #     fig = go.Figure(go.Indicator(
            #         mode = "gauge+number+delta",
            #         value = actual,
            #         delta = {'reference': target, 'relative': False, 'valueformat': ',.2f'},
            #         gauge = {
            #             'axis': {'range': [0, max(target * 1.5, actual * 1.1)], 'tickwidth': 1, 'tickcolor': "darkblue"}, # Dynamic range
            #             'bar': {'color': "darkblue"},
            #             'steps' : [
            #                 {'range': [0, target * 0.5], 'color': "lightgray"},
            #                 {'range': [target * 0.5, target], 'color': "gray"}],
            #             'threshold' : {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': target}},
            #         title = {'text': f"Progress vs Target ({target:,.2f})"}))
            #     fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
            #     st.plotly_chart(fig, use_container_width=True)
            # except Exception as chart_ex:
            #      st.warning(f"Could not display gauge chart for {metric}: {chart_ex}")
            # --- End Optional Gauge ---

            st.markdown("---") # Separator between goals in a column

        goal_index += 1
