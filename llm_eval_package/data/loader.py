import pandas as pd
import json
from llm_eval_package.config import REQUIRED_COLUMNS # Updated import path
import streamlit as st

class DataLoader:
    """
    Handles loading and validating input data for LLM evaluation.
    Supports CSV and JSON file formats.
    """

    def __init__(self):
        """
        Initializes the DataLoader.
        """
        pass

    def load_data(self, file_uploader) -> pd.DataFrame:
        """
        Loads data from an uploaded file (CSV or JSON) and performs validation.

        Args:
            file_uploader: The Streamlit file uploader object.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the loaded data.

        Raises:
            ValueError: If the file format is unsupported or required columns are missing.
        """
        if file_uploader is not None:
            file_extension = file_uploader.name.split('.')[-1].lower()

            if file_extension == 'csv':
                df = self._load_csv(file_uploader)
            elif file_extension == 'json':
                df = self._load_json(file_uploader)
            else:
                st.error("Unsupported file format. Please upload a CSV or JSON file.")
                st.stop() # Stop execution if format is unsupported

            self._validate_columns(df)
            return df
        return pd.DataFrame() # Return empty DataFrame if no file is uploaded

    def _load_csv(self, file_uploader) -> pd.DataFrame:
        """
        Loads data from a CSV file.

        Args:
            file_uploader: The Streamlit file uploader object for the CSV file.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the CSV data.
        """
        return pd.read_csv(file_uploader)

    def _load_json(self, file_uploader) -> pd.DataFrame:
        """
        Loads data from a JSON file.

        Args:
            file_uploader: The Streamlit file uploader object for the JSON file.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the JSON data.
        """
        # Read the file content as a string
        json_data = file_uploader.read().decode('utf-8')
        # Parse the JSON string into a Python object
        data = json.loads(json_data)
        return pd.DataFrame(data)

    def _validate_columns(self, df: pd.DataFrame):
        """
        Validates if the DataFrame contains all required columns.

        Args:
            df (pd.DataFrame): The DataFrame to validate.

        Raises:
            ValueError: If any required column is missing.
        """
        # Only check for the truly mandatory columns for evaluation
        mandatory_cols = ['query', 'llm_output', 'reference_answer']
        missing_columns = [col for col in mandatory_cols if col not in df.columns]
        if missing_columns:
            st.error(f"Missing required columns: {', '.join(missing_columns)}. "
                     f"Please ensure your file contains: {', '.join(mandatory_cols)}")
            st.stop() # Stop execution if columns are missing

        # Check for optional columns and add them if missing, filling with empty strings
        for col in REQUIRED_COLUMNS: # <-- This uses the global REQUIRED_COLUMNS
            if col not in df.columns:
                df[col] = '' # Add missing optional columns with empty string