import streamlit as st
import pandas as pd

class DataManagementView:
    """
    Manages the display and interaction for data management,
    such as previewing the uploaded dataset.
    """

    def __init__(self):
        """
        Initializes the DataManagementView.
        """
        pass

    def render_data_preview(self, df: pd.DataFrame):
        """
        Renders a preview of the uploaded DataFrame.

        Args:
            df (pd.DataFrame): The DataFrame to display.
        """
        if not df.empty:
            st.subheader("📊 Uploaded Data Preview")
            st.info(f"Showing first {min(len(df), 10)} rows of your dataset (Total rows: {len(df)}).")
            st.dataframe(df.head(10), use_container_width=True)
            
        else:
            st.info("No data uploaded yet. Please upload a CSV or JSON file from the sidebar.")

