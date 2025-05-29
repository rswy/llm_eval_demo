import streamlit as st
import pandas as pd
import sys
import os
import io # For handling byte stream for pandas
import traceback # For more detailed error logging in UI if needed

# Add the project root to sys.path if running streamlit_app.py directly from its location
# This assumes streamlit_app.py is in the project root.
# If llm_eval_package is in a subdirectory, adjust path accordingly.
project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root_path not in sys.path:
    sys.path.insert(0, project_root_path)

from llm_eval_package.data.loader import DataLoader
from llm_eval_package.core.engine import Evaluator
from llm_eval_package.ui.sidebar_view import SidebarView, BOT_DOMAIN_MAPPING # Assuming BOT_DOMAIN_MAPPING is here
from llm_eval_package.ui.data_view import DataManagementView
from llm_eval_package.ui.results_view import ResultsView
from llm_eval_package.ui.tutorial_view import TutorialView
from llm_eval_package.config import (
    METRIC_THRESHOLDS,
    DEFAULT_PASS_CRITERION # Import default pass criterion
)

# Import the function for fetching responses and its defaults
from llm_eval_package.data.rag_input_processor import (
    fetch_bot_responses as fetch_bot_responses_from_file, # Renamed for clarity
    DEFAULT_API_URL,
    DEFAULT_API_HEADERS # To potentially show user the default or for modification
)

# Helper function to adapt fetch_bot_responses for DataFrames (in-memory processing)
def fetch_bot_responses_for_df(
    input_df: pd.DataFrame,
    query_column: str,
    selected_domain_key: str,
    api_token: str = None # Allow passing token explicitly
    ) -> pd.DataFrame:
    if input_df.empty:
        st.warning("Input DataFrame is empty. Cannot fetch responses.")
        return input_df.copy() # Return a copy to avoid modifying original on warning
    if query_column not in input_df.columns:
        st.error(f"Query column '{query_column}' not found in the uploaded data.")
        return input_df.copy()

    # Use BytesIO for in-memory CSV handling to reuse file-based fetch_bot_responses
    temp_input_csv_stream = io.BytesIO()
    input_df.to_csv(temp_input_csv_stream, index=False, encoding='utf-8')
    temp_input_csv_stream.seek(0) # Rewind the stream to the beginning for reading

    temp_output_csv_stream = io.BytesIO()

    try:
        current_api_headers = DEFAULT_API_HEADERS.copy()
        if api_token:
            current_api_headers["Authorization"] = f"Bearer {api_token}"
        elif "YOUR_EXPIRED_OR_PLACEHOLDER_TOKEN_HERE" in current_api_headers.get("Authorization", ""):
             st.warning("Using a placeholder API token. Update `llm_eval_package/data/rag_input_processor.py` or provide a token in the UI if fetching fails.", icon="⚠️")

        # The 'domains' parameter is left as None to use the default from rag_input_processor
        # fetch_bot_responses_from_file is designed to handle stream objects for paths
        fetch_bot_responses_from_file(
            input_csv_path=temp_input_csv_stream,
            output_csv_path=temp_output_csv_stream,
            query_column=query_column,
            domain_key=selected_domain_key, # This key must be valid in rag_input_processor's DEFAULT_DOMAINS
            api_url=DEFAULT_API_URL, # Or make this configurable via UI if needed
            api_headers=current_api_headers,
            domains=None # Uses default domains from rag_input_processor.py
        )
        
        temp_output_csv_stream.seek(0) # Rewind after writing
        if temp_output_csv_stream.getbuffer().nbytes > 0: # Check if stream has content
            output_df = pd.read_csv(temp_output_csv_stream)
            # Calculate number of successfully fetched responses (not empty and not starting with "Error:")
            valid_responses_mask = output_df['llm_output'].notna() & ~output_df['llm_output'].astype(str).str.startswith('Error:')
            num_valid_responses = valid_responses_mask.sum()
            st.success(f"Successfully processed {len(output_df)} queries. Fetched {num_valid_responses} valid responses.")
            if num_valid_responses < len(output_df):
                st.warning(f"{len(output_df) - num_valid_responses} queries might have resulted in errors. Check 'llm_output' column for details like 'Error: ...'.")
            return output_df
        else:
            st.error("API call might have completed but no data was written to the output stream. Check API logic and connectivity.")
            return input_df.copy() # Return original on error

    except Exception as e:
        st.error(f"Error during fetching bot responses: {e}")
        st.error(f"Traceback: {traceback.format_exc()}")
        return input_df.copy() # Return original on error
    finally:
        temp_input_csv_stream.close()
        temp_output_csv_stream.close()


