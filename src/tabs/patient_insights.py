# src/tabs/patient_insights.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from datetime import timedelta

# Define a consistent color palette/template
PLOTLY_TEMPLATE = "plotly_white"

def render_patient_insights_tab(filtered_df, df_data, start_date, end_date):
    """
    Renders the Patient Insights & Analytics tab content.

    Args:
        filtered_df (pd.DataFrame): The filtered DataFrame based on sidebar selections.
        df_data (pd.DataFrame): The original unfiltered DataFrame.
        start_date (datetime.date): The start date from the filter.
        end_date (datetime.date): The end date from the filter.
    """
    st.header("Patient Insights & Analytics")

    if filtered_df.empty:
        st.warning("No data available for the selected filters.")
        return # Stop rendering if no data

    # --- Overview Metrics ---
    st.subheader("📊 Patient Overview")
    patient_overview1, patient_overview2, patient_overview3, patient_overview4 = st.columns(4)

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

    with patient_overview1:
        total_patients = filtered_df["Patient"].nunique()
        prev_patients = prev_period_df["Patient"].nunique() if not prev_period_df.empty else 0
        patient_growth = calculate_change(total_patients, prev_patients)
        st.metric("Total Patients", f"{total_patients:,}", f"{patient_growth:.1f}%")

    with patient_overview2:
        avg_visits = len(filtered_df) / total_patients if total_patients > 0 else 0
        # Calculate previous period avg visits
        prev_total_visits = len(prev_period_df)
        prev_avg_visits = prev_total_visits / prev_patients if prev_patients > 0 else 0
        avg_visits_change = calculate_change(avg_visits, prev_avg_visits)
        st.metric("Avg Visits/Patient", f"{avg_visits:.1f}", delta=f"{avg_visits_change:.1f}%")

    with patient_overview3:
        avg_revenue_per_patient = filtered_df.groupby("Patient")["gross income"].sum().mean() if total_patients > 0 else 0
        prev_avg_revenue_per_patient = prev_period_df.groupby("Patient")["gross income"].sum().mean() if prev_patients > 0 else 0
        avg_rev_patient_change = calculate_change(avg_revenue_per_patient, prev_avg_revenue_per_patient)
        st.metric("Avg Revenue/Patient", f"EGP{avg_revenue_per_patient:,.2f}", delta=f"{avg_rev_patient_change:.1f}%")

    with patient_overview4:
        # Retention Rate: % of patients with > 1 visit in the period
        retention_rate = (filtered_df.groupby("Patient")["id"].count() > 1).mean() * 100 if total_patients > 0 else 0
        prev_retention_rate = (prev_period_df.groupby("Patient")["id"].count() > 1).mean() * 100 if prev_patients > 0 else 0
        retention_change = retention_rate - prev_retention_rate # Absolute change
        st.metric("Patient Retention Rate", f"{retention_rate:.1f}%", delta=f"{retention_change:.1f} % points")

    st.divider()

    # --- Patient Visit Analysis ---
    st.subheader("🔄 Visit Patterns")
    visit_col1, visit_col2 = st.columns(2)

    with visit_col1:
        # Visit Frequency Distribution
        if total_patients > 0:
            visit_freq = filtered_df.groupby("Patient")["id"].count().value_counts().sort_index().reset_index()
            visit_freq.columns = ['Number of Visits', 'Number of Patients']
            fig = px.bar(
                visit_freq,
                x='Number of Visits',
                y='Number of Patients',
                 title="Visit Frequency Distribution",
                 labels={"Number of Visits": "Number of Visits", "Number of Patients": "Number of Patients"},
                 color='Number of Patients',
                 color_continuous_scale=px.colors.sequential.Blues,
                 template=PLOTLY_TEMPLATE # Apply template
            )
            fig.update_layout(height=400, coloraxis_showscale=False, margin=dict(t=40))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No patient visit frequency data to display.")

    with visit_col2:
        # Visit Type Distribution (Overall for filtered period)
        visit_type_dist = filtered_df['visit type'].value_counts().reset_index()
        visit_type_dist.columns = ['Visit Type', 'Count']

        fig = px.pie(
            visit_type_dist,
            values='Count',
            names='Visit Type',
             title="Overall Visit Type Distribution",
             hole=0.4,
             color_discrete_sequence=px.colors.qualitative.Pastel,
             template=PLOTLY_TEMPLATE # Apply template
        )
        fig.update_layout(height=400, margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Patient Revenue Analysis ---
    st.subheader("💰 Revenue Analytics")
    revenue_col1, revenue_col2 = st.columns(2)

    with revenue_col1:
        # Patient Revenue Distribution (Box Plot)
        if total_patients > 0:
            patient_revenue = filtered_df.groupby("Patient")["gross income"].sum()

            fig = go.Figure()
            fig.add_trace(go.Box(
                y=patient_revenue.values,
                name="Revenue Distribution",
                boxpoints="outliers", # Show outliers
                marker_color="rgb(25, 118, 210)",
                line_color="rgb(25, 118, 210)"
            ))

            fig.update_layout(
                title="Patient Revenue Distribution",
                height=400,
                 yaxis_title="Total Revenue per Patient (EGP)",
                 showlegend=False,
                 margin=dict(t=40),
                 template=PLOTLY_TEMPLATE # Apply template
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No patient revenue data to display.")

    with revenue_col2:
        # Top Revenue Contributing Patients
        if total_patients > 0:
            patient_revenue = filtered_df.groupby("Patient")["gross income"].sum().sort_values(ascending=False)
            top_patients = patient_revenue.head(10).reset_index()
            top_patients.columns = ['Patient', 'Total Revenue']

            fig = px.bar(
                top_patients,
                x='Patient',
                y='Total Revenue',
                 title="Top 10 Patients by Revenue",
                 labels={"Patient": "Patient ID", "Total Revenue": "Total Revenue (EGP)"},
                 color='Total Revenue',
                 color_continuous_scale=px.colors.sequential.Blues,
                 template=PLOTLY_TEMPLATE # Apply template
            )
            fig.update_layout(height=400, coloraxis_showscale=False, xaxis_title=None, margin=dict(t=40))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No top patient revenue data to display.")

    st.divider()

    # --- Patient Segmentation (Simplified K-Means) ---
    st.subheader("🎯 Patient Segmentation (K-Means)")

    if total_patients > 2: # Need at least 3 patients for 3 clusters
        # Prepare data for segmentation
        patient_metrics = filtered_df.groupby("Patient").agg(
            visit_count=('id', 'count'),
            total_revenue=('gross income', 'sum'),
            avg_revenue=('gross income', 'mean'),
            avg_duration=('visit_duration_mins', 'mean')
        ).reset_index()
        patient_metrics = patient_metrics.fillna(0) # Fill NaNs that might arise from single visits

        # Normalize features for clustering
        features = ["visit_count", "total_revenue", "avg_revenue", "avg_duration"]
        # Check for near-zero variance before scaling
        valid_features = [f for f in features if patient_metrics[f].nunique() > 1]
        if not valid_features:
             st.warning("Insufficient feature variance for segmentation.")
        else:
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(patient_metrics[valid_features])

            # Perform k-means clustering
            n_clusters = 3 # Keep it simple
            try:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10) # Explicitly set n_init
                patient_metrics["Segment_Num"] = kmeans.fit_predict(scaled_features)

                # Analyze cluster centers to assign meaningful labels (example logic)
                cluster_centers = scaler.inverse_transform(kmeans.cluster_centers_)
                centers_df = pd.DataFrame(cluster_centers, columns=valid_features)
                # Assign labels based on total_revenue (example)
                centers_df['Segment_Label'] = centers_df['total_revenue'].rank(method='dense').map({1.0: 'Low Value', 2.0: 'Mid Value', 3.0: 'High Value'})
                segment_map = centers_df['Segment_Label'].to_dict()

                patient_metrics["Segment"] = patient_metrics["Segment_Num"].map(segment_map)

                # Display segmentation results
                segment_col1, segment_col2 = st.columns(2)

                with segment_col1:
                    # Segment Distribution Pie Chart
                    segment_dist = patient_metrics["Segment"].value_counts().reset_index()
                    segment_dist.columns = ['Segment', 'Count']

                    fig = px.pie(
                        segment_dist,
                        values='Count',
                         names='Segment',
                         title="Patient Segment Distribution",
                         color_discrete_sequence=px.colors.qualitative.Set3,
                         template=PLOTLY_TEMPLATE # Apply template
                    )
                    fig.update_layout(height=400, margin=dict(t=40))
                    st.plotly_chart(fig, use_container_width=True)

                with segment_col2:
                    # Segment Characteristics Table
                    segment_stats = patient_metrics.groupby("Segment").agg(
                        Patient_Count=('Patient', 'count'),
                        Avg_Visits=('visit_count', 'mean'),
                        Avg_Total_Revenue=('total_revenue', 'mean'),
                        Avg_Revenue_Visit=('avg_revenue', 'mean'),
                        Avg_Visit_Duration=('avg_duration', 'mean')
                    ).round(2)

                    # segment_stats.columns = ["Patient Count", "Avg Visits", "Avg Total Revenue",
                    #                        "Avg Revenue/Visit", "Avg Visit Duration"] # Renamed in agg

                    st.dataframe(
                        segment_stats,
                        column_config={
                            "Patient_Count": st.column_config.NumberColumn("Patient Count", format="%d"),
                            "Avg_Visits": st.column_config.NumberColumn("Avg Visits", format="%.1f"),
                            "Avg_Total_Revenue": st.column_config.NumberColumn("Avg Total Revenue", format="EGP%.2f"),
                            "Avg_Revenue_Visit": st.column_config.NumberColumn("Avg Revenue/Visit", format="EGP%.2f"),
                            "Avg_Visit_Duration": st.column_config.NumberColumn("Avg Duration (mins)", format="%.1f")
                        }
                    )
            except Exception as e:
                 st.error(f"Error during clustering: {e}")

    else:
        st.info("Insufficient number of unique patients for segmentation (requires at least 3).")


    st.divider()

    # --- Patient Loyalty Analysis (RFM) ---
    st.subheader("🏆 Patient Loyalty Analysis (RFM)")

    if total_patients > 0:
        # Create a sample RFM (Recency, Frequency, Monetary) analysis
        snapshot_date = filtered_df['date'].max() + timedelta(days=1) # Day after last date in filtered data
        patient_rfm = filtered_df.groupby('Patient').agg(
            Recency=('date', lambda x: (snapshot_date - x.max()).days),
            Frequency=('id', 'count'),
            Monetary=('gross income', 'sum')
        ).reset_index()

        # Create scoring based on quantiles (adjust labels for clarity: 4=Best, 1=Worst)
        try:
            # Handle potential duplicate edges in quantiles
            patient_rfm['R_Score'] = pd.qcut(patient_rfm['Recency'], 4, labels=[1, 2, 3, 4], duplicates='drop') # Lower recency is better (4)
            patient_rfm['F_Score'] = pd.qcut(patient_rfm['Frequency'].rank(method='first'), 4, labels=[1, 2, 3, 4], duplicates='drop') # Higher frequency is better (4)
            patient_rfm['M_Score'] = pd.qcut(patient_rfm['Monetary'].rank(method='first'), 4, labels=[1, 2, 3, 4], duplicates='drop') # Higher monetary is better (4)

            # Convert scores to numeric for calculation if needed, handle potential NaNs from qcut
            patient_rfm[['R_Score', 'F_Score', 'M_Score']] = patient_rfm[['R_Score', 'F_Score', 'M_Score']].fillna(1).astype(int)

            # Calculate RFM Score (optional, segmentation below is often more useful)
            # patient_rfm['RFM_Score'] = patient_rfm['R_Score'].astype(str) + patient_rfm['F_Score'].astype(str) + patient_rfm['M_Score'].astype(str)

            # Define segments based on scores (example segmentation)
            def rfm_segment(row):
                r, f, m = row['R_Score'], row['F_Score'], row['M_Score']
                if r >= 4 and f >= 4: return 'Champions' # Recent, Frequent
                if r >= 3 and f >= 3: return 'Loyal Customers' # Fairly Recent, Fairly Frequent
                if r >= 3 and m >= 3: return 'Potential Loyalists' # Recent or High Value
                if r >= 4: return 'New Customers' # Very Recent, Low F/M
                if f >= 4: return 'Promising' # Frequent, but not recent
                if m >= 4: return 'Big Spenders' # High Value, but not recent/frequent
                if r <= 2 and f <= 2: return 'At Risk' # Not Recent, Not Frequent
                if r <= 2: return 'Hibernating' # Not Recent
                return 'Others' # Default category

            patient_rfm['Segment'] = patient_rfm.apply(rfm_segment, axis=1)

            # Display segment counts
            segment_counts = patient_rfm['Segment'].value_counts().reset_index()
            segment_counts.columns = ['Segment', 'Count']

            rfm_col1, rfm_col2 = st.columns([1, 2]) # Adjust column ratio

            with rfm_col1:
                fig = px.pie(
                    segment_counts,
                    values='Count',
                     names='Segment',
                     title='RFM Segmentation',
                     color_discrete_sequence=px.colors.qualitative.Bold,
                     template=PLOTLY_TEMPLATE # Apply template
                )
                fig.update_layout(height=500, margin=dict(t=40))
                st.plotly_chart(fig, use_container_width=True)

            with rfm_col2:
                # Action recommendations based on segments
                st.subheader("Recommended Actions")

                action_df = pd.DataFrame({
                    'Segment': ['Champions', 'Loyal Customers', 'Potential Loyalists', 'New Customers', 'Promising', 'Big Spenders', 'At Risk', 'Hibernating', 'Others'],
                    'Description': [
                        'Best customers: Recent, Frequent, High Value',
                        'Regular customers: Buy often',
                        'Recent or High Value, potential to be Loyal',
                        'Recent, but low frequency/value',
                        'Frequent, but haven\'t visited recently',
                        'High value, but infrequent/not recent',
                        'Low Recency & Frequency - may lose them',
                        'Low Recency - inactive for a while',
                        'Other less defined groups'
                    ],
                    'Recommended Action': [
                        'Reward, loyalty programs, early access',
                        'Upsell, ask for reviews, satisfaction surveys',
                        'Offer membership, recommend related services',
                        'Onboarding support, build relationship',
                        'Reactivation offers, personalized check-ins',
                        'Personalized offers based on past high-value purchases',
                        'Targeted reactivation campaigns, special discounts',
                        'Win-back offers, understand reasons for inactivity',
                        'Analyze further or monitor'
                    ]
                })

                # Merge counts with actions
                action_df = pd.merge(action_df, segment_counts, on='Segment', how='left').fillna({'Count': 0})
                action_df['Count'] = action_df['Count'].astype(int)

                st.dataframe(
                    action_df[['Segment', 'Count', 'Description', 'Recommended Action']].sort_values('Count', ascending=False),
                    hide_index=True,
                    use_container_width=True
                 )

        except ValueError as e:
            st.warning(f"Could not perform RFM segmentation due to data distribution issues (e.g., too few unique values for quantiles): {e}")
        except Exception as e:
            st.error(f"An unexpected error occurred during RFM analysis: {e}")

    else:
        st.info("No patient data available for RFM analysis.")
