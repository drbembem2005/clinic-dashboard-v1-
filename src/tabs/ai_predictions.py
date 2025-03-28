# src/tabs/ai_predictions.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import timedelta
from scipy import stats
from scipy.stats import zscore

# AI and ML imports - place necessary ones here
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import streamlit_mermaid as st_mermaid # Keep if mermaid chart is desired here
import calendar # Keep for calendar view

# Define a consistent color palette for charts
PLOTLY_TEMPLATE = "plotly_white" # Use a clean template

def render_ai_predictions_tab(filtered_df):
    """
    Renders the AI-Powered Predictions & Analytics tab content.

    Args:
        filtered_df (pd.DataFrame): The filtered DataFrame based on sidebar selections.
    """
    st.header("🤖 AI-Powered Predictions & Analytics")

    if filtered_df.empty:
        st.warning("No data available for the selected filters to perform AI analysis.")
        return # Stop rendering if no data

    # --- Forecasting Section ---
    st.subheader("🎯 Forecast Settings")
    settings_col1, settings_col2 = st.columns(2)

    with settings_col1:
        forecast_days = st.slider("Forecast Horizon (Days)", min_value=7, max_value=90, value=30, step=7, key="forecast_days_slider")
        confidence_level = st.slider("Confidence Level (%)", min_value=80, max_value=99, value=95, step=1, key="confidence_slider")

    with settings_col2:
        selected_metric = st.selectbox(
            "Select Metric to Forecast",
            options=["Revenue", "Visit Count", "Average Visit Duration"],
            index=0,
            key="forecast_metric_select"
        )

    st.divider()
    st.subheader(f"📈 {selected_metric} Forecast")

    # Prepare data for forecasting
    daily_data = filtered_df.groupby(filtered_df['date'].dt.date).agg(
        revenue=('gross income', 'sum'),
        visit_count=('id', 'count'),
        avg_duration=('visit_duration_mins', 'mean')
    ).reset_index()
    daily_data['date'] = pd.to_datetime(daily_data['date']) # Ensure datetime
    daily_data = daily_data.set_index('date').resample('D').asfreq().fillna(0).reset_index() # Ensure continuous daily data

    # Select the appropriate metric for forecasting
    if selected_metric == "Revenue":
        forecast_data_series = daily_data['revenue']
        y_label = "Predicted Revenue (EGP)"
        format_func = lambda x: f"EGP{x:,.2f}"
    elif selected_metric == "Visit Count":
        forecast_data_series = daily_data['visit_count']
        y_label = "Predicted Visit Count"
        format_func = lambda x: f"{x:,.0f}"
    else: # Average Visit Duration
        forecast_data_series = daily_data['avg_duration']
        y_label = "Predicted Avg Duration (mins)"
        format_func = lambda x: f"{x:.1f}"

    # Check if enough data for seasonal model
    min_data_points = 14 # Need at least 2 full seasons for seasonal='add'
    if len(forecast_data_series) >= min_data_points:
        try:
            # Fit the forecasting model (Holt-Winters Exponential Smoothing)
            forecast_model = ExponentialSmoothing(
                np.asarray(forecast_data_series, dtype=np.float64),
                trend='add',
                seasonal='add',
                seasonal_periods=7 # Weekly seasonality
            ).fit()

            # Generate forecast
            forecast_values = forecast_model.forecast(forecast_days)
            forecast_dates = pd.date_range(
                start=daily_data['date'].max() + pd.Timedelta(days=1),
                periods=forecast_days
            )

            # Calculate confidence intervals
            residuals = forecast_model.resid
            sigma = np.std(residuals) if len(residuals) > 1 else 0 # Avoid error if only 1 residual
            z_value = stats.norm.ppf((1 + confidence_level/100) / 2)

            ci_lower = forecast_values - z_value * sigma
            ci_upper = forecast_values + z_value * sigma
            # Ensure lower bound is not negative for counts/revenue/duration
            ci_lower = np.maximum(ci_lower, 0)

            # Create forecast plot
            fig_forecast = go.Figure() # Apply template in update_layout below

            # Add historical data
            fig_forecast.add_trace(go.Scatter(
                x=daily_data['date'],
                y=forecast_data_series,
                name='Historical',
                line=dict(color='blue')
            ))

            # Add forecast
            fig_forecast.add_trace(go.Scatter(
                x=forecast_dates,
                y=forecast_values,
                name='Forecast',
                line=dict(color='red', dash='dash')
            ))

            # Add confidence interval
            fig_forecast.add_trace(go.Scatter(
                x=forecast_dates.tolist() + forecast_dates.tolist()[::-1],
                y=ci_upper.tolist() + ci_lower.tolist()[::-1],
                fill='toself',
                fillcolor='rgba(255,0,0,0.1)',
                line=dict(color='rgba(255,0,0,0)'),
                name=f'{confidence_level}% Confidence Interval',
                hoverinfo='skip' # Don't show hover for the fill
            ))

            fig_forecast.update_layout(
                title=f"{selected_metric} Forecast - Next {forecast_days} Days",
                xaxis_title="Date",
                yaxis_title=y_label,
                height=500,
                template=PLOTLY_TEMPLATE, # Apply template
                hovermode='x unified',
                margin=dict(t=50)
            )

            st.plotly_chart(fig_forecast, use_container_width=True, key="ai_forecast_chart")

            # Forecast Insights
            st.subheader("🔍 Forecast Insights")
            insights_col1, insights_col2, insights_col3 = st.columns(3)

            with insights_col1:
                current_value = forecast_data_series.iloc[-1] if not forecast_data_series.empty else 0
                end_value = forecast_values[-1] if len(forecast_values) > 0 else 0
                change_pct = ((end_value - current_value) / current_value * 100) if current_value != 0 else 0
                st.metric(
                    f"End of Period ({forecast_dates[-1].strftime('%b %d')})",
                    format_func(end_value),
                    f"{change_pct:+.1f}% vs Current"
                )

            with insights_col2:
                avg_forecast = forecast_values.mean() if len(forecast_values) > 0 else 0
                avg_historical = forecast_data_series.mean() if not forecast_data_series.empty else 0
                avg_change_pct = ((avg_forecast - avg_historical) / avg_historical * 100) if avg_historical != 0 else 0
                st.metric(
                    "Average Forecast Value",
                    format_func(avg_forecast),
                    f"{avg_change_pct:+.1f}% vs Historical Avg"
                )

            with insights_col3:
                # Volatility (Coefficient of Variation)
                volatility = (forecast_values.std() / avg_forecast * 100) if avg_forecast != 0 else 0
                hist_volatility = (forecast_data_series.std() / avg_historical * 100) if avg_historical != 0 else 0
                vol_change = volatility - hist_volatility # Absolute change in % points
                st.metric(
                    "Forecast Volatility (CV %)",
                    f"{volatility:.1f}%",
                    f"{vol_change:+.1f} % points vs Historical"
                )

        except Exception as e:
            st.error(f"Error during forecasting: {e}")
            st.info("Ensure sufficient historical data (at least 14 days) for seasonal forecasting.")
    else:
        st.warning(f"Insufficient data ({len(forecast_data_series)} days) for seasonal forecasting. Need at least {min_data_points} days.")


    # --- Seasonality/Pattern Analysis ---
    st.divider()
    st.subheader("📊 Pattern Analysis")
    pattern_col1, pattern_col2 = st.columns(2)

    # Map selected metric to the actual column name in filtered_df
    if selected_metric == "Revenue":
        metric_col_name = 'gross income'
    elif selected_metric == "Visit Count":
        metric_col_name = 'id' # Assuming 'id' counts visits
    else: # Average Visit Duration
        metric_col_name = 'visit_duration_mins'

    # Choose aggregation method based on metric
    agg_method = 'mean' if selected_metric != "Visit Count" else 'count'


    with pattern_col1:
        # Daily Pattern (Day of Week)
        # Apply the correct aggregation method
        daily_pattern = filtered_df.groupby('day_of_week')[metric_col_name].agg(agg_method)
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_pattern = daily_pattern.reindex(day_order)

        fig_daily = px.bar(
            x=daily_pattern.index,
            y=daily_pattern.values,
            title=f'Average {selected_metric} by Day of Week',
            labels={'x': 'Day of Week', 'y': f'Average {selected_metric}'},
            template=PLOTLY_TEMPLATE # Apply template
        )
        fig_daily.update_layout(height=400, margin=dict(t=40))
        st.plotly_chart(fig_daily, use_container_width=True, key="ai_daily_pattern_chart")

    with pattern_col2:
        # Monthly Pattern (Month of Year)
        # Apply the correct aggregation method
        monthly_pattern = filtered_df.groupby(filtered_df['date'].dt.month)[metric_col_name].agg(agg_method)
        month_names = [calendar.month_name[i] for i in monthly_pattern.index]

        fig_monthly = px.line(
            x=month_names,
            y=monthly_pattern.values,
            title=f'Average {selected_metric} by Month',
            labels={'x': 'Month', 'y': f'Average {selected_metric}'},
            markers=True,
            template=PLOTLY_TEMPLATE # Apply template
        )
        # Ensure months are sorted correctly if index isn't already sorted 1-12
        fig_monthly.update_xaxes(categoryorder='array', categoryarray=month_names)
        fig_monthly.update_layout(height=400, margin=dict(t=40))
        st.plotly_chart(fig_monthly, use_container_width=True, key="ai_monthly_pattern_chart")


    # --- ML Model Comparison ---
    st.divider()
    st.subheader("🤖 ML Model Comparison for Revenue Prediction")
    st.info("Comparing simple models to predict next day's revenue based on past data.")

    # Prepare data for ML models (using daily aggregated data)
    ml_data = daily_data.copy().set_index('date') # Use date as index for shifting

    # Create lagged features for revenue
    target_col = 'revenue'
    for lag in range(1, 8): # Use previous 7 days
        ml_data[f'{target_col}_lag_{lag}'] = ml_data[target_col].shift(lag)

    # Create time-based features
    ml_data['day_of_week'] = ml_data.index.dayofweek
    ml_data['month'] = ml_data.index.month
    ml_data['day_of_year'] = ml_data.index.dayofyear
    ml_data['week_of_year'] = ml_data.index.isocalendar().week.astype(int)

    # Drop rows with NaN values created by lagging
    ml_data = ml_data.dropna()

    if not ml_data.empty and len(ml_data) > 10: # Need sufficient data for split
        # Define features (X) and target (y)
        feature_cols = [col for col in ml_data.columns if col != target_col]
        X = ml_data[feature_cols]
        y = ml_data[target_col]

        # Split data for training and testing (time series split might be better, but simple split for demo)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False) # No shuffle for time-based data

        # Initialize and train models
        models = {
            'Linear Regression': LinearRegression(),
            'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10, min_samples_split=5), # Tuned slightly
            'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, random_state=42, max_depth=5, learning_rate=0.05) # Tuned slightly
        }

        results = {}
        predictions = {}

        for name, model in models.items():
            try:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                predictions[name] = y_pred
                mae = mean_absolute_error(y_test, y_pred)
                mse = mean_squared_error(y_test, y_pred)
                results[name] = {'MAE': mae, 'MSE': mse, 'RMSE': np.sqrt(mse)}
            except Exception as e:
                st.warning(f"Could not train or evaluate model '{name}': {e}")
                results[name] = {'MAE': np.nan, 'MSE': np.nan, 'RMSE': np.nan}

        # Display results
        ml_col1, ml_col2 = st.columns(2)

        with ml_col1:
            st.subheader("Model Performance Metrics")
            st.markdown("""
            Comparing different machine learning models for predicting the next day's revenue.
            Lower values for MAE (Mean Absolute Error), MSE (Mean Squared Error), and RMSE (Root Mean Squared Error) indicate better performance.
             RMSE is in the same units as revenue (EGP).
             """)
            results_df = pd.DataFrame(results).T.sort_values('RMSE') # Sort by RMSE
            st.dataframe(results_df.style.format("{:,.2f}")) # Corrected indentation

            # Plot predictions vs actual
            fig_pred = go.Figure() # Apply template in update_layout below
            fig_pred.add_trace(go.Scatter(x=y_test.index, y=y_test, mode='lines', name='Actual Revenue', line=dict(color='black')))
            for name, y_pred in predictions.items():
                fig_pred.add_trace(go.Scatter(x=y_test.index, y=y_pred, mode='lines', name=f'{name} Prediction', line=dict(dash='dot')))

            fig_pred.update_layout(title='Model Predictions vs Actual Revenue (Test Set)',
                                   xaxis_title='Date', yaxis_title='Revenue (EGP)', height=400, template=PLOTLY_TEMPLATE, margin=dict(t=40)) # Apply template
            st.plotly_chart(fig_pred, use_container_width=True)


        with ml_col2:
            # Feature importance (only for tree-based models)
            st.subheader("Feature Importance (Tree Models)")
            st.markdown("""
            Shows which factors (features) the tree-based models (Random Forest, Gradient Boosting) considered most important when making revenue predictions.
            Higher values mean the feature had more influence. Lag features refer to revenue from previous days.
            """)
            importance_data = {}
            if 'Random Forest' in models and hasattr(models['Random Forest'], 'feature_importances_'):
                importance_data['Random Forest'] = models['Random Forest'].feature_importances_
            if 'Gradient Boosting' in models and hasattr(models['Gradient Boosting'], 'feature_importances_'):
                importance_data['Gradient Boosting'] = models['Gradient Boosting'].feature_importances_

            if importance_data:
                importance_df = pd.DataFrame(importance_data, index=feature_cols)
                importance_df = importance_df.mean(axis=1).sort_values(ascending=False).reset_index() # Average importance if multiple models
                importance_df.columns = ['Feature', 'Importance']

                fig_imp = px.bar(importance_df.head(10), # Show top 10
                                 x='Importance', y='Feature', orientation='h',
                                 title='Top 10 Feature Importances (Averaged)',
                                 template=PLOTLY_TEMPLATE) # Apply template
                fig_imp.update_layout(height=400, yaxis={'categoryorder':'total ascending'}, margin=dict(t=40, l=10))
                st.plotly_chart(fig_imp, use_container_width=True)
            else:
                st.info("No feature importance data available from trained models.")

    else:
        st.info("Insufficient daily data for ML model comparison (requires > 10 days after processing).")


    # --- Advanced Patient Segmentation (PCA + K-Means) ---
    # This was already present in the patient insights tab, maybe keep it there?
    # Or refine it here if desired. For now, commenting out to avoid duplication.
    # st.divider()
    # st.subheader("🧩 Advanced Patient Segmentation (PCA + K-Means)")
    # ... (Code from original tabs[5] for PCA + K-Means) ...

    # --- Calendar Heatmap ---
    # This was also in the original tabs[5], maybe better suited for Operational or Patient tabs?
    # Commenting out for now.
    # st.divider()
    # st.subheader("📅 Monthly Patient Distribution Calendar")
    # ... (Code for calendar heatmap) ...

    # --- Combined Analytics View ---
    # This subplot view might be better placed in the Executive Summary or a dedicated 'Overview' tab.
    # Commenting out for now.
    # st.divider()
    # st.subheader("📊 Combined Analytics View (Subplots)")
    # ... (Code for make_subplots) ...

    # --- Mermaid Diagram ---
    # This seems more related to process flow, maybe Operational or a dedicated Process tab?
    # Commenting out for now.
    # st.divider()
    # st.subheader("📊 Patient Journey Flow")
    # ... (Code for mermaid chart) ...
