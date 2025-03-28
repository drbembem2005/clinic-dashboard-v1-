# src/tabs/executive_summary.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

# Define a consistent color palette/template
PLOTLY_TEMPLATE = "plotly_white"

def render_executive_summary_tab(filtered_df, df_data, start_date, end_date):
    """
    Renders the Executive Summary tab content.

    Args:
        filtered_df (pd.DataFrame): The filtered DataFrame based on sidebar selections.
        df_data (pd.DataFrame): The original unfiltered DataFrame.
        start_date (datetime.date): The start date from the filter.
        end_date (datetime.date): The end date from the filter.
    """
    st.header("Executive Summary Dashboard")
    st.divider()

    if filtered_df.empty:
        st.warning("No data available for the selected filters.")
        return # Stop rendering if no data

    # Calculate daily revenue first
    daily_revenue = filtered_df.groupby(filtered_df["date"].dt.date)["gross income"].sum().reset_index()
    daily_revenue.columns = ["date", "revenue"]
    daily_revenue['date'] = pd.to_datetime(daily_revenue['date']) # Ensure date is datetime

    # AI-Generated Business Insights Block
    st.subheader("AI-Generated Business Insights")
    insight_col1, insight_col2 = st.columns(2)

    with insight_col1:
        # Revenue Trend Insight
        if len(daily_revenue) >= 7:
            daily_revenue["rolling_avg"] = daily_revenue["revenue"].rolling(window=7, min_periods=1).mean()
            # Ensure enough data points for comparison
            if len(daily_revenue) >= 14:
                trend_last_days = daily_revenue["rolling_avg"].iloc[-7:].mean()
                trend_previous_days = daily_revenue["rolling_avg"].iloc[-14:-7].mean()
                trend_change = ((trend_last_days - trend_previous_days) / trend_previous_days * 100) if trend_previous_days > 0 else 0
            elif len(daily_revenue) >= 7: # Compare last 7 days to the first available period of similar length
                 trend_last_days = daily_revenue["rolling_avg"].iloc[-7:].mean()
                 trend_previous_days = daily_revenue["rolling_avg"].iloc[:len(daily_revenue)-7].mean() # Compare to what's left
                 trend_change = ((trend_last_days - trend_previous_days) / trend_previous_days * 100) if trend_previous_days > 0 else 0
            else:
                 trend_change = 0 # Not enough data for trend calculation

            if trend_change > 10:
                st.success(f"**📈 Strong Revenue Growth**\n\nRevenue is showing a significant upward trend with a {trend_change:.1f}% increase in the 7-day rolling average compared to the previous period.")
            elif trend_change > 0:
                st.info(f"**📈 Steady Growth**\n\nRevenue shows a moderate upward trend with a {trend_change:.1f}% increase in the 7-day rolling average.")
            elif trend_change < -10:
                 st.error(f"**📉 Significant Revenue Decline**\n\nRevenue trend shows a sharp {abs(trend_change):.1f}% decrease. Urgent review recommended.")
            else:
                st.warning(f"**📉 Revenue Alert**\n\nRevenue trend shows a {abs(trend_change):.1f}% decrease. Consider reviewing strategy.")
        else:
            st.info("Insufficient data (less than 7 days) for detailed revenue trend analysis.")


    with insight_col2:
        # Operational Insights
        if not filtered_df.empty:
            busy_days = filtered_df.groupby('day_of_week')['id'].count().sort_values(ascending=False)
            peak_time = filtered_df.groupby('hour')['id'].count().sort_values(ascending=False).index[0]
            avg_duration = filtered_df['visit_duration_mins'].mean()
            st.info(f"**⏰ Operational Patterns**\n\n- Busiest day: {busy_days.index[0]} ({busy_days.iloc[0]} visits)\n- Peak hour: {peak_time}:00\n- Avg. visit duration: {avg_duration:.0f} minutes")
        else:
            st.info("No operational data to display for the selected filters.")

    st.divider()

    # KPI Section
    st.subheader("Key Performance Indicators")

    # Calculate previous period dates
    period_duration = (end_date - start_date).days + 1
    prev_start_date = start_date - timedelta(days=period_duration)
    prev_end_date = start_date - timedelta(days=1)

    # Filter data for the previous period
    prev_period_df = df_data[
        (df_data["date"].dt.date >= prev_start_date) &
        (df_data["date"].dt.date <= prev_end_date)
    ]

    # Helper function for calculating KPI change
    def calculate_change(current_val, prev_val):
        if prev_val is None or pd.isna(prev_val) or prev_val == 0:
            return 0 # Avoid division by zero or comparison with NaN
        return ((current_val - prev_val) / prev_val * 100)

    # First row of KPIs
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    # Total Revenue
    total_revenue = filtered_df["gross income"].sum()
    prev_period_revenue = prev_period_df["gross income"].sum() if not prev_period_df.empty else 0
    revenue_change = calculate_change(total_revenue, prev_period_revenue)
    with kpi_col1:
        st.metric(label="Total Revenue", value=f"EGP{total_revenue:,.2f}", delta=f"{revenue_change:.1f}%")

    # Total Profit
    total_profit = filtered_df["profit"].sum()
    prev_period_profit = prev_period_df["profit"].sum() if not prev_period_df.empty else 0
    profit_change = calculate_change(total_profit, prev_period_profit)
    with kpi_col2:
        st.metric(label="Total Profit", value=f"EGP{total_profit:,.2f}", delta=f"{profit_change:.1f}%")

    # Patient Count
    patient_count = filtered_df["Patient"].nunique()
    prev_period_patients = prev_period_df["Patient"].nunique() if not prev_period_df.empty else 0
    patient_change = calculate_change(patient_count, prev_period_patients)
    with kpi_col3:
        st.metric(label="Unique Patients", value=f"{patient_count:,}", delta=f"{patient_change:.1f}%")

    # Average Revenue per Visit
    avg_revenue = filtered_df["gross income"].mean() if not filtered_df.empty else 0
    prev_period_avg = prev_period_df["gross income"].mean() if not prev_period_df.empty else 0
    avg_change = calculate_change(avg_revenue, prev_period_avg)
    with kpi_col4:
        st.metric(label="Avg. Revenue per Visit", value=f"EGP{avg_revenue:,.2f}", delta=f"{avg_change:.1f}%")

    # Second row of KPIs
    kpi2_col1, kpi2_col2, kpi2_col3, kpi2_col4 = st.columns(4)

    # Profit Margin
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    prev_profit_margin = (prev_period_profit / prev_period_revenue * 100) if prev_period_revenue > 0 else 0
    margin_change = profit_margin - prev_profit_margin # Absolute change in percentage points
    with kpi2_col1:
        st.metric(label="Profit Margin", value=f"{profit_margin:.1f}%", delta=f"{margin_change:.1f} % points") # Indicate absolute change

    # Cash vs Card Ratio
    cash_amount = filtered_df["cash pay"].sum()
    visa_amount = filtered_df["visa pay"].sum()
    total_paid = cash_amount + visa_amount
    cash_ratio = (cash_amount / total_paid * 100) if total_paid > 0 else 0

    prev_cash = prev_period_df["cash pay"].sum() if not prev_period_df.empty else 0
    prev_visa = prev_period_df["visa pay"].sum() if not prev_period_df.empty else 0
    prev_total_paid = prev_cash + prev_visa
    prev_cash_ratio = (prev_cash / prev_total_paid * 100) if prev_total_paid > 0 else 0
    cash_ratio_change = cash_ratio - prev_cash_ratio # Absolute change
    with kpi2_col2:
        st.metric(label="Cash Payment Ratio", value=f"{cash_ratio:.1f}%", delta=f"{cash_ratio_change:.1f} % points")

    # Commission Rate
    total_commission = filtered_df["total_commission"].sum()
    commission_rate = (total_commission / total_revenue * 100) if total_revenue > 0 else 0
    prev_total_commission = prev_period_df["total_commission"].sum() if not prev_period_df.empty else 0
    prev_commission_rate = (prev_total_commission / prev_period_revenue * 100) if prev_period_revenue > 0 else 0
    commission_change = commission_rate - prev_commission_rate # Absolute change
    with kpi2_col3:
        st.metric(label="Avg. Commission Rate", value=f"{commission_rate:.1f}%", delta=f"{commission_change:.1f} % points")

    # Visits per Day
    days_count = (end_date - start_date).days + 1
    visits_per_day = len(filtered_df) / days_count if days_count > 0 else 0
    prev_days_count = (prev_end_date - prev_start_date).days + 1 if prev_start_date <= prev_end_date else 0 # Handle edge case
    prev_visits = len(prev_period_df)
    prev_visits_per_day = prev_visits / prev_days_count if prev_days_count > 0 else 0
    visits_change = calculate_change(visits_per_day, prev_visits_per_day)
    with kpi2_col4:
        st.metric(label="Avg. Visits per Day", value=f"{visits_per_day:.1f}", delta=f"{visits_change:.1f}%")

    st.divider()

    # Charts Section
    st.subheader("Revenue & Performance Analytics")

    # Revenue Charts
    exec_chart1, exec_chart2 = st.columns(2)

    with exec_chart1:
        st.subheader("Revenue Trend")
        if not daily_revenue.empty:
            fig = px.line(
                daily_revenue,
                x="date",
                y="revenue",
                title="Daily Revenue Trend",
                labels={"date": "Date", "revenue": "Revenue (EGP)"},
                line_shape="spline",
                template=PLOTLY_TEMPLATE # Apply template
            )
            fig.update_traces(mode="lines+markers", fill="tozeroy", line=dict(width=2, color="#1976D2"))
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis_tickformat="%b %d, %Y", # More specific format
                yaxis_tickprefix="EGP"
            )
            st.plotly_chart(fig, use_container_width=True, key="exec_revenue_trend")
        else:
            st.info("No daily revenue data to display.")

    with exec_chart2:
        st.subheader("Revenue by Visit Type")
        if not filtered_df.empty:
            visit_revenue = filtered_df.groupby("visit type")["gross income"].sum().reset_index()
            visit_revenue.columns = ["visit_type", "revenue"]
            visit_revenue = visit_revenue.sort_values("revenue", ascending=False)

            fig = px.bar(
                visit_revenue,
                x="visit_type",
                y="revenue",
                title="Revenue by Visit Type",
                labels={"visit_type": "Visit Type", "revenue": "Revenue (EGP)"},
                color="revenue",
                color_continuous_scale=px.colors.sequential.Blues, # Use Plotly sequential scale
                template=PLOTLY_TEMPLATE # Apply template
            )
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                coloraxis_showscale=False,
                xaxis_title=None # Cleaner look
            )
            st.plotly_chart(fig, use_container_width=True, key="exec_visit_revenue")
        else:
            st.info("No visit type revenue data to display.")

    # Performance Charts Block
    exec_chart3, exec_chart4 = st.columns(2)

    with exec_chart3:
        st.subheader("Top 10 Doctors by Revenue")
        if not filtered_df.empty:
            doctor_revenue = filtered_df.groupby("Doctor")["gross income"].sum().reset_index()
            doctor_revenue.columns = ["doctor", "revenue"]
            doctor_revenue = doctor_revenue.sort_values("revenue", ascending=False).head(10)

            fig = px.bar(
                doctor_revenue,
                y="doctor",
                x="revenue",
                title="Top 10 Doctors by Revenue",
                labels={"doctor": "Doctor", "revenue": "Revenue (EGP)"},
                color="revenue",
                color_continuous_scale=px.colors.sequential.Blues,
                orientation="h",
                template=PLOTLY_TEMPLATE # Apply template
            )
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                coloraxis_showscale=False,
                yaxis_categoryorder="total ascending",
                yaxis_title=None # Cleaner look
            )
            st.plotly_chart(fig, use_container_width=True, key="exec_doctor_revenue")
        else:
            st.info("No doctor revenue data to display.")

    with exec_chart4:
        st.subheader("Revenue by Day of Week")
        if not filtered_df.empty:
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_revenue = filtered_df.groupby("day_of_week")["gross income"].sum().reset_index()
            day_revenue.columns = ["day", "revenue"]

            # Ensure 'day' column is categorical with the correct order
            day_revenue["day"] = pd.Categorical(day_revenue["day"], categories=day_order, ordered=True)
            day_revenue = day_revenue.sort_values("day")

            fig = px.bar(
                day_revenue,
                x="day",
                y="revenue",
                title="Revenue by Day of Week",
                labels={"day": "Day", "revenue": "Revenue (EGP)"},
                color="revenue",
                color_continuous_scale=px.colors.sequential.Blues,
                template=PLOTLY_TEMPLATE # Apply template
            )
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis_categoryorder="array",
                xaxis_categoryarray=day_order,
                coloraxis_showscale=False,
                xaxis_title=None # Cleaner look
            )
            st.plotly_chart(fig, use_container_width=True, key="exec_day_revenue")
        else:
            st.info("No daily revenue data to display.")
