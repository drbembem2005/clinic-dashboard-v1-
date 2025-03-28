# src/tabs/doctor_analytics.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Define a consistent color palette/template
PLOTLY_TEMPLATE = "plotly_white"

def render_doctor_analytics_tab(filtered_df):
    """
    Renders the Doctor Performance Analytics tab content.

    Args:
        filtered_df (pd.DataFrame): The filtered DataFrame based on sidebar selections.
    """
    st.header("Doctor Performance Analytics")

    if filtered_df.empty:
        st.warning("No data available for the selected filters.")
        return # Stop rendering if no data

    # Doctor Performance Metrics with detailed commission breakdown
    doc_metrics = filtered_df.groupby('Doctor').agg(
        gross_income=('gross income', 'sum'),
        id=('id', 'count'), # Visit count
        Patient=('Patient', 'nunique'), # Unique patients
        commission_paid_daily=('commission_paid_daily', 'sum'),
        commission_paid_monthly=('commission_paid_monthly', 'sum'),
        total_commission=('total_commission', 'sum')
    ).reset_index()

    # Calculate derived metrics, handling potential division by zero
    doc_metrics['avg_revenue_per_visit'] = np.where(
        doc_metrics['id'] > 0,
        doc_metrics['gross_income'] / doc_metrics['id'], # Use underscore
        0
    )
    doc_metrics['avg_revenue_per_patient'] = np.where(
        doc_metrics['Patient'] > 0,
        doc_metrics['gross_income'] / doc_metrics['Patient'], # Use underscore
        0
    )
    doc_metrics['commission_rate'] = np.where(
        doc_metrics['gross_income'] > 0, # Use underscore
        (doc_metrics['total_commission'] / doc_metrics['gross_income'] * 100), # Use underscore
        0
    )

    # Sort doctors by revenue for display
    st.subheader("Individual Doctor Performance")
    # Use the aggregated 'gross_income' for sorting
    for doctor in doc_metrics.sort_values('gross_income', ascending=False)['Doctor']:
        # Use the aggregated 'gross_income' for display in expander
        with st.expander(f"📊 {doctor} - Revenue: EGP{doc_metrics[doc_metrics['Doctor'] == doctor]['gross_income'].iloc[0]:,.2f}"):
            doc_data = doc_metrics[doc_metrics['Doctor'] == doctor].iloc[0]

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                # Use aggregated 'gross_income' for metric
                st.metric("Total Revenue", f"EGP{doc_data['gross_income']:,.2f}")
            with col2:
                st.metric("Unique Patients", f"{doc_data['Patient']:,}")
            with col3:
                st.metric("Total Visits", f"{doc_data['id']:,}") # Use 'id' count
            with col4:
                st.metric("Commission Rate", f"{doc_data['commission_rate']:.1f}%")

            # Commission breakdown
            st.markdown("---") # Separator
            st.markdown("#### Commission Breakdown")
            comm_col1, comm_col2, comm_col3 = st.columns(3)
            with comm_col1:
                st.metric("Daily Paid", f"EGP{doc_data['commission_paid_daily']:,.2f}")
            with comm_col2:
                st.metric("End-of-Month", f"EGP{doc_data['commission_paid_monthly']:,.2f}")
            with comm_col3:
                 st.metric("Total Commission", f"EGP{doc_data['total_commission']:,.2f}")


            # Additional metrics
            st.markdown("---") # Separator
            metrics_col1, metrics_col2 = st.columns(2)
            with metrics_col1:
                st.metric("Avg Revenue/Visit", f"EGP{doc_data['avg_revenue_per_visit']:,.2f}")
            with metrics_col2:
                st.metric("Avg Revenue/Patient", f"EGP{doc_data['avg_revenue_per_patient']:,.2f}")

    st.divider()

    # Overall Doctor Performance Visualization
    st.subheader("📈 Doctor Performance Comparison")

    performance_col1, performance_col2 = st.columns(2)

    with performance_col1:
        # Top Doctors by Revenue
        # Use aggregated 'gross_income' for sorting and plotting
        top_docs_revenue = doc_metrics.sort_values('gross_income', ascending=False).head(10)

        fig = px.bar(
            top_docs_revenue,
            y='Doctor',
            x='gross_income', # Use underscore
            title='Top 10 Doctors by Revenue',
            labels={'Doctor': '', 'gross_income': 'Revenue (EGP)'}, # Use underscore in label key
             color='gross_income', # Use underscore
             color_continuous_scale=px.colors.sequential.Blues,
             orientation='h',
             text='gross_income', # Use underscore
             template=PLOTLY_TEMPLATE # Apply template
        )
        fig.update_traces(texttemplate='EGP %{text:,.0f}', textposition='outside')
        fig.update_layout(height=500, yaxis_categoryorder='total ascending', margin=dict(t=40, l=10))
        st.plotly_chart(fig, use_container_width=True)

    with performance_col2:
        # Commission Rate Comparison Scatter Plot
        fig = px.scatter(
            doc_metrics,
            x='gross_income', # Use underscore
            y='commission_rate',
            size='id', # Size by number of visits
            color='avg_revenue_per_visit',
            hover_name='Doctor',
            title='Revenue vs Commission Rate (Size by Visits)',
            labels={
                'gross_income': 'Total Revenue (EGP)', # Use underscore in label key
                'commission_rate': 'Commission Rate (%)',
                'id': 'Number of Visits',
                 'avg_revenue_per_visit': 'Avg Revenue per Visit (EGP)'
             },
             color_continuous_scale=px.colors.sequential.Viridis, # Different color scale
             template=PLOTLY_TEMPLATE # Apply template
        )
        fig.update_layout(height=500, margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Doctor Efficiency Metrics
    st.subheader("⚡ Doctor Efficiency Analysis")

    efficiency_col1, efficiency_col2 = st.columns(2)

    with efficiency_col1:
        # Patients per Doctor
        patient_count = doc_metrics.sort_values('Patient', ascending=False).head(15) # Show top 15

        fig = px.bar(
            patient_count,
            y='Doctor',
            x='Patient',
            title='Top 15 Doctors by Unique Patient Count',
            labels={'Doctor': '', 'Patient': 'Unique Patient Count'},
             color='Patient',
             color_continuous_scale=px.colors.sequential.Greens,
             orientation='h',
             text='Patient',
             template=PLOTLY_TEMPLATE # Apply template
        )
        fig.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig.update_layout(height=500, yaxis_categoryorder='total ascending', margin=dict(t=40, l=10))
        st.plotly_chart(fig, use_container_width=True)

    with efficiency_col2:
        # Average Revenue per Patient
        avg_rev_patient = doc_metrics.sort_values('avg_revenue_per_patient', ascending=False).head(15) # Show top 15

        fig = px.bar(
            avg_rev_patient,
            y='Doctor',
            x='avg_revenue_per_patient',
            title='Top 15 Doctors by Avg Revenue per Patient',
            labels={'Doctor': '', 'avg_revenue_per_patient': 'Avg Revenue (EGP)'},
             color='avg_revenue_per_patient',
             color_continuous_scale=px.colors.sequential.Oranges,
             orientation='h',
             text='avg_revenue_per_patient',
             template=PLOTLY_TEMPLATE # Apply template
        )
        fig.update_traces(texttemplate='EGP %{text:,.0f}', textposition='outside')
        fig.update_layout(height=500, yaxis_categoryorder='total ascending', margin=dict(t=40, l=10))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Doctor Visit Type Analysis
    st.subheader("🩺 Visit Type Analysis by Doctor")

    # Group by doctor and visit type
    visit_type_by_doc = filtered_df.groupby(['Doctor', 'visit type'])['id'].count().reset_index()
    visit_type_by_doc.columns = ['Doctor', 'Visit Type', 'Count']

    # Create stacked bar chart
    fig = px.bar(
        visit_type_by_doc,
        x='Doctor',
        y='Count',
         color='Visit Type',
         title='Visit Types by Doctor',
         labels={'Doctor': 'Doctor', 'Count': 'Number of Visits', 'Visit Type': 'Visit Type'},
         barmode='stack', # Explicitly set to stack
         template=PLOTLY_TEMPLATE # Apply template
    )
    fig.update_layout(height=500, xaxis_tickangle=-45, margin=dict(t=40, b=100)) # Angle ticks for readability
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Doctor Performance Over Time
    st.subheader("📅 Doctor Performance Trends")

    # Allow user to select a doctor for detailed trend analysis
    available_doctors_trend = sorted(filtered_df['Doctor'].unique())
    if available_doctors_trend:
        selected_doctor = st.selectbox("Select Doctor for Trend Analysis", options=available_doctors_trend, key="doc_trend_select")

        # Filter data for selected doctor
        doctor_trend_data = filtered_df[filtered_df['Doctor'] == selected_doctor]

        # Group by date
        doctor_daily = doctor_trend_data.groupby(doctor_trend_data['date'].dt.date).agg(
            gross_income=('gross income', 'sum'),
            id=('id', 'count'), # Visit count
            Patient=('Patient', 'nunique'), # Unique patients
            total_commission=('total_commission', 'sum')
        ).reset_index()
        doctor_daily['date'] = pd.to_datetime(doctor_daily['date']) # Ensure datetime

         # Create line chart with subplots if needed, or combined
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=doctor_daily['date'],
            y=doctor_daily['gross_income'], # Use underscore
            name='Revenue',
            line=dict(color='#1976D2', width=2),
            mode='lines+markers'
        ))

        fig.add_trace(go.Scatter(
            x=doctor_daily['date'],
            y=doctor_daily['total_commission'],
            name='Commission',
            line=dict(color='#F44336', width=2),
            mode='lines+markers'
        ))

        fig.add_trace(go.Scatter(
            x=doctor_daily['date'],
            y=doctor_daily['id'],
            name='Visit Count',
            line=dict(color='#4CAF50', width=2, dash='dot'), # Differentiate style
            yaxis='y2', # Use secondary axis
            mode='lines+markers'
        ))

        fig.update_layout(
            title=f'Daily Performance Trend for {selected_doctor}',
            xaxis_title='Date',
            yaxis=dict(title='Amount (EGP)', tickprefix='EGP'),
            yaxis2=dict(title='Visit Count', overlaying='y', side='right', showgrid=False), # Hide grid for secondary axis
            height=500,
            legend=dict(x=0.01, y=0.99),
            hovermode='x unified',
            margin=dict(t=40),
            template=PLOTLY_TEMPLATE # Apply template
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No doctors available in the filtered data for trend analysis.")
