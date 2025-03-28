# src/tabs/financial_performance.py
import streamlit as st
import pandas as pd
import numpy as np # Added numpy import
import plotly.express as px
import plotly.graph_objects as go

# Define a consistent color palette/template
PLOTLY_TEMPLATE = "plotly_white"

def render_financial_performance_tab(filtered_df):
    """
    Renders the Financial Performance Analysis tab content.

    Args:
        filtered_df (pd.DataFrame): The filtered DataFrame based on sidebar selections.
    """
    st.header("Financial Performance Analysis")

    if filtered_df.empty:
        st.warning("No data available for the selected filters.")
        return # Stop rendering if no data

    # Financial Overview with commission breakdown
    fin_overview_col1, fin_overview_col2, fin_overview_col3 = st.columns([1, 1, 2]) # Adjust column ratios

    with fin_overview_col1:
        total_revenue = filtered_df["gross income"].sum()
        total_doctor_commission = filtered_df["total_commission"].sum() # Renamed for clarity
        advertising_commission = filtered_df["advertising_commission"].sum()
        net_profit = filtered_df["profit"].sum() # Use calculated profit

        st.metric("Total Revenue", f"EGP{total_revenue:,.2f}")
        st.metric("Net Profit", f"EGP{net_profit:,.2f}")


    with fin_overview_col2:
        st.metric("Total Doctor Commission", f"EGP{total_doctor_commission:,.2f}")
        st.metric("Advertising Commission", f"EGP{advertising_commission:,.2f}")
        # daily_commission = filtered_df["commission_paid_daily"].sum() # Consider if these are needed here or in doctor tab
        # monthly_commission = filtered_df["commission_paid_monthly"].sum()
        # st.metric("Daily Paid Commission", f"EGP{daily_commission:,.2f}")
        # st.metric("End-of-Month Commission", f"EGP{monthly_commission:,.2f}")


    with fin_overview_col3:
        # Commission Trend
        commission_trend = filtered_df.groupby(filtered_df['date'].dt.date).agg(
            # commission_paid_daily=('commission_paid_daily', 'sum'), # Optional
            # commission_paid_monthly=('commission_paid_monthly', 'sum'), # Optional
            advertising_commission=('advertising_commission', 'sum'),
            total_doctor_commission=('total_commission', 'sum') # Renamed
        ).reset_index()
        commission_trend['date'] = pd.to_datetime(commission_trend['date']) # Ensure datetime

        fig = px.line(commission_trend, x='date',
                     y=['total_doctor_commission', 'advertising_commission'],
                     title='Commission Breakdown Over Time',
                     labels={'value': 'Amount (EGP)', 'variable': 'Commission Type', 'date': 'Date'},
                     color_discrete_map={
                         # 'commission_paid_daily': '#2196F3',
                         # 'commission_paid_monthly': '#FFC107',
                         'advertising_commission': '#F44336',
                          'total_doctor_commission': '#4CAF50' # Renamed
                      },
                      template=PLOTLY_TEMPLATE) # Apply template
        fig.update_layout(height=300, margin=dict(t=30, b=10)) # Adjust height and margins
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Detailed Financial Analysis
    fin_col1, fin_col2 = st.columns(2)

    with fin_col1:
        st.subheader("Revenue Breakdown by Payment Method")

        # Revenue by Payment Method
        payment_revenue = filtered_df.groupby('payment_method').agg(
            gross_income=('gross income', 'sum'),
            id=('id', 'count') # Use 'id' or another unique identifier
        ).reset_index()

        if not payment_revenue.empty and 'id' in payment_revenue.columns and payment_revenue['id'].sum() > 0:
             payment_revenue['avg_transaction'] = payment_revenue['gross_income'] / payment_revenue['id']
        else:
             payment_revenue['avg_transaction'] = 0 # Avoid division by zero

        fig = px.pie(
            payment_revenue,
            values='gross_income',
            names='payment_method',
            title='Revenue by Payment Method',
             hole=0.4,
             color_discrete_sequence=px.colors.qualitative.Pastel, # Softer colors
             template=PLOTLY_TEMPLATE # Apply template
        )
        fig.update_layout(height=400, margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True, key="fin_payment_method_pie")

    with fin_col2:
        st.subheader("Monthly Financial Trends")

        # Monthly Profit Trend
        monthly_metrics = filtered_df.copy()
        # Ensure month_year exists
        if 'month_year' not in monthly_metrics.columns:
             monthly_metrics["month_year"] = monthly_metrics["date"].dt.strftime('%Y-%m')

        monthly_metrics = monthly_metrics.groupby('month_year').agg(
            gross_income=('gross income', 'sum'),
            total_commission=('total_commission', 'sum'),
            profit=('profit', 'sum')
        ).reset_index()

        if not monthly_metrics.empty:
            monthly_metrics['profit_margin'] = np.where(
                monthly_metrics['gross_income'] > 0, # Use underscore
                monthly_metrics['profit'] / monthly_metrics['gross_income'] * 100, # Use underscore
                0
            ) # Corrected indentation

            fig = go.Figure()

            # Add Revenue line
            fig.add_trace(go.Scatter(
                x=monthly_metrics['month_year'],
                y=monthly_metrics['gross_income'],
                name='Revenue',
                line=dict(color='#2196F3', width=2),
                mode='lines+markers'
            ))

            # Add Profit line
            fig.add_trace(go.Scatter(
                x=monthly_metrics['month_year'],
                y=monthly_metrics['profit'],
                name='Profit',
                line=dict(color='#4CAF50', width=2),
                mode='lines+markers'
            ))

            # Add Profit Margin line on secondary y-axis
            fig.add_trace(go.Scatter(
                x=monthly_metrics['month_year'],
                y=monthly_metrics['profit_margin'],
                name='Profit Margin %',
                line=dict(color='#FFC107', width=2, dash='dot'),
                yaxis='y2',
                mode='lines+markers'
            ))

            fig.update_layout(
                title='Monthly Revenue, Profit, and Margin',
                height=400,
                yaxis=dict(title='Amount (EGP)', tickprefix='EGP'),
                yaxis2=dict(title='Profit Margin (%)', overlaying='y', side='right', ticksuffix='%'),
                xaxis_title='Month-Year',
                legend=dict(x=0.01, y=0.99),
                 hovermode='x unified',
                 margin=dict(t=40),
                 template=PLOTLY_TEMPLATE # Apply template
            )
            st.plotly_chart(fig, use_container_width=True, key="fin_monthly_trends") # Changed key
        else:
            st.info("No monthly data available for the selected filters.")