def main():
    st.set_page_config(
        page_title="Genius AI LLM Evaluator",
        page_icon="✨",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize components
    data_loader = DataLoader()
    evaluator = Evaluator()
    sidebar_view = SidebarView()
    data_management_view = DataManagementView()
    results_view = ResultsView()
    tutorial_view = TutorialView()

    # Session state initialization
    if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()
    if 'df_evaluated' not in st.session_state: st.session_state.df_evaluated = pd.DataFrame()
    if 'show_results' not in st.session_state: st.session_state.show_results = False
    if 'selected_metrics_for_results' not in st.session_state: st.session_state.selected_metrics_for_results = []
    if 'custom_thresholds_for_results' not in st.session_state: st.session_state.custom_thresholds_for_results = None
    if 'show_tutorial' not in st.session_state: st.session_state.show_tutorial = True
    if 'file_uploader_key' not in st.session_state: st.session_state.file_uploader_key = 0
    if 'sidebar_inputs' not in st.session_state: st.session_state.sidebar_inputs = {} # To store all sidebar outputs
    if 'selected_domain_key' not in st.session_state:
        st.session_state.selected_domain_key = list(BOT_DOMAIN_MAPPING.keys())[0] if BOT_DOMAIN_MAPPING else "SG Branch" # Default domain
    if 'api_token_input' not in st.session_state: st.session_state.api_token_input = ""
    if 'selected_overall_criterion' not in st.session_state:
        st.session_state.selected_overall_criterion = DEFAULT_PASS_CRITERION
    if 'uploaded_file_name' not in st.session_state: st.session_state.uploaded_file_name = None


    # Render sidebar and get user inputs
    sidebar_outputs = sidebar_view.render_sidebar(st.session_state.file_uploader_key)
    st.session_state.sidebar_inputs = {
        'uploaded_file': sidebar_outputs[0],
        'selected_metrics': sidebar_outputs[1],
        'custom_thresholds': sidebar_outputs[3],
        'sensitive_keywords': sidebar_outputs[4],
        'selected_task_type': sidebar_outputs[5], # Will be default if task selection disabled
        'go_to_instructions': sidebar_outputs[6],
        'selected_domain_key': sidebar_outputs[7],
        'selected_overall_criterion': sidebar_outputs[8]
    }
    # Update specific session state vars for easier access if needed elsewhere
    st.session_state.selected_domain_key = st.session_state.sidebar_inputs['selected_domain_key']
    st.session_state.selected_overall_criterion = st.session_state.sidebar_inputs['selected_overall_criterion']


    # Handle "Go to Instructions" button click
    if st.session_state.sidebar_inputs['go_to_instructions']:
        st.session_state.show_tutorial = True
        st.session_state.show_results = False # Hide results if going to tutorial
        st.session_state.df_original = pd.DataFrame() # Clear data to show fresh tutorial
        st.session_state.df_evaluated = pd.DataFrame() # Clear evaluated data
        st.session_state.file_uploader_key += 1 # Increment key to reset file uploader
        st.session_state.uploaded_file_name = None
        st.rerun()

    # Main Title and Header
    st.markdown(
        """
        <style>
        .main-header {font-size: 3em; font-weight: bold; color: #4CAF50; text-align: center; margin-bottom: 0.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.1);}
        .subheader {font-size: 1.5em; color: #555; text-align: center; margin-bottom: 1em;}
        .stButton>button {background-color: #4CAF50; color: white; border-radius: 12px; padding: 10px 24px; font-size: 1.2em; border: none; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); transition: 0.3s;}
        .stButton>button:hover {background-color: #45a049; box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);}
        .stAlert {border-radius: 10px;}
        </style>
        <h1 class="main-header">✨ BYOB Evaluator ✨</h1>
        <h5 class="subheader">A Tool by Genius AI</h5>
        """,
        unsafe_allow_html=True
    )

    # Determine if we should show the tutorial
    should_show_tutorial_now = st.session_state.show_tutorial and \
                               st.session_state.sidebar_inputs['uploaded_file'] is None and \
                               st.session_state.df_original.empty and \
                               st.session_state.df_evaluated.empty

    if should_show_tutorial_now:
        tutorial_view.render_tutorial()
        return # Exit main to avoid further processing if tutorial is active
    else:
        if st.session_state.show_tutorial: # Ensure flag is False if conditions changed
            st.session_state.show_tutorial = False

    # Data loading and preview logic
    uploaded_file_obj = st.session_state.sidebar_inputs['uploaded_file']
    if uploaded_file_obj is not None:
        # Load data if it's a new file or if df_original is empty
        if st.session_state.df_original.empty or st.session_state.uploaded_file_name != uploaded_file_obj.name:
            try:
                with st.spinner(f"Loading data from {uploaded_file_obj.name}..."):
                    st.session_state.df_original = data_loader.load_data(uploaded_file_obj)
                    st.session_state.uploaded_file_name = uploaded_file_obj.name # Store name of loaded file
                st.session_state.df_evaluated = pd.DataFrame() # Clear previous evaluation
                st.session_state.show_results = False
                st.session_state.show_tutorial = False # Successfully loaded data, so hide tutorial
                data_management_view.render_data_preview(st.session_state.df_original)
            except Exception as e:
                st.error(f"Error loading or validating data: {e}")
                st.session_state.df_original = pd.DataFrame()
                st.session_state.df_evaluated = pd.DataFrame()
                st.session_state.show_results = False
                st.session_state.show_tutorial = True # Go back to tutorial on data error
                st.session_state.file_uploader_key += 1
                st.session_state.uploaded_file_name = None
                st.rerun()
                return # Stop execution if data loading fails
        else: # File is already loaded and matches current df_original source
            data_management_view.render_data_preview(st.session_state.df_original)
    elif not st.session_state.df_original.empty: # No new file, but data exists in session
        data_management_view.render_data_preview(st.session_state.df_original)
    # else: No file and no df_original -> tutorial should be showing or app is in initial state after instructions


    # --- Button to Fetch Bot Responses ---
    if not st.session_state.df_original.empty: # Show only if data is loaded and ready for queries
        st.markdown("---")
        st.subheader("Fetch Live Bot Responses (Optional)")
        st.caption("This uses the 'query' column from your currently loaded data to call the selected Bot API and updates the 'llm_output' column.")
        
        st.session_state.api_token_input = st.text_input(
            "API Authorization Token (Bearer)",
            type="password",
            value=st.session_state.api_token_input,
            help="Optional: Enter your API token. If blank, a default from the application's configuration will be attempted."
        )

        if st.button("🔗 Fetch Bot Responses & Update Data", help="Calls API and replaces/adds 'llm_output' column in the current dataset."):
            if 'query' not in st.session_state.df_original.columns:
                st.error("The current data must contain a 'query' column to fetch responses.")
            else:
                with st.spinner(f"Fetching responses for {len(st.session_state.df_original)} queries using domain '{st.session_state.selected_domain_key}'... This may take some time."):
                    token_to_use = st.session_state.api_token_input if st.session_state.api_token_input.strip() else None
                    
                    # Operate on a copy to avoid partial updates if errors occur mid-process
                    df_for_fetching = st.session_state.df_original.copy()
                    
                    updated_df = fetch_bot_responses_for_df(
                        input_df=df_for_fetching,
                        query_column='query',
                        selected_domain_key=st.session_state.selected_domain_key,
                        api_token=token_to_use
                    )
                    # Only update session state if the process was somewhat successful (returned a df)
                    if updated_df is not None:
                        st.session_state.df_original = updated_df # Update the main dataframe
                        st.session_state.df_evaluated = pd.DataFrame() # Clear previous evaluation results
                        st.session_state.show_results = False
                        st.experimental_rerun() # Rerun to refresh the data preview immediately and clear old eval results display
                    else:
                        st.error("Fetching responses failed to return an updated dataset.")
    
    # --- Run Evaluation Button ---
    run_evaluation_button_clicked = False
    if not st.session_state.df_original.empty:
        col1, col2, col3 = st.columns([1, 2, 1]) 
        with col2:
            run_evaluation_button_clicked = st.button("🚀 Run Evaluation", help="Click to start the evaluation process on the current data.", use_container_width=True)
        st.markdown("---")

    if run_evaluation_button_clicked and not st.session_state.df_original.empty:
        if 'llm_output' not in st.session_state.df_original.columns or st.session_state.df_original['llm_output'].isnull().all():
            st.error("The 'llm_output' column is missing or entirely empty in the data. Please fetch bot responses or ensure your uploaded data includes it before running evaluation.")
        elif not st.session_state.sidebar_inputs['selected_metrics']:
            st.warning("Please select at least one metric to run the evaluation.")
        else:
            with st.spinner("Running evaluation... This may take a while for large datasets."):
                try:
                    st.session_state.df_evaluated = evaluator.evaluate_dataframe(
                        st.session_state.df_original.copy(),
                        st.session_state.sidebar_inputs['selected_metrics'],
                        custom_thresholds=st.session_state.sidebar_inputs['custom_thresholds'],
                        sensitive_keywords=st.session_state.sidebar_inputs['sensitive_keywords'],
                        overall_pass_criterion=st.session_state.selected_overall_criterion # Pass the criterion
                    )
                    st.session_state.show_results = True
                    st.session_state.selected_metrics_for_results = st.session_state.sidebar_inputs['selected_metrics']
                    st.session_state.custom_thresholds_for_results = st.session_state.sidebar_inputs['custom_thresholds']
                    st.session_state.show_tutorial = False # Hide tutorial if evaluation runs
                except Exception as e:
                    st.error(f"An error occurred during evaluation: {e}")
                    st.error(f"Traceback: {traceback.format_exc()}") # Show full traceback in UI for debug
                    st.session_state.show_results = False
                    # Consider if resetting to tutorial is appropriate here or just show error
    elif run_evaluation_button_clicked and st.session_state.df_original.empty:
        st.warning("Please upload a dataset before running the evaluation.")
        # st.session_state.show_tutorial = True # Optionally revert to tutorial
        # st.session_state.file_uploader_key += 1
        # st.rerun()

    # Display results if evaluation has been run
    if st.session_state.show_results and not st.session_state.df_evaluated.empty:
        results_view.render_results(
            st.session_state.df_evaluated,
            st.session_state.selected_metrics_for_results,
            st.session_state.custom_thresholds_for_results
            # The overall_pass_fail_column is now hardcoded as "Overall Pass/Fail" in results_view
        )
        
        # Option to download results
        csv_output = st.session_state.df_evaluated.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Full Results as CSV",
            data=csv_output,
            file_name="llm_evaluation_results.csv",
            mime="text/csv",
        )

if __name__ == "__main__":
    main()




# import streamlit as st
# import pandas as pd
# import sys
# import os
# import io # For handling byte stream for pandas

# project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
# if project_root_path not in sys.path:
#     sys.path.insert(0, project_root_path)

# from llm_eval_package.data.loader import DataLoader
# from llm_eval_package.core.engine import Evaluator
# # from llm_eval_package.core.reporting import Reporter # Reporter is more for CLI or non-Streamlit context
# from llm_eval_package.ui.sidebar_view import SidebarView, BOT_DOMAIN_MAPPING
# from llm_eval_package.ui.data_view import DataManagementView
# from llm_eval_package.ui.results_view import ResultsView
# from llm_eval_package.ui.tutorial_view import TutorialView
# from llm_eval_package.config import METRIC_THRESHOLDS

# from llm_eval_package.data.rag_input_processor import (
#     fetch_bot_responses as fetch_bot_responses_from_file, # Renamed for clarity
#     DEFAULT_API_URL,
#     DEFAULT_API_HEADERS
# )

# # Helper function to adapt fetch_bot_responses for DataFrames
# def fetch_bot_responses_for_df(
#     input_df: pd.DataFrame,
#     query_column: str,
#     selected_domain_key: str,
#     api_token: str = None
#     ) -> pd.DataFrame:
#     if input_df.empty:
#         st.warning("Input DataFrame is empty. Cannot fetch responses.")
#         return input_df.copy() # Return a copy to avoid modifying original on warning
#     if query_column not in input_df.columns:
#         st.error(f"Query column '{query_column}' not found in the uploaded data.")
#         return input_df.copy()

#     # Use BytesIO for in-memory CSV handling
#     temp_input_csv_stream = io.BytesIO()
#     input_df.to_csv(temp_input_csv_stream, index=False, encoding='utf-8')
#     temp_input_csv_stream.seek(0) # Rewind the stream to the beginning for reading

#     temp_output_csv_stream = io.BytesIO()

#     try:
#         current_api_headers = DEFAULT_API_HEADERS.copy()
#         if api_token:
#             current_api_headers["Authorization"] = f"Bearer {api_token}"
#         elif "YOUR_EXPIRED_OR_PLACEHOLDER_TOKEN_HERE" in current_api_headers.get("Authorization", ""):
#              st.warning("Using a placeholder API token. Update `llm_eval_package/data/rag_input_processor.py` or provide a token in the UI if fetching fails.", icon="⚠️")

#         fetch_bot_responses_from_file(
#             input_csv_path=temp_input_csv_stream, # Pass the stream
#             output_csv_path=temp_output_csv_stream, # Pass the stream
#             query_column=query_column,
#             domain_key=selected_domain_key,
#             api_url=DEFAULT_API_URL,
#             api_headers=current_api_headers,
#             domains=None # Uses default from rag_input_processor.py
#         )
        
#         temp_output_csv_stream.seek(0) # Rewind after writing
#         if temp_output_csv_stream.getbuffer().nbytes > 0: # Check if stream has content
#             output_df = pd.read_csv(temp_output_csv_stream)
#             valid_responses_mask = output_df['llm_output'].notna() & ~output_df['llm_output'].astype(str).str.startswith('Error:')
#             num_valid_responses = valid_responses_mask.sum()
#             st.success(f"Successfully processed {len(output_df)} queries. Fetched {num_valid_responses} valid responses.")
#             if num_valid_responses < len(output_df):
#                 st.warning(f"{len(output_df) - num_valid_responses} queries might have resulted in errors. Check 'llm_output' column.")
#             return output_df
#         else:
#             st.error("API call completed but no data was written to the output stream. Check API logic.")
#             return input_df.copy()

#     except Exception as e:
#         st.error(f"Error during fetching bot responses: {e}")
#         import traceback
#         st.error(f"Traceback: {traceback.format_exc()}")
#         return input_df.copy()
#     finally:
#         temp_input_csv_stream.close()
#         temp_output_csv_stream.close()


# def main():
#     st.set_page_config(
#         page_title="Genius AI LLM Evaluator",
#         page_icon="✨",
#         layout="wide",
#         initial_sidebar_state="expanded"
#     )

#     data_loader = DataLoader()
#     evaluator = Evaluator()
#     # reporter = Reporter() # Not used directly in Streamlit app's main flow
#     sidebar_view = SidebarView()
#     data_management_view = DataManagementView()
#     results_view = ResultsView()
#     tutorial_view = TutorialView()

#     # Initialize session state variables
#     if 'df_original' not in st.session_state: st.session_state.df_original = pd.DataFrame()
#     if 'df_evaluated' not in st.session_state: st.session_state.df_evaluated = pd.DataFrame()
#     if 'show_results' not in st.session_state: st.session_state.show_results = False
#     if 'selected_metrics_for_results' not in st.session_state: st.session_state.selected_metrics_for_results = []
#     if 'custom_thresholds_for_results' not in st.session_state: st.session_state.custom_thresholds_for_results = None
#     if 'show_tutorial' not in st.session_state: st.session_state.show_tutorial = True
#     if 'file_uploader_key' not in st.session_state: st.session_state.file_uploader_key = 0
#     if 'sidebar_inputs' not in st.session_state: st.session_state.sidebar_inputs = {}
#     if 'selected_domain_key' not in st.session_state:
#         st.session_state.selected_domain_key = list(BOT_DOMAIN_MAPPING.keys())[0] if BOT_DOMAIN_MAPPING else "SG Branch"
#     if 'api_token_input' not in st.session_state: st.session_state.api_token_input = ""
#     if 'uploaded_file_name' not in st.session_state: st.session_state.uploaded_file_name = None


#     sidebar_outputs = sidebar_view.render_sidebar(st.session_state.file_uploader_key)
#     st.session_state.sidebar_inputs = {
#         'uploaded_file': sidebar_outputs[0],
#         'selected_metrics': sidebar_outputs[1],
#         'custom_thresholds': sidebar_outputs[3],
#         'sensitive_keywords': sidebar_outputs[4],
#         'selected_task_type': sidebar_outputs[5],
#         'go_to_instructions': sidebar_outputs[6],
#         'selected_domain_key': sidebar_outputs[7]
#     }
#     st.session_state.selected_domain_key = sidebar_outputs[7]

#     if st.session_state.sidebar_inputs['go_to_instructions']:
#         st.session_state.show_tutorial = True
#         st.session_state.show_results = False
#         st.session_state.df_original = pd.DataFrame()
#         st.session_state.df_evaluated = pd.DataFrame()
#         st.session_state.file_uploader_key += 1
#         st.rerun()

#     st.markdown(
#         """
#         <style>
#         .main-header {font-size: 3em; font-weight: bold; color: #4CAF50; text-align: center; margin-bottom: 0.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.1);}
#         .subheader {font-size: 1.5em; color: #555; text-align: center; margin-bottom: 1em;}
#         .stButton>button {background-color: #4CAF50; color: white; border-radius: 12px; padding: 10px 24px; font-size: 1.2em; border: none; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); transition: 0.3s;}
#         .stButton>button:hover {background-color: #45a049; box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);}
#         .stAlert {border-radius: 10px;}
#         </style>
#         <h1 class="main-header">✨ BYOB EVALUATOR ✨</h1>
#         <h5 class="subheader">A Genius AI Product</h5>
#         """,
#         unsafe_allow_html=True
#     )

#     should_show_tutorial_now = st.session_state.show_tutorial and \
#                                st.session_state.sidebar_inputs['uploaded_file'] is None and \
#                                st.session_state.df_original.empty and \
#                                st.session_state.df_evaluated.empty

#     if should_show_tutorial_now:
#         tutorial_view.render_tutorial()
#         return
#     else:
#         if st.session_state.show_tutorial: # Ensure flag is false if not showing tutorial
#             st.session_state.show_tutorial = False

#     # Data loading and preview logic
#     uploaded_file_obj = st.session_state.sidebar_inputs['uploaded_file']
#     if uploaded_file_obj is not None:
#         # Load data if it's a new file or if df_original is empty
#         if st.session_state.df_original.empty or st.session_state.uploaded_file_name != uploaded_file_obj.name:
#             try:
#                 st.session_state.df_original = data_loader.load_data(uploaded_file_obj)
#                 st.session_state.uploaded_file_name = uploaded_file_obj.name
#                 st.session_state.df_evaluated = pd.DataFrame() # Clear previous evaluation
#                 st.session_state.show_results = False
#                 st.session_state.show_tutorial = False
#                 data_management_view.render_data_preview(st.session_state.df_original)
#             except Exception as e:
#                 st.error(f"Error loading or validating data: {e}")
#                 st.session_state.df_original = pd.DataFrame()
#                 st.session_state.df_evaluated = pd.DataFrame()
#                 st.session_state.show_results = False
#                 st.session_state.show_tutorial = True
#                 st.session_state.file_uploader_key += 1
#                 st.rerun()
#                 return
#         else: # File is already loaded and matches current df_original source
#             data_management_view.render_data_preview(st.session_state.df_original)
#     elif not st.session_state.df_original.empty: # No new file, but data exists in session
#         data_management_view.render_data_preview(st.session_state.df_original)


#     # --- Button to Fetch Bot Responses ---
#     if not st.session_state.df_original.empty: # Show only if data is loaded
#         st.markdown("---")
#         st.subheader("Fetch Live Bot Responses (Optional)")
        
#         st.session_state.api_token_input = st.text_input(
#             "API Authorization Token (Bearer)",
#             type="password",
#             value=st.session_state.api_token_input,
#             help="Optional: Enter API token. Overrides default from code."
#         )

#         if st.button("🔗 Fetch Bot Responses & Update Data", help="Uses 'query' column from current data, calls API for selected domain, updates 'llm_output'."):
#             if 'query' not in st.session_state.df_original.columns:
#                 st.error("The current data must contain a 'query' column to fetch responses.")
#             else:
#                 with st.spinner(f"Fetching responses for {len(st.session_state.df_original)} queries using domain '{st.session_state.selected_domain_key}'..."):
#                     token_to_use = st.session_state.api_token_input if st.session_state.api_token_input.strip() else None
                    
#                     updated_df = fetch_bot_responses_for_df(
#                         input_df=st.session_state.df_original.copy(), # Operate on a copy
#                         query_column='query',
#                         selected_domain_key=st.session_state.selected_domain_key,
#                         api_token=token_to_use
#                     )
#                     st.session_state.df_original = updated_df # Update the main dataframe
#                     st.session_state.df_evaluated = pd.DataFrame() 
#                     st.session_state.show_results = False
#                     st.experimental_rerun() 
    
#     # --- Run Evaluation Button ---
#     run_evaluation_button_clicked = False
#     if not st.session_state.df_original.empty:
#         col1, col2, col3 = st.columns([1, 2, 1]) 
#         with col2:
#             run_evaluation_button_clicked = st.button("🚀 Run Evaluation", help="Click to start the evaluation process.", use_container_width=True)
#         st.markdown("---")

#     if run_evaluation_button_clicked and not st.session_state.df_original.empty:
#         if 'llm_output' not in st.session_state.df_original.columns or st.session_state.df_original['llm_output'].isnull().all():
#             st.error("The 'llm_output' column is missing or empty in the data. Please fetch bot responses or ensure your uploaded data includes it before running evaluation.")
#         elif not st.session_state.sidebar_inputs['selected_metrics']:
#             st.warning("Please select at least one metric to run the evaluation.")
#         else:
#             with st.spinner("Running evaluation... This may take a while for large datasets."):
#                 try:
#                     st.session_state.df_evaluated = evaluator.evaluate_dataframe(
#                         st.session_state.df_original.copy(),
#                         st.session_state.sidebar_inputs['selected_metrics'],
#                         custom_thresholds=st.session_state.sidebar_inputs['custom_thresholds'],
#                         sensitive_keywords=st.session_state.sidebar_inputs['sensitive_keywords']
#                     )
#                     st.session_state.show_results = True
#                     st.session_state.selected_metrics_for_results = st.session_state.sidebar_inputs['selected_metrics']
#                     st.session_state.custom_thresholds_for_results = st.session_state.sidebar_inputs['custom_thresholds']
#                     st.session_state.show_tutorial = False
#                 except Exception as e:
#                     st.error(f"An error occurred during evaluation: {e}")
#                     # st.session_state.show_results = False
#                     # st.session_state.show_tutorial = True 
#                     # st.session_state.file_uploader_key += 1 
#                     # st.rerun() 
#     elif run_evaluation_button_clicked and st.session_state.df_original.empty:
#         st.warning("Please upload a dataset before running the evaluation.")
#         # st.session_state.show_tutorial = True
#         # st.session_state.file_uploader_key += 1
#         # st.rerun()

#     # Display results
#     if st.session_state.show_results and not st.session_state.df_evaluated.empty:
#         results_view.render_results(
#             st.session_state.df_evaluated,
#             st.session_state.selected_metrics_for_results,
#             st.session_state.custom_thresholds_for_results
#         )
#         csv_output = st.session_state.df_evaluated.to_csv(index=False).encode('utf-8')
#         st.download_button(
#             label="Download Results as CSV",
#             data=csv_output,
#             file_name="llm_evaluation_results.csv",
#             mime="text/csv",
#         )

# if __name__ == "__main__":
#     main()





# # import streamlit as st
# # import pandas as pd
# # import sys
# # import os

# # # Add the project root to sys.path so Python can find 'llm_eval_package'
# # # This assumes streamlit_app.py is in the project root directory.
# # project_root = os.path.abspath(os.path.dirname(__file__))
# # if project_root not in sys.path:
# #     sys.path.insert(0, project_root)

# # # Import components from the new llm_eval_package
# # from llm_eval_package.data.loader import DataLoader
# # from llm_eval_package.core.engine import Evaluator
# # from llm_eval_package.core.reporting import Reporter
# # from llm_eval_package.ui.sidebar_view import SidebarView
# # from llm_eval_package.ui.data_view import DataManagementView
# # from llm_eval_package.ui.results_view import ResultsView
# # from llm_eval_package.ui.tutorial_view import TutorialView
# # from llm_eval_package.config import METRIC_THRESHOLDS # Renamed from app_config

# # def main():
# #     """
# #     Main function to run the Streamlit LLM Evaluation App.
# #     """
# #     # Set Streamlit page configuration
# #     st.set_page_config(
# #         page_title="Genius AI LLM Evaluator",
# #         page_icon="✨",
# #         layout="wide", # Use wide layout by default
# #         initial_sidebar_state="expanded"
# #     )

# #     # Initialize components
# #     data_loader = DataLoader()
# #     evaluator = Evaluator()
# #     reporter = Reporter()
# #     sidebar_view = SidebarView()
# #     data_management_view = DataManagementView()
# #     results_view = ResultsView()
# #     tutorial_view = TutorialView()

# #     # Session state initialization
# #     if 'df_original' not in st.session_state:
# #         st.session_state.df_original = pd.DataFrame()
# #     if 'df_evaluated' not in st.session_state:
# #         st.session_state.df_evaluated = pd.DataFrame()
# #     if 'show_results' not in st.session_state:
# #         st.session_state.show_results = False
# #     if 'selected_metrics_for_results' not in st.session_state:
# #         st.session_state.selected_metrics_for_results = []
# #     if 'custom_thresholds_for_results' not in st.session_state:
# #         st.session_state.custom_thresholds_for_results = None
# #     if 'show_tutorial' not in st.session_state:
# #         st.session_state.show_tutorial = True # Start with tutorial visible
# #     # New: Key to reset file uploader widget
# #     if 'file_uploader_key' not in st.session_state:
# #         st.session_state.file_uploader_key = 0
# #     # New: Store inputs from sidebar to be used by the main Run Evaluation button
# #     if 'sidebar_inputs' not in st.session_state:
# #         st.session_state.sidebar_inputs = {}

# #     print(f"DEBUG: --- RERUN START ---")
# #     print(f"DEBUG: show_tutorial: {st.session_state.show_tutorial}")
# #     print(f"DEBUG: show_results: {st.session_state.show_results}")
# #     print(f"DEBUG: df_original.empty: {st.session_state.df_original.empty}")
# #     print(f"DEBUG: df_evaluated.empty: {st.session_state.df_evaluated.empty}")


# #     # Render sidebar and get user inputs
# #     # The sidebar now returns a dictionary of its inputs
# #     sidebar_outputs = sidebar_view.render_sidebar(st.session_state.file_uploader_key)
# #     # Store these outputs in session state for the main evaluation logic to access
# #     st.session_state.sidebar_inputs = {
# #         'uploaded_file': sidebar_outputs[0],
# #         'selected_metrics': sidebar_outputs[1],
# #         'custom_thresholds': sidebar_outputs[3],
# #         'sensitive_keywords': sidebar_outputs[4],
# #         'selected_task_type': sidebar_outputs[5],
# #         'go_to_instructions': sidebar_outputs[6]
# #     }
# #     # run_evaluation is now handled by a button in the main area, not the sidebar
# #     run_evaluation_from_sidebar = sidebar_outputs[2] # This will always be False now


# #     print(f"DEBUG: uploaded_file (from sidebar): {st.session_state.sidebar_inputs['uploaded_file'] is not None}")
# #     print(f"DEBUG: selected_metrics (from sidebar): {st.session_state.sidebar_inputs['selected_metrics']}")
# #     print(f"DEBUG: go_to_instructions (from sidebar): {st.session_state.sidebar_inputs['go_to_instructions']}")


# #     # Handle "Go to Instructions" button click (triggered from sidebar_outputs)
# #     if st.session_state.sidebar_inputs['go_to_instructions']:
# #         st.session_state.show_tutorial = True
# #         st.session_state.show_results = False # Hide results if going to tutorial
# #         st.session_state.df_original = pd.DataFrame() # Clear data to show fresh tutorial
# #         st.session_state.df_evaluated = pd.DataFrame() # Clear evaluated data
# #         st.session_state.file_uploader_key += 1 # Increment key to reset file uploader
# #         print(f"DEBUG: 'Go to Instructions' clicked. Resetting state and rerunning.")
# #         st.rerun() # Rerun to update the display

# #     # Main Title and Header
# #     st.markdown(
# #         """
# #         <style>
# #         .main-header {
# #             font-size: 3em;
# #             font-weight: bold;
# #             color: #4CAF50; /* A nice green */
# #             text-align: center;
# #             margin-bottom: 0.5em;
# #             text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
# #         }
# #         .subheader {
# #             font-size: 1.5em;
# #             color: #555;
# #             text-align: center;
# #             margin-bottom: 1em;
# #         }
# #         .stButton>button {
# #             background-color: #4CAF50;
# #             color: white;
# #             border-radius: 12px;
# #             padding: 10px 24px;
# #             font-size: 1.2em;
# #             border: none;
# #             box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
# #             transition: 0.3s;
# #         }
# #         .stButton>button:hover {
# #             background-color: #45a049;
# #             box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
# #         }
# #         .stAlert {
# #             border-radius: 10px;
# #         }
# #         </style>
# #         <h1 class="main-header">✨ LLM Evaluation Dashboard ✨</h1>
# #         <p class="subheader">Evaluate your Large Language Models with confidence.</p>
# #         """,
# #         unsafe_allow_html=True
# #     )

# #     # Determine if we should show the tutorial based on current state and actions
# #     should_show_tutorial_now = st.session_state.show_tutorial and \
# #                                st.session_state.sidebar_inputs['uploaded_file'] is None and \
# #                                st.session_state.df_original.empty and \
# #                                st.session_state.df_evaluated.empty

# #     if should_show_tutorial_now:
# #         print(f"DEBUG: Rendering tutorial based on conditions.")
# #         tutorial_view.render_tutorial()
# #         print(f"DEBUG: Tutorial rendered. Exiting main function.")
# #         return # Exit main to avoid further processing if tutorial is active
# #     else:
# #         # If we are not showing tutorial, ensure the flag is False
# #         if st.session_state.show_tutorial: # Only set to False if it was True and conditions changed
# #             st.session_state.show_tutorial = False
# #         print(f"DEBUG: NOT rendering tutorial. Proceeding to data/evaluation logic.")

# #     # If not showing tutorial, proceed with main app logic
# #     # Load data if file is uploaded or if a file was previously uploaded and is in session state
# #     if st.session_state.sidebar_inputs['uploaded_file'] is not None:
# #         print(f"DEBUG: New file uploaded. Attempting to load data.")
# #         try:
# #             df_original = data_loader.load_data(st.session_state.sidebar_inputs['uploaded_file'])
# #             st.session_state.df_original = df_original # Store original for display
# #             data_management_view.render_data_preview(df_original)
# #             st.session_state.show_tutorial = False # Successfully loaded data, so hide tutorial
# #             print(f"DEBUG: Data loaded successfully. show_tutorial set to False. df_original.empty: {st.session_state.df_original.empty}")
# #         except Exception as e:
# #             st.error(f"Error loading or validating data: {e}")
# #             print(f"DEBUG: Data loading error: {e}. Resetting state and rerunning to tutorial.")
# #             st.session_state.df_original = pd.DataFrame() # Clear data on error
# #             st.session_state.df_evaluated = pd.DataFrame()
# #             st.session_state.show_results = False
# #             st.session_state.show_tutorial = True # Go back to tutorial on data error
# #             st.session_state.file_uploader_key += 1 # Reset uploader on error
# #             st.rerun() # Rerun to clear previous data display and show tutorial
# #             return # Stop execution if data loading fails
# #     elif not st.session_state.df_original.empty:
# #         print(f"DEBUG: No new file, but df_original exists in session state. Displaying preview.")
# #         data_management_view.render_data_preview(st.session_state.df_original)
# #         st.session_state.show_tutorial = False # If showing data preview, tutorial should be off
# #         print(f"DEBUG: Data preview rendered. show_tutorial set to False. df_original.empty: {st.session_state.df_original.empty}")
# #     else:
# #         print(f"DEBUG: No file uploaded and df_original is empty. No data preview. This state should ideally not be reached if not in tutorial.")

# #     # --- Run Evaluation Button (Moved to main area) ---
# #     # Only show the button if data is loaded
# #     run_evaluation_button_clicked = False
# #     if not st.session_state.df_original.empty:
# #         # Use a container for the button to control its placement/width
# #         # Center the button using columns
# #         col1, col2, col3 = st.columns([1, 2, 1]) 
# #         with col2:
# #             run_evaluation_button_clicked = st.button("🚀 Run Evaluation", help="Click to start the evaluation process.", use_container_width=True)
# #         st.markdown("---") # Add a separator after the button
# #         print(f"DEBUG: Run Evaluation button displayed. Clicked: {run_evaluation_button_clicked}")

# #     # Run evaluation if button is clicked and data is available
# #     if run_evaluation_button_clicked and not st.session_state.df_original.empty:
# #         print(f"DEBUG: Run Evaluation button clicked and data is available. Starting evaluation.")
# #         if not st.session_state.sidebar_inputs['selected_metrics']:
# #             print(f"DEBUG: No metrics selected.")
# #             st.warning("Please select at least one metric to run the evaluation.")
# #         else:
# #             with st.spinner("Running evaluation... This may take a while for large datasets."):
# #                 try:
# #                     # Pass custom_thresholds and sensitive_keywords to the evaluator
# #                     st.session_state.df_evaluated = evaluator.evaluate_dataframe(
# #                         st.session_state.df_original.copy(), # Use a copy to avoid modifying original
# #                         st.session_state.sidebar_inputs['selected_metrics'],
# #                         custom_thresholds=st.session_state.sidebar_inputs['custom_thresholds'],
# #                         sensitive_keywords=st.session_state.sidebar_inputs['sensitive_keywords']
# #                     )
# #                     st.session_state.show_results = True
# #                     st.session_state.selected_metrics_for_results = st.session_state.sidebar_inputs['selected_metrics'] # Store for results view
# #                     st.session_state.custom_thresholds_for_results = st.session_state.sidebar_inputs['custom_thresholds'] # Store for results view
# #                     st.session_state.show_tutorial = False # Hide tutorial if evaluation runs
# #                     print(f"DEBUG: Evaluation completed. show_results: {st.session_state.show_results}, df_evaluated.empty: {st.session_state.df_evaluated.empty}")
# #                 except Exception as e:
# #                     st.error(f"An error occurred during evaluation: {e}")
# #                     print(f"DEBUG: Evaluation error: {e}. Resetting state and rerunning to tutorial.")
# #                     st.session_state.show_results = False
# #                     st.session_state.show_tutorial = True # Go back to tutorial on evaluation error
# #                     st.session_state.file_uploader_key += 1 # Reset uploader on error
# #                     st.rerun() # Rerun to show tutorial
# #     elif run_evaluation_button_clicked and st.session_state.df_original.empty:
# #         print(f"DEBUG: Run Evaluation clicked but no data. Showing warning and rerunning to tutorial.")
# #         st.warning("Please upload a dataset before running the evaluation.")
# #         st.session_state.show_tutorial = True # Show tutorial if run without data
# #         st.session_state.file_uploader_key += 1 # Reset uploader on error
# #         st.rerun() # Rerun to show tutorial
# #     else:
# #         print(f"DEBUG: Not running evaluation. run_evaluation_button_clicked: {run_evaluation_button_clicked}, df_original.empty: {st.session_state.df_original.empty}")


# #     # Display results if evaluation has been run
# #     if st.session_state.show_results and not st.session_state.df_evaluated.empty:
# #         print(f"DEBUG: show_results is True and df_evaluated is not empty. Rendering results.")
# #         results_view.render_results(
# #             st.session_state.df_evaluated,
# #             st.session_state.selected_metrics_for_results,
# #             st.session_state.custom_thresholds_for_results
# #         )
        
# #         # Option to download results
# #         csv_output = st.session_state.df_evaluated.to_csv(index=False).encode('utf-8')
# #         st.download_button(
# #             label="Download Results as CSV",
# #             data=csv_output,
# #             file_name="llm_evaluation_results.csv",
# #             mime="text/csv",
# #         )
# #     else:
# #         print(f"DEBUG: Not rendering results. show_results: {st.session_state.show_results}, df_evaluated.empty: {st.session_state.df_evaluated.empty}")

# #     print(f"DEBUG: --- RERUN END ---")

# # if __name__ == "__main__":
# #     main()

# # # import streamlit as st
# # # import pandas as pd
# # # import sys
# # # import os

# # # # --- CRITICAL: Import Streamlit's internal CLI module for programmatic launch ---
# # # import streamlit.web.cli as st_cli

# # # # Add the project root to sys.path so Python can find 'llm_eval_package'
# # # # This assumes streamlit_app.py is in the project root directory.
# # # project_root = os.path.abspath(os.path.dirname(__file__))
# # # if project_root not in sys.path:
# # #     sys.path.insert(0, project_root)

# # # # Import components from the new llm_eval_package
# # # from llm_eval_package.data.loader import DataLoader
# # # from llm_eval_package.core.engine import Evaluator
# # # from llm_eval_package.core.reporting import Reporter
# # # from llm_eval_package.ui.sidebar_view import SidebarView
# # # from llm_eval_package.ui.data_view import DataManagementView
# # # from llm_eval_package.ui.results_view import ResultsView
# # # from llm_eval_package.ui.tutorial_view import TutorialView
# # # from llm_eval_package.config import METRIC_THRESHOLDS # Renamed from app_config

# # # def run_streamlit_app_logic():
# # #     """
# # #     Contains the core Streamlit application logic.
# # #     This function will be called by the Streamlit server.
# # #     """
# # #     # Initialize components
# # #     data_loader = DataLoader()
# # #     evaluator = Evaluator()
# # #     reporter = Reporter()
# # #     sidebar_view = SidebarView()
# # #     data_management_view = DataManagementView()
# # #     results_view = ResultsView()
# # #     tutorial_view = TutorialView()

# # #     # Session state initialization
# # #     if 'df_original' not in st.session_state:
# # #         st.session_state.df_original = pd.DataFrame()
# # #     if 'df_evaluated' not in st.session_state:
# # #         st.session_state.df_evaluated = pd.DataFrame()
# # #     if 'show_results' not in st.session_state:
# # #         st.session_state.show_results = False
# # #     if 'selected_metrics_for_results' not in st.session_state:
# # #         st.session_state.selected_metrics_for_results = []
# # #     if 'custom_thresholds_for_results' not in st.session_state:
# # #         st.session_state.custom_thresholds_for_results = None
# # #     if 'show_tutorial' not in st.session_state:
# # #         st.session_state.show_tutorial = True # Start with tutorial visible
# # #     # New: Key to reset file uploader widget
# # #     if 'file_uploader_key' not in st.session_state:
# # #         st.session_state.file_uploader_key = 0
# # #     # New: Store inputs from sidebar to be used by the main Run Evaluation button
# # #     if 'sidebar_inputs' not in st.session_state:
# # #         st.session_state.sidebar_inputs = {}

# # #     print(f"DEBUG: --- RERUN START ---")
# # #     print(f"DEBUG: show_tutorial: {st.session_state.show_tutorial}")
# # #     print(f"DEBUG: show_results: {st.session_state.show_results}")
# # #     print(f"DEBUG: df_original.empty: {st.session_state.df_original.empty}")
# # #     print(f"DEBUG: df_evaluated.empty: {st.session_state.df_evaluated.empty}")


# # #     # Render sidebar and get user inputs
# # #     # The sidebar now returns a dictionary of its inputs
# # #     sidebar_outputs = sidebar_view.render_sidebar(st.session_state.file_uploader_key)
# # #     # Store these outputs in session state for the main evaluation logic to access
# # #     st.session_state.sidebar_inputs = {
# # #         'uploaded_file': sidebar_outputs[0],
# # #         'selected_metrics': sidebar_outputs[1],
# # #         'custom_thresholds': sidebar_outputs[3],
# # #         'sensitive_keywords': sidebar_outputs[4],
# # #         'selected_task_type': sidebar_outputs[5],
# # #         'go_to_instructions': sidebar_outputs[6]
# # #     }
# # #     # run_evaluation is now handled by a button in the main area, not the sidebar
# # #     run_evaluation_from_sidebar = sidebar_outputs[2] # This will always be False now


# # #     print(f"DEBUG: uploaded_file (from sidebar): {st.session_state.sidebar_inputs['uploaded_file'] is not None}")
# # #     print(f"DEBUG: selected_metrics (from sidebar): {st.session_state.sidebar_inputs['selected_metrics']}")
# # #     print(f"DEBUG: go_to_instructions (from sidebar): {st.session_state.sidebar_inputs['go_to_instructions']}")


# # #     # Handle "Go to Instructions" button click (triggered from sidebar_outputs)
# # #     if st.session_state.sidebar_inputs['go_to_instructions']:
# # #         st.session_state.show_tutorial = True
# # #         st.session_state.show_results = False # Hide results if going to tutorial
# # #         st.session_state.df_original = pd.DataFrame() # Clear data to show fresh tutorial
# # #         st.session_state.df_evaluated = pd.DataFrame() # Clear evaluated data
# # #         st.session_state.file_uploader_key += 1 # Increment key to reset file uploader
# # #         print(f"DEBUG: 'Go to Instructions' clicked. Resetting state and rerunning.")
# # #         st.rerun() # Rerun to update the display

# # #     # Main Title and Header
# # #     st.markdown(
# # #         """
# # #         <style>
# # #         .main-header {
# # #             font-size: 3em;
# # #             font-weight: bold;
# # #             color: #4CAF50; /* A nice green */
# # #             text-align: center;
# # #             margin-bottom: 0.5em;
# # #             text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
# # #         }
# # #         .subheader {
# # #             font-size: 1.5em;
# # #             color: #555;
# # #             text-align: center;
# # #             margin-bottom: 1em;
# # #         }
# # #         .stButton>button {
# # #             background-color: #4CAF50;
# # #             color: white;
# # #             border-radius: 12px;
# # #             padding: 10px 24px;
# # #             font-size: 1.2em;
# # #             border: none;
# # #             box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
# # #             transition: 0.3s;
# # #         }
# # #         .stButton>button:hover {
# # #             background-color: #45a049;
# # #             box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
# # #         }
# # #         .stAlert {
# # #             border-radius: 10px;
# # #         }
# # #         </style>
# # #         <h1 class="main-header">✨ LLM Evaluation Dashboard ✨</h1>
# # #         <p class="subheader">Evaluate your Large Language Models with confidence.</p>
# # #         """,
# # #         unsafe_allow_html=True
# # #     )

# # #     # Determine if we should show the tutorial based on current state and actions
# # #     should_show_tutorial_now = st.session_state.show_tutorial and \
# # #                                st.session_state.sidebar_inputs['uploaded_file'] is None and \
# # #                                st.session_state.df_original.empty and \
# # #                                st.session_state.df_evaluated.empty

# # #     if should_show_tutorial_now:
# # #         print(f"DEBUG: Rendering tutorial based on conditions.")
# # #         tutorial_view.render_tutorial()
# # #         print(f"DEBUG: Tutorial rendered. Exiting main function.")
# # #         return # Exit main to avoid further processing if tutorial is active
# # #     else:
# # #         # If we are not showing tutorial, ensure the flag is False
# # #         if st.session_state.show_tutorial: # Only set to False if it was True and conditions changed
# # #             st.session_state.show_tutorial = False
# # #         print(f"DEBUG: NOT rendering tutorial. Proceeding to data/evaluation logic.")

# # #     # If not showing tutorial, proceed with main app logic
# # #     # Load data if file is uploaded or if a file was previously uploaded and is in session state
# # #     if st.session_state.sidebar_inputs['uploaded_file'] is not None:
# # #         print(f"DEBUG: New file uploaded. Attempting to load data.")
# # #         try:
# # #             df_original = data_loader.load_data(st.session_state.sidebar_inputs['uploaded_file'])
# # #             st.session_state.df_original = df_original # Store original for display
# # #             data_management_view.render_data_preview(df_original)
# # #             st.session_state.show_tutorial = False # Successfully loaded data, so hide tutorial
# # #             print(f"DEBUG: Data loaded successfully. show_tutorial set to False. df_original.empty: {st.session_state.df_original.empty}")
# # #         except Exception as e:
# # #             st.error(f"Error loading or validating data: {e}")
# # #             print(f"DEBUG: Data loading error: {e}. Resetting state and rerunning to tutorial.")
# # #             st.session_state.df_original = pd.DataFrame() # Clear data on error
# # #             st.session_state.df_evaluated = pd.DataFrame()
# # #             st.session_state.show_results = False
# # #             st.session_state.show_tutorial = True # Go back to tutorial on data error
# # #             st.session_state.file_uploader_key += 1 # Reset uploader on error
# # #             st.rerun() # Rerun to clear previous data display and show tutorial
# # #             return # Stop execution if data loading fails
# # #     elif not st.session_state.df_original.empty:
# # #         print(f"DEBUG: No new file, but df_original exists in session state. Displaying preview.")
# # #         data_management_view.render_data_preview(st.session_state.df_original)
# # #         st.session_state.show_tutorial = False # If showing data preview, tutorial should be off
# # #         print(f"DEBUG: Data preview rendered. show_tutorial set to False. df_original.empty: {st.session_state.df_original.empty}")
# # #     else:
# # #         print(f"DEBUG: No file uploaded and df_original is empty. No data preview. This state should ideally not be reached if not in tutorial.")

# # #     # --- Run Evaluation Button (Moved to main area) ---
# # #     # Only show the button if data is loaded
# # #     run_evaluation_button_clicked = False
# # #     if not st.session_state.df_original.empty:
# # #         # Use a container for the button to control its placement/width
# # #         # Center the button using columns
# # #         col1, col2, col3 = st.columns([1, 2, 1]) 
# # #         with col2:
# # #             run_evaluation_button_clicked = st.button("🚀 Run Evaluation", help="Click to start the evaluation process.", use_container_width=True)
# # #         st.markdown("---") # Add a separator after the button
# # #         print(f"DEBUG: Run Evaluation button displayed. Clicked: {run_evaluation_button_clicked}")

# # #     # Run evaluation if button is clicked and data is available
# # #     if run_evaluation_button_clicked and not st.session_state.df_original.empty:
# # #         print(f"DEBUG: Run Evaluation button clicked and data is available. Starting evaluation.")
# # #         if not st.session_state.sidebar_inputs['selected_metrics']:
# # #             print(f"DEBUG: No metrics selected.")
# # #             st.warning("Please select at least one metric to run the evaluation.")
# # #         else:
# # #             with st.spinner("Running evaluation... This may take a while for large datasets."):
# # #                 try:
# # #                     # Pass custom_thresholds and sensitive_keywords to the evaluator
# # #                     st.session_state.df_evaluated = evaluator.evaluate_dataframe(
# # #                         st.session_state.df_original.copy(), # Use a copy to avoid modifying original
# # #                         st.session_state.sidebar_inputs['selected_metrics'],
# # #                         custom_thresholds=st.session_state.sidebar_inputs['custom_thresholds'],
# # #                         sensitive_keywords=st.session_state.sidebar_inputs['sensitive_keywords']
# # #                     )
# # #                     st.session_state.show_results = True
# # #                     st.session_state.selected_metrics_for_results = st.session_state.sidebar_inputs['selected_metrics'] # Store for results view
# # #                     st.session_state.custom_thresholds_for_results = st.session_state.sidebar_inputs['custom_thresholds'] # Store for results view
# # #                     st.session_state.show_tutorial = False # Hide tutorial if evaluation runs
# # #                     print(f"DEBUG: Evaluation completed. show_results: {st.session_state.show_results}, df_evaluated.empty: {st.session_state.df_evaluated.empty}")
# # #                 except Exception as e:
# # #                     st.error(f"An error occurred during evaluation: {e}")
# # #                     print(f"DEBUG: Evaluation error: {e}. Resetting state and rerunning to tutorial.")
# # #                     st.session_state.show_results = False
# # #                     st.session_state.show_tutorial = True # Go back to tutorial on evaluation error
# # #                     st.session_state.file_uploader_key += 1 # Reset uploader on error
# # #                     st.rerun() # Rerun to show tutorial
# # #     elif run_evaluation_button_clicked and st.session_state.df_original.empty:
# # #         print(f"DEBUG: Run Evaluation clicked but no data. Showing warning and rerunning to tutorial.")
# # #         st.warning("Please upload a dataset before running the evaluation.")
# # #         st.session_state.show_tutorial = True # Show tutorial if run without data
# # #         st.session_state.file_uploader_key += 1 # Reset uploader on error
# # #         st.rerun() # Rerun to show tutorial
# # #     else:
# # #         print(f"DEBUG: Not running evaluation. run_evaluation_button_clicked: {run_evaluation_button_clicked}, df_original.empty: {st.session_state.df_original.empty}")


# # #     # Display results if evaluation has been run
# # #     if st.session_state.show_results and not st.session_state.df_evaluated.empty:
# # #         print(f"DEBUG: show_results is True and df_evaluated is not empty. Rendering results.")
# # #         results_view.render_results(
# # #             st.session_state.df_evaluated,
# # #             st.session_state.selected_metrics_for_results,
# # #             st.session_state.custom_thresholds_for_results
# # #         )
        
# # #         # Option to download results
# # #         csv_output = st.session_state.df_evaluated.to_csv(index=False).encode('utf-8')
# # #         st.download_button(
# # #             label="Download Results as CSV",
# # #             data=csv_output,
# # #             file_name="llm_evaluation_results.csv",
# # #             mime="text/csv",
# # #         )
# # #     else:
# # #         print(f"DEBUG: Not rendering results. show_results: {st.session_state.show_results}, df_evaluated.empty: {st.session_state.df_evaluated.empty}")

# # #     print(f"DEBUG: --- RERUN END ---")

# # # # --- CRITICAL: Programmatic launch of Streamlit server when bundled ---
# # # # This block ensures that when the .exe is run, it starts the Streamlit server.
# # # # It uses a more robust check for whether Streamlit is already running.
# # # if __name__ == "__main__":
# # #     # Check if the script is being run via 'streamlit run' command
# # #     # This is a more reliable check than internal Streamlit attributes.
# # #     is_running_via_streamlit_cli = ("streamlit" in sys.argv[0] and "run" in sys.argv) or \
# # #                                    (len(sys.argv) > 1 and sys.argv[1] == "streamlit" and sys.argv[2] == "run")

# # #     if not is_running_via_streamlit_cli:
# # #         # If not running via 'streamlit run', then we are likely in a PyInstaller bundle.
# # #         # Programmatically set up sys.argv for Streamlit's internal runner.
        
# # #         # Get the path to the current script (streamlit_app.py)
# # #         # This is needed by Streamlit's internal runner
# # #         this_script_path = os.path.abspath(__file__)
        
# # #         # Set command-line arguments for Streamlit server
# # #         # These are the arguments that 'streamlit run' would normally take.
# # #         sys.argv = [
# # #             "streamlit", "run", this_script_path,
# # #             "--server.port", "8501",
# # #             "--server.enableCORS", "false",
# # #             "--server.enableXsrfProtection", "false",
# # #             "--browser.gatherUsageStats", "false", # Optional: Disable usage stats
# # #             "--global.developmentMode", "false" # Optional: Set to false for production
# # #         ]
        
# # #         # Call Streamlit's internal main function to start the server.
# # #         # This will block until the server is shut down.
# # #         # It's crucial to call this from the __main__ block.
# # #         sys.exit(st_cli.main_run())
# # #     else:
# # #         # If already running via 'streamlit run' (e.g., during development),
# # #         # just call the main app logic directly.
# # #         run_streamlit_app_logic()
