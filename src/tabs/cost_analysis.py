# src/tabs/cost_analysis.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta # Import timedelta
import sys
import os

# Add src directory to Python path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    from data_loader import get_costs
except ImportError:
    st.error("Could not import database functions from data_loader.py.")
    st.stop()

def format_currency(amount):
    """Formats a number as EGP currency."""
    return f"EGP {amount:,.2f}"

def render_cost_analysis_tab(filtered_revenue_df, start_date, end_date):
    """
    Renders the cost analysis tab, displaying profitability, cost breakdown,
    and trends based on entered costs and filtered revenue data.

    Args:
        filtered_revenue_df (pd.DataFrame): DataFrame containing filtered revenue data
                                            (must have 'gross income' column).
        start_date (date): The start date from the sidebar filter.
        end_date (date): The end date from the sidebar filter.
    """
    st.header("📊 Cost Analysis & Profitability")

    # --- Add Cost-Specific Filters ---
    st.subheader("Cost Filters")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        cost_date_column = st.radio(
            "Filter costs based on:",
            ('expense_date', 'payment_date'),
            index=0, # Default to expense_date
            key='cost_date_filter_type',
            horizontal=True,
            help="Choose whether to filter costs by the date the expense was incurred or the date it was paid."
        )
    with col_f2:
        # Independent date range selector for costs
        # Try to get min/max dates from the database for better defaults
        try:
            all_costs_df_for_dates = get_costs() # Fetch all costs just for date range
            min_cost_date = all_costs_df_for_dates[cost_date_column].dropna().min() if not all_costs_df_for_dates.empty else date.today() - timedelta(days=30)
            max_cost_date = all_costs_df_for_dates[cost_date_column].dropna().max() if not all_costs_df_for_dates.empty else date.today()
            # Ensure min_cost_date is not NaT or None
            if pd.isna(min_cost_date): min_cost_date = date.today() - timedelta(days=30)
            if pd.isna(max_cost_date): max_cost_date = date.today()
        except Exception: # Fallback if fetching all costs fails
            min_cost_date = date.today() - timedelta(days=30)
            max_cost_date = date.today()

        cost_start_date, cost_end_date = st.date_input(
            f"Select {cost_date_column.replace('_', ' ').title()} Range",
            value=(min_cost_date, max_cost_date),
            min_value=min_cost_date,
            max_value=max_cost_date,
            key="cost_analysis_date_range"
        )
        # Capture the output directly into a tuple variable first
        selected_date_range = cost_start_date # st.date_input returns the tuple here initially

        # Now check the length of the actual tuple
        if isinstance(selected_date_range, tuple) and len(selected_date_range) == 2:
             cost_start_date, cost_end_date = selected_date_range # Unpack if valid
        else: # Handle case where input is cleared or invalid
             st.warning("Invalid date range selected for costs, using default range.")
             cost_start_date, cost_end_date = min_cost_date, max_cost_date


    st.markdown(f"Analyzing costs by **{cost_date_column.replace('_', ' ')}** from **{cost_start_date.strftime('%Y-%m-%d')}** to **{cost_end_date.strftime('%Y-%m-%d')}**")
    st.markdown(f"Revenue data is based on the main sidebar filter: **{start_date.strftime('%Y-%m-%d')}** to **{end_date.strftime('%Y-%m-%d')}**")
    st.divider()

    # --- Fetch and Filter Cost Data using new controls ---
    try:
        # Pass the selected date column and range to get_costs
        df_costs = get_costs(start_date_filter=cost_start_date, end_date_filter=cost_end_date, date_column=cost_date_column)
    except Exception as e:
        st.error(f"Failed to load cost data: {e}")
        return # Stop execution in this tab if costs can't be loaded

    if df_costs.empty:
        st.warning(f"No cost data found for the selected period based on {cost_date_column.replace('_', ' ')}. Please add entries in the 'Cost Entry' tab.")
        total_costs = 0 # Set costs to 0 if none found
        # Still calculate revenue based on main filters
        if not filtered_revenue_df.empty:
            total_revenue = filtered_revenue_df['gross income'].sum()
        else:
            total_revenue = 0
        profitability = total_revenue - total_costs
        # Display KPIs even if no costs
        st.subheader("Key Financial Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Revenue (Sidebar Filter)", format_currency(total_revenue))
        with col2:
            st.metric(f"Total Costs ({cost_date_column.replace('_', ' ').title()} Filter)", format_currency(total_costs))
        with col3:
            delta_color = "normal" if profitability >= 0 else "inverse"
            st.metric("Profit / Loss", format_currency(profitability), delta_color=delta_color)
        return # Stop further analysis if no costs

    # --- Calculate Key Metrics ---
    total_costs = df_costs['amount'].sum() # Costs based on cost filters

    if not filtered_revenue_df.empty:
        total_revenue = filtered_revenue_df['gross income'].sum()
    else:
        total_revenue = 0
        st.info("No revenue data matches the current filters in the sidebar.")

    profitability = total_revenue - total_costs

    # --- Display KPIs ---
    st.subheader("Key Financial Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Revenue (Sidebar Filter)", format_currency(total_revenue)) # Clarify revenue source
    with col2:
        st.metric(f"Total Costs ({cost_date_column.replace('_', ' ').title()} Filter)", format_currency(total_costs)) # Clarify cost source
    with col3:
        # Use color coding for profitability
        delta_color = "normal" if profitability >= 0 else "inverse"
        st.metric("Profit / Loss", format_currency(profitability), delta_color=delta_color)

    st.divider()

    # --- Visualizations ---
    st.subheader("Cost Breakdown & Trends")
    col1, col2 = st.columns(2)

    with col1:
        # Cost Breakdown by Category
        st.markdown("##### Cost Breakdown by Category")
        category_costs = df_costs.groupby('category')['amount'].sum().reset_index()
        category_costs = category_costs.sort_values(by='amount', ascending=False)
        fig_cat_pie = px.pie(category_costs,
                             names='category',
                             values='amount',
                             title="Cost Distribution by Category",
                             hole=0.3)
        fig_cat_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_cat_pie.update_layout(showlegend=False, height=400) # Hide legend for pie
        st.plotly_chart(fig_cat_pie, use_container_width=True)

    with col2:
        # Cost Trend Over Time
        st.markdown(f"##### Cost Trend Over Time (by {cost_date_column.replace('_', ' ')})")
        # Ensure the chosen date column is datetime for resampling
        df_costs[cost_date_column] = pd.to_datetime(df_costs[cost_date_column], errors='coerce')
        df_costs_trend = df_costs.dropna(subset=[cost_date_column]) # Drop rows where date conversion failed

        # Resample by month (or week/day depending on period length of the cost filter)
        time_unit = 'M' # Default to Month
        if (cost_end_date - cost_start_date).days <= 90:
            time_unit = 'W-MON' # Use Week starting Monday if period <= 90 days
        if (cost_end_date - cost_start_date).days <= 31:
             time_unit = 'D' # Use Day if period <= 31 days

        # Use the selected date column for resampling
        cost_trend = df_costs_trend.set_index(cost_date_column).resample(time_unit)['amount'].sum().reset_index()
        fig_trend = px.line(cost_trend,
                            x=cost_date_column, # Use selected date column for x-axis
                            y='amount',
                            title=f"Costs Over Time (by {cost_date_column.replace('_', ' ')})",
                            labels={cost_date_column: 'Date', 'amount': 'Total Cost (EGP)'},
                            markers=True)
        fig_trend.update_layout(height=400)
        st.plotly_chart(fig_trend, use_container_width=True)

    st.divider()

    # --- Detailed Item Analysis (Optional Filtering) ---
    st.subheader("Detailed Cost Analysis")
    # Allow filtering by category to see items
    categories = ['All'] + sorted(df_costs['category'].unique().tolist())
    selected_category = st.selectbox("Filter by Category to see Items:", options=categories)

    if selected_category == 'All':
        filtered_item_costs = df_costs
    else:
        filtered_item_costs = df_costs[df_costs['category'] == selected_category]

    if not filtered_item_costs.empty:
        # Item Breakdown within selected category (or all)
        item_costs = filtered_item_costs.groupby(['category', 'item'])['amount'].sum().reset_index()
        item_costs = item_costs.sort_values(by='amount', ascending=False)

        fig_item_bar = px.bar(item_costs,
                              x='item',
                              y='amount',
                              color='category', # Color by category if 'All' is selected
                              title=f"Cost Breakdown by Item ({selected_category})",
                              labels={'item': 'Item/Description', 'amount': 'Total Cost (EGP)'})
        fig_item_bar.update_layout(xaxis_title=None) # Hide x-axis title for clarity
        st.plotly_chart(fig_item_bar, use_container_width=True)

        # Detailed Table
        st.markdown("##### Detailed Cost Entries (Filtered by Cost Controls)")
        # Format and select columns for display - include both dates
        display_costs = filtered_item_costs[['expense_date', 'payment_date', 'category', 'item', 'amount']].copy()
        # Format dates nicely, handle potential NaT
        display_costs['expense_date'] = pd.to_datetime(display_costs['expense_date']).dt.strftime('%Y-%m-%d')
        display_costs['payment_date'] = pd.to_datetime(display_costs['payment_date']).dt.strftime('%Y-%m-%d').replace('NaT', 'Unpaid')
        display_costs['amount'] = display_costs['amount'].map('{:,.2f}'.format) # Format currency
        # Sort by the date column used for filtering
        display_costs = display_costs.sort_values(by=cost_date_column, ascending=False)
        st.dataframe(display_costs, use_container_width=True, hide_index=True)
    else:
        st.info(f"No cost items found for the category: {selected_category}")
