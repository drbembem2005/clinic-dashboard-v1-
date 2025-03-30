# src/tabs/cost_entry.py
import streamlit as st
import pandas as pd
from datetime import date, datetime
import sys
import os

# Add src directory to Python path if needed (alternative to modifying in main.py)
# This makes the tab runnable independently for testing if necessary
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..') # Go up one level to src
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    # Import necessary functions from data_loader
    from data_loader import add_cost, get_costs
except ImportError:
    st.error("Could not import database functions from data_loader.py. Ensure it's in the src directory.")
    st.stop()

# Define common cost categories
COMMON_CATEGORIES = [
    "Salaries",
    "Rent",
    "Utilities",
    "Supplies",
    "Marketing",
    "Maintenance",
    "Insurance",
    "Taxes",
    "Other" # Keep 'Other' as an option
]

def render_cost_entry_tab():
    """Renders the cost entry form and recent entries table."""
    st.header("💸 Cost Entry")
    st.markdown("Use this form to record clinic expenses.")

    with st.form("cost_entry_form", clear_on_submit=True):
        st.subheader("Enter New Cost")
        col1, col2, col3 = st.columns(3) # Use 3 columns
        with col1:
            expense_date = st.date_input("Expense Date", value=date.today(), help="Date the expense was incurred.") # Renamed and added help
            category_selection = st.selectbox("Category", options=COMMON_CATEGORIES, index=len(COMMON_CATEGORIES)-1) # Default to 'Other'
            # Allow custom category if 'Other' is selected
            if category_selection == "Other":
                category = st.text_input("Enter Custom Category", key="custom_category_input")
            else: # Corrected: Only one else needed here
                category = category_selection

        with col2:
            item = st.text_input("Item/Description", placeholder="e.g., Electricity Bill, Nurse Salary, Gloves")
            # Add Payment Date input - make it optional
            payment_date = st.date_input("Payment Date (Optional)", value=None, help="Date the expense was paid. Leave blank if unpaid.")

        with col3: # Moved amount to 3rd column
            amount = st.number_input("Amount (EGP)", min_value=0.0, format="%.2f", step=10.0)

        submitted = st.form_submit_button("Add Cost Entry")

        if submitted:
            # Basic validation
            # Basic validation
            final_category = category.strip() if category_selection == "Other" else category_selection
            final_item = item.strip()

            if not expense_date: # Check expense_date
                st.warning("Please select an Expense Date.")
            elif not final_category:
                st.warning("Please select or enter a category.")
            elif not final_item:
                st.warning("Please enter an item/description.")
            elif amount <= 0:
                st.warning("Please enter a valid amount greater than zero.")
            else:
                # Attempt to add the cost to the database, passing both dates
                # Use expense_date and payment_date variables from the form
                success = add_cost(expense_date, payment_date, final_category, final_item, amount)
                if success:
                    payment_date_str = f" (Paid: {payment_date})" if payment_date else " (Unpaid)"
                    st.success(f"Cost entry added: {final_category} - {final_item} (EGP {amount:.2f}) on {expense_date}{payment_date_str}")
                    # Clear custom category input if it was used
                    if category_selection == "Other":
                         st.session_state.custom_category_input = "" # Attempt to clear if needed, might require rerun
                else:
                    st.error("Failed to add cost entry to the database.")

    st.divider()

    # Display recent cost entries
    st.subheader("Recent Cost Entries")
    try:
        # Fetch the last N entries (e.g., 10)
        df_recent_costs = get_costs() # Get all costs first
        if not df_recent_costs.empty:
             # Sort by recorded_at descending to be sure, although query does it
             # Sort by recorded_at descending to be sure, although query does it
             df_recent_costs = df_recent_costs.sort_values(by='recorded_at', ascending=False)
             # Select columns to display and format - Use new date columns
             display_cols = ['expense_date', 'payment_date', 'category', 'item', 'amount']
             df_display = df_recent_costs[display_cols].head(10) # Show top 10 most recent
             # Format dates nicely, handle potential NaT for payment_date
             df_display['expense_date'] = pd.to_datetime(df_display['expense_date']).dt.strftime('%Y-%m-%d')
             df_display['payment_date'] = pd.to_datetime(df_display['payment_date']).dt.strftime('%Y-%m-%d').replace('NaT', 'Unpaid') # Format and handle unpaid
             df_display['amount'] = df_display['amount'].map('{:,.2f}'.format) # Format amount
             st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
             st.info("No cost entries found in the database yet.")

    except Exception as e:
        st.error(f"An error occurred while fetching recent costs: {e}")
