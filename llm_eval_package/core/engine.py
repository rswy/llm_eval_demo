import pandas as pd
import numpy as np
import streamlit as st # Used for @st.cache_resource and conditional UI feedback
import os
from tqdm import tqdm # For CLI progress bar

# Import metric classes
from llm_eval_package.metrics.fluency_similarity import SemanticSimilarityMetric
from llm_eval_package.metrics.completeness import CompletenessMetric
from llm_eval_package.metrics.conciseness import ConcisenessMetric
from llm_eval_package.metrics.trust_factuality import TrustFactualityMetric
from llm_eval_package.metrics.safety import SafetyMetric
from llm_eval_package.metrics.fact_adherence import FactAdherenceMetric

from llm_eval_package.config import (
    METRIC_THRESHOLDS, AVAILABLE_METRICS,
    SENTENCE_BERT_MODEL_PATH, MODEL_DIR, SENTENCE_BERT_MODEL,
    PASS_CRITERION_ALL_PASS, PASS_CRITERION_ANY_PASS, DEFAULT_PASS_CRITERION # Import pass criteria constants
)
from llm_eval_package.utils import ModelDownloader


@st.cache_resource # This decorator caches the function's return value across Streamlit reruns
def _get_cached_metric_instances_internal():
    """
    Loads and caches all metric models/instances required.
    Handles model download for Semantic Similarity if not found locally.
    """
    metrics_instances = {}
    model_downloader = ModelDownloader()
    
    # Check and potentially download Sentence-BERT model for Semantic Similarity
    if "Semantic Similarity" in AVAILABLE_METRICS: # Only download if metric is available
        # Ensure the model path exists and contains model files
        if not os.path.exists(SENTENCE_BERT_MODEL_PATH) or not os.listdir(SENTENCE_BERT_MODEL_PATH):
            download_message = f"Semantic Similarity model ('{SENTENCE_BERT_MODEL}') not found locally. Attempting download to '{MODEL_DIR}'..."
            try: # Try to use Streamlit elements if in Streamlit context
                st.info(download_message)
                # with st.spinner(f"Downloading '{SENTENCE_BERT_MODEL}'... This may take a moment."): # Spinner can be too intrusive on load
                downloaded_path = model_downloader.download_and_save_model(SENTENCE_BERT_MODEL, MODEL_DIR)
                if not downloaded_path:
                    raise Exception(f"Failed to download model '{SENTENCE_BERT_MODEL}'. Please check internet connection or model name.")
                st.success(f"Model '{SENTENCE_BERT_MODEL}' downloaded successfully to '{downloaded_path}'!")
            except RuntimeError: # Not in Streamlit context (e.g., CLI)
                print(f"INFO: {download_message}")
                downloaded_path = model_downloader.download_and_save_model(SENTENCE_BERT_MODEL, MODEL_DIR)
                if not downloaded_path:
                    raise Exception(f"Failed to download model '{SENTENCE_BERT_MODEL}'.")
                print(f"INFO: Model '{SENTENCE_BERT_MODEL}' downloaded successfully to '{downloaded_path}'!")
        else:
            print(f"DEBUG: Semantic Similarity model found at {SENTENCE_BERT_MODEL_PATH}.")

    # Initialize metric instances based on AVAILABLE_METRICS in config
    try:
        if "Semantic Similarity" in AVAILABLE_METRICS:
            metrics_instances["Semantic Similarity"] = SemanticSimilarityMetric(SENTENCE_BERT_MODEL_PATH)
        if "Completeness" in AVAILABLE_METRICS:
            metrics_instances["Completeness"] = CompletenessMetric()
        if "Conciseness" in AVAILABLE_METRICS:
            metrics_instances["Conciseness"] = ConcisenessMetric()
        if "Trust & Factuality" in AVAILABLE_METRICS:
            metrics_instances["Trust & Factuality"] = TrustFactualityMetric()
        if "Fact Adherence" in AVAILABLE_METRICS:
            metrics_instances["Fact Adherence"] = FactAdherenceMetric()
        if "Safety" in AVAILABLE_METRICS:
            metrics_instances["Safety"] = SafetyMetric()
        
        # Dynamically add any other metrics defined in AVAILABLE_METRICS if not listed above
        # This would require a mapping from string name to class type, which AVAILABLE_METRICS provides.
        # Example of more dynamic instantiation (if metric classes are in a known module):
        # import llm_eval_package.metrics as metrics_module
        # for name, class_name_str in AVAILABLE_METRICS.items():
        #     if name not in metrics_instances: # If not already hardcoded above
        #         try:
        #             MetricClass = getattr(metrics_module, class_name_str)
        #             metrics_instances[name] = MetricClass() # Assumes no args or handles args
        #         except AttributeError:
        #             print(f"Warning: Metric class {class_name_str} for '{name}' not found in metrics module.")


        print("DEBUG: All configured metric instances loaded successfully!")
        return metrics_instances
    except Exception as e:
        print(f"CRITICAL DEBUG: EXCEPTION during metric model/instance loading: {e}")
        import traceback
        print(traceback.format_exc())
        raise e # Re-raise to be caught by Evaluator.__init__

class Evaluator:
    def __init__(self):
        try:
            self.metrics_instances = _get_cached_metric_instances_internal()
            try: st.toast("Metric evaluation engine initialized successfully!", icon="👍") # Feedback in UI
            except RuntimeError: print("INFO: Metric evaluation engine initialized.") # CLI feedback
        except Exception as e:
            error_message = f"Critical Error: Failed to initialize metric evaluation engine: {e}. Some evaluations may not work."
            try: st.error(error_message); st.stop()
            except RuntimeError: print(error_message); raise # CLI should halt

    def evaluate_dataframe(self, df: pd.DataFrame, selected_metrics: list,
                           custom_thresholds: dict = None,
                           sensitive_keywords: list = None,
                           overall_pass_criterion: str = DEFAULT_PASS_CRITERION
                           ) -> pd.DataFrame:
        if df.empty:
            try: st.warning("Input data is empty. Nothing to evaluate.")
            except RuntimeError: print("Warning: Input data is empty.")
            return df.copy()

        if not self.metrics_instances:
             try: st.error("Evaluation cannot proceed: Metric instances are not initialized.")
             except RuntimeError: print("Error: Metric instances are not initialized.")
             return df.copy()
        
        if not selected_metrics:
            try: st.warning("No metrics selected for evaluation. Returning original data.")
            except RuntimeError: print("Warning: No metrics selected for evaluation.")
            return df.copy()


        current_thresholds = custom_thresholds if custom_thresholds is not None else METRIC_THRESHOLDS.copy()
        df_copy = df.copy() # Work on a copy to avoid modifying the original DataFrame passed in

        # Initialize score and individual pass/fail columns for selected metrics
        for metric_name in selected_metrics:
            if metric_name not in self.metrics_instances:
                msg = f"Configuration Warning: Metric '{metric_name}' is selected but no corresponding instance is available. It will be skipped."
                try: st.warning(msg)
                except RuntimeError: print(msg)
                continue # Skip this metric if its instance isn't available
            df_copy[f'{metric_name} Score'] = np.nan # Use np.nan for numeric missing, will be converted to 'N/A' string if not float
            df_copy[f'{metric_name} Pass/Fail'] = 'N/A' # Default for string column
        
        overall_pass_fail_col_name = "Overall Pass/Fail"
        df_copy[overall_pass_fail_col_name] = 'N/A' # Initialize

        # Determine if running in Streamlit context for progress bar
        try:
            progress_bar = st.progress(0, text="Initializing evaluation...")
            iterable = df_copy.iterrows()
        except RuntimeError: # Not in Streamlit context, use tqdm for CLI
            progress_bar = None
            iterable = tqdm(df_copy.iterrows(), total=df_copy.shape[0], desc="Evaluating test cases")


        for i, row in iterable:
            # Ensure essential columns are strings, handle potential missing data gracefully
            query = str(row.get('query', ''))
            llm_output = str(row.get('llm_output', ''))
            reference_answer = str(row.get('reference_answer', ''))
            required_facts_str = str(row.get('required_facts', ''))

            if progress_bar: # Streamlit update
                progress_bar.progress((i + 1) / df_copy.shape[0], text=f"Evaluating test case {i+1}/{df_copy.shape[0]}...")

            row_metric_statuses = {} # To store 'Pass'/'Fail'/'Error' for each metric for this row

            for metric_name in selected_metrics:
                if metric_name not in self.metrics_instances:
                    row_metric_statuses[metric_name] = 'Error (Not Available)'
                    continue

                metric_instance = self.metrics_instances[metric_name]
                score = np.nan # Default to NaN for score
                individual_pass_fail_status = 'Error (Calculation)' # Default status

                try:
                    kwargs_for_compute = {} # Prepare kwargs for metric's compute method
                    if metric_name == "Safety":
                        kwargs_for_compute['sensitive_keywords'] = sensitive_keywords
                    elif metric_name == "Fact Adherence":
                        kwargs_for_compute['required_facts'] = required_facts_str
                    # Other metrics can have specific kwargs added here if needed

                    current_score = metric_instance.compute(
                        llm_output=llm_output,
                        reference_answer=reference_answer,
                        query=query,
                        **kwargs_for_compute
                    )
                    
                    # Ensure score is float or can be safely converted
                    if isinstance(current_score, (int, float)) and not pd.isna(current_score):
                        score = float(current_score)
                        df_copy.loc[i, f'{metric_name} Score'] = score
                    else: # Score is NaN or not a number
                        df_copy.loc[i, f'{metric_name} Score'] = 'N/A' # Represent as string if not valid score
                        score = np.nan # Keep internal score as NaN for logic


                    # Determine Pass/Fail for this individual metric
                    threshold = current_thresholds.get(metric_name)
                    if threshold is not None and not pd.isna(score):
                        if metric_name == "Safety": # Safety: score must be exactly threshold (usually 1.0)
                            individual_pass_fail_status = 'Pass' if score == threshold else 'Fail'
                        else: # Standard metrics: score >= threshold
                            individual_pass_fail_status = 'Pass' if score >= threshold else 'Fail'
                    elif pd.isna(score): # If score calculation resulted in NaN
                        individual_pass_fail_status = 'Error (No Score)'
                    else: # No threshold defined for this metric
                        individual_pass_fail_status = 'N/A (No Threshold)'
                    
                    df_copy.loc[i, f'{metric_name} Pass/Fail'] = individual_pass_fail_status
                    row_metric_statuses[metric_name] = individual_pass_fail_status

                except Exception as e:
                    error_detail = str(e)[:100] # Brief error for display
                    print(f"ERROR during evaluation of metric '{metric_name}' for row index {i}: {e}")
                    # Optionally log full traceback here for debugging
                    df_copy.loc[i, f'{metric_name} Score'] = 'Error'
                    df_copy.loc[i, f'{metric_name} Pass/Fail'] = 'Error (Exception)'
                    row_metric_statuses[metric_name] = 'Error (Exception)'
            
            # Calculate Overall Pass/Fail for the row based on the chosen criterion
            if selected_metrics: # Only calculate if there were metrics to evaluate
                # Get statuses of only the *selected and processed* metrics for this row
                processed_statuses = [row_metric_statuses.get(m) for m in selected_metrics if m in row_metric_statuses]

                if not processed_statuses:
                     df_copy.loc[i, overall_pass_fail_col_name] = 'Error (No Metric Results)'
                elif overall_pass_criterion == PASS_CRITERION_ALL_PASS:
                    if all(status == 'Pass' for status in processed_statuses):
                        df_copy.loc[i, overall_pass_fail_col_name] = 'Pass'
                    elif any(status and 'Error' in status for status in processed_statuses): # If any metric had an error
                        df_copy.loc[i, overall_pass_fail_col_name] = 'Error'
                    else: # Contains 'Fail' or 'N/A', and no 'Error' that wasn't handled by Pass/Fail logic
                        df_copy.loc[i, overall_pass_fail_col_name] = 'Fail'
                elif overall_pass_criterion == PASS_CRITERION_ANY_PASS:
                    if any(status == 'Pass' for status in processed_statuses):
                        df_copy.loc[i, overall_pass_fail_col_name] = 'Pass'
                    elif all(status and 'Error' in status for status in processed_statuses): # All selected metrics resulted in error
                        df_copy.loc[i, overall_pass_fail_col_name] = 'Error'
                    else: # No 'Pass', and mix of 'Fail', 'N/A', 'Error (No Score)'
                        df_copy.loc[i, overall_pass_fail_col_name] = 'Fail'
                else: # Unknown criterion
                    df_copy.loc[i, overall_pass_fail_col_name] = 'N/A (Invalid Criterion)'
            else: # No metrics were selected for evaluation
                df_copy.loc[i, overall_pass_fail_col_name] = 'N/A (No Metrics Selected)'
        
        if progress_bar: progress_bar.empty() # Clear Streamlit progress bar
        
        success_msg = "Evaluation complete!"
        try: st.success(success_msg)
        except RuntimeError: print(success_msg) # CLI
        
        return df_copy

    def get_available_metrics(self) -> list:
        """Returns a list of available metric names."""
        return list(AVAILABLE_METRICS.keys())

    def get_metric_thresholds(self) -> dict:
        """Returns a copy of the default metric thresholds."""
        return METRIC_THRESHOLDS.copy()



# # llm_eval_package/core/engine.py
# import pandas as pd
# import numpy as np
# from tqdm import tqdm # Ensure tqdm is installed if using for CLI progress
# import streamlit as st # Keep for @st.cache_resource and potential UI feedback
# import os

# # Import metric classes
# from llm_eval_package.metrics.fluency_similarity import SemanticSimilarityMetric
# from llm_eval_package.metrics.completeness import CompletenessMetric
# from llm_eval_package.metrics.conciseness import ConcisenessMetric
# from llm_eval_package.metrics.trust_factuality import TrustFactualityMetric
# from llm_eval_package.metrics.safety import SafetyMetric
# from llm_eval_package.metrics.fact_adherence import FactAdherenceMetric # <-- ADDED

# from llm_eval_package.config import (
#     METRIC_THRESHOLDS, AVAILABLE_METRICS,
#     SENTENCE_BERT_MODEL_PATH, MODEL_DIR, SENTENCE_BERT_MODEL
# )
# from llm_eval_package.utils import ModelDownloader


# @st.cache_resource # This decorator caches the function's return value across reruns
# def _get_cached_metric_instances_internal():
#     metrics_instances = {}
#     model_downloader = ModelDownloader()

#     if not os.path.exists(SENTENCE_BERT_MODEL_PATH) or not os.listdir(SENTENCE_BERT_MODEL_PATH):
#         print(f"DEBUG: Model directory {SENTENCE_BERT_MODEL_PATH} is empty or does not exist. Attempting download.")
#         # Use a placeholder for st.info/st.success if not in Streamlit context, or make conditional
#         try: # Check if streamlit is running to use st.info
#             st.info(f"Downloading required model '{SENTENCE_BERT_MODEL}' for Semantic Similarity...")
#         except Exception: # Not in streamlit context
#             print(f"Info: Downloading required model '{SENTENCE_BERT_MODEL}' for Semantic Similarity...")

#         downloaded_path = model_downloader.download_and_save_model(SENTENCE_BERT_MODEL, MODEL_DIR)
#         if not downloaded_path:
#             # This exception will be caught by the Evaluator's __init__
#             raise Exception(f"Failed to download model '{SENTENCE_BERT_MODEL}'.")
#         else:
#             try: # Check if streamlit is running to use st.success
#                 st.success(f"Model '{SENTENCE_BERT_MODEL}' downloaded successfully!")
#             except Exception:
#                 print(f"Success: Model '{SENTENCE_BERT_MODEL}' downloaded successfully!")
#     else:
#         print(f"DEBUG: Model directory {SENTENCE_BERT_MODEL_PATH} already exists.")

#     try:
#         if "Semantic Similarity" in AVAILABLE_METRICS:
#             metrics_instances["Semantic Similarity"] = SemanticSimilarityMetric(SENTENCE_BERT_MODEL_PATH)
#         if "Completeness" in AVAILABLE_METRICS:
#             metrics_instances["Completeness"] = CompletenessMetric()
#         if "Conciseness" in AVAILABLE_METRICS:
#             metrics_instances["Conciseness"] = ConcisenessMetric()
#         if "Trust & Factuality" in AVAILABLE_METRICS:
#             metrics_instances["Trust & Factuality"] = TrustFactualityMetric()
#         if "Safety" in AVAILABLE_METRICS:
#             metrics_instances["Safety"] = SafetyMetric()
#         if "Fact Adherence" in AVAILABLE_METRICS: # <-- ADDED
#             metrics_instances["Fact Adherence"] = FactAdherenceMetric()

#         print("DEBUG: All configured metric models/instances loaded successfully!")
#         return metrics_instances
#     except Exception as e:
#         print(f"DEBUG: EXCEPTION during metric model loading: {e}")
#         raise e

# class Evaluator:
#     def __init__(self):
#         try:
#             self.metrics_instances = _get_cached_metric_instances_internal()
#             # Only show toast if in Streamlit context
#             try: st.toast("All metric models loaded successfully!", icon="✅")
#             except: pass
#         except Exception as e:
#             # Handle error appropriately whether in Streamlit or CLI
#             try: st.error(f"Critical Error loading metric models: {e}. Evaluation may not work."); st.stop()
#             except: print(f"CRITICAL Error loading metric models: {e}. Evaluation may not work."); raise

#     def evaluate_dataframe(self, df: pd.DataFrame, selected_metrics: list, custom_thresholds: dict = None, sensitive_keywords: list = None) -> pd.DataFrame:
#         if df.empty:
#             # Use st.warning only if in Streamlit context
#             try: st.warning("No data to evaluate. Please upload a valid dataset.")
#             except: print("Warning: No data to evaluate.")
#             return df.copy()

#         if not self.metrics_instances:
#              try: st.error("Evaluation cannot proceed: Metric models were not initialized.")
#              except: print("Error: Evaluation cannot proceed: Metric models were not initialized.")
#              return df.copy()

#         current_thresholds = custom_thresholds if custom_thresholds is not None else METRIC_THRESHOLDS.copy()
#         df_copy = df.copy() # Work on a copy

#         for metric_name in selected_metrics:
#             if metric_name not in self.metrics_instances:
#                 msg = f"Metric '{metric_name}' is selected but not available/initialized. Skipping."
#                 try: st.warning(msg)
#                 except: print(f"Warning: {msg}")
#                 continue # Skip this metric

#             df_copy[f'{metric_name} Score'] = np.nan
#             df_copy[f'{metric_name} Pass/Fail'] = 'N/A'

#         # Progress bar handling (conditional for Streamlit)
#         progress_bar = None
#         try:
#             progress_bar = st.progress(0, text="Initializing evaluation...")
#         except Exception: # Not in Streamlit context, use tqdm for CLI
#             iterable = tqdm(df_copy.iterrows(), total=df_copy.shape[0], desc="Evaluating LLM outputs")

#         # If not using tqdm (e.g. in Streamlit), use standard iterrows
#         if progress_bar is None: # CLI mode (tqdm handles iteration)
#             pass
#         else: # Streamlit mode
#             iterable = df_copy.iterrows()


#         for i, row in iterable: # iterable is either tqdm or df.iterrows()
#             query = row.get('query', '')
#             llm_output = row.get('llm_output', '')
#             reference_answer = row.get('reference_answer', '')
#             required_facts_str = row.get('required_facts', '') # Get required_facts for the row

#             if progress_bar: # Streamlit update
#                 progress_bar.progress((i + 1) / df_copy.shape[0], text=f"Evaluating row {i+1}/{df_copy.shape[0]}")

#             for metric_name in selected_metrics:
#                 if metric_name not in self.metrics_instances:
#                     continue # Already warned above

#                 metric_instance = self.metrics_instances[metric_name]
#                 score = np.nan # Default to NaN
#                 pass_fail = 'Error'

#                 try:
#                     kwargs_for_compute = {}
#                     if metric_name == "Safety":
#                         kwargs_for_compute['sensitive_keywords'] = sensitive_keywords
#                     elif metric_name == "Fact Adherence":
#                         kwargs_for_compute['required_facts'] = required_facts_str
#                     # Other metrics might need other specific kwargs from the row if designed that way

#                     score = metric_instance.compute(
#                         llm_output=llm_output,
#                         reference_answer=reference_answer,
#                         query=query,
#                         **kwargs_for_compute
#                     )
#                     df_copy.loc[i, f'{metric_name} Score'] = score if not pd.isna(score) else 'N/A' # Store N/A if score is NaN

#                     threshold = current_thresholds.get(metric_name)
#                     if threshold is not None and not pd.isna(score):
#                         if metric_name == "Safety": # Safety passes if score is 1.0 (matches threshold)
#                             pass_fail = 'Pass' if score == threshold else 'Fail'
#                         else: # Other metrics pass if score >= threshold
#                             pass_fail = 'Pass' if score >= threshold else 'Fail'
#                     elif pd.isna(score):
#                         pass_fail = 'Error (No Score)'
#                     else: # No threshold defined
#                         pass_fail = 'N/A (No Threshold)'
#                     df_copy.loc[i, f'{metric_name} Pass/Fail'] = pass_fail

#                 except Exception as e:
#                     error_msg = f"Error evaluating {metric_name} for row index {i}: {str(e)[:100]}..."
#                     try: st.error(error_msg) # Show brief error in UI
#                     except: pass # If not in streamlit, error will be in console
#                     print(f"Detailed error for {metric_name}, row {i}: {e}")
#                     df_copy.loc[i, f'{metric_name} Score'] = 'Error'
#                     df_copy.loc[i, f'{metric_name} Pass/Fail'] = 'Error'
        
#         if progress_bar: progress_bar.empty() # Clear Streamlit progress bar
        
#         success_msg = "Evaluation complete!"
#         try: st.success(success_msg)
#         except: print(success_msg)
        
#         return df_copy

#     def get_available_metrics(self) -> list:
#         return list(AVAILABLE_METRICS.keys())

#     def get_metric_thresholds(self) -> dict:
#         return METRIC_THRESHOLDS.copy()




# # import pandas as pd
# # import numpy as np
# # from tqdm import tqdm
# # import streamlit as st
# # import os

# # # Import metric classes from the new llm_eval_package.metrics sub-package
# # from llm_eval_package.metrics.fluency_similarity import SemanticSimilarityMetric
# # from llm_eval_package.metrics.completeness import CompletenessMetric
# # from llm_eval_package.metrics.conciseness import ConcisenessMetric
# # from llm_eval_package.metrics.trust_factuality import TrustFactualityMetric
# # from llm_eval_package.metrics.safety import SafetyMetric

# # # Import configuration from the new llm_eval_package.config module
# # from llm_eval_package.config import METRIC_THRESHOLDS, AVAILABLE_METRICS, SENTENCE_BERT_MODEL_PATH, MODEL_DIR, SENTENCE_BERT_MODEL
# # # Import ModelDownloader from utils
# # from llm_eval_package.utils import ModelDownloader


# # # Define the model loading function outside the class.
# # # This function is explicitly cached by @st.cache_resource.
# # @st.cache_resource
# # def _get_cached_metric_instances_internal():
# #     """
# #     Loads and caches all metric models required.
# #     This function is cached by st.cache_resource to optimize performance across Streamlit reruns.
# #     It avoids direct st. calls to prevent issues during initial module loading.
# #     """
# #     metrics_instances = {}
    
# #     # Check and potentially download Sentence-BERT model
# #     model_downloader = ModelDownloader()
    
# #     # Ensure the model path exists and contains model files
# #     if not os.path.exists(SENTENCE_BERT_MODEL_PATH) or not os.listdir(SENTENCE_BERT_MODEL_PATH):
# #         print(f"DEBUG: Model directory {SENTENCE_BERT_MODEL_PATH} is empty or does not exist. Attempting download.")
# #         st.info(f"Downloading required model '{SENTENCE_BERT_MODEL}' for Semantic Similarity. This may take a moment...")
# #         downloaded_path = model_downloader.download_and_save_model(SENTENCE_BERT_MODEL, MODEL_DIR)
# #         if not downloaded_path:
# #             raise Exception(f"Failed to download model '{SENTENCE_BERT_MODEL}'. Please check your internet connection or model name.")
# #         else:
# #             st.success(f"Model '{SENTENCE_BERT_MODEL}' downloaded successfully!")
# #     else:
# #         print(f"DEBUG: Model directory {SENTENCE_BERT_MODEL_PATH} already exists and contains files.")


# #     print(f"DEBUG: Attempting to load metric models from {SENTENCE_BERT_MODEL_PATH}")
# #     print(f"DEBUG: Does model path exist? {os.path.exists(SENTENCE_BERT_MODEL_PATH)}")
# #     print(f"DEBUG: Contents of model directory: {os.listdir(os.path.dirname(SENTENCE_BERT_MODEL_PATH)) if os.path.exists(os.path.dirname(SENTENCE_BERT_MODEL_PATH)) else 'Directory does not exist'}")

# #     try:
# #         metrics_instances["Semantic Similarity"] = SemanticSimilarityMetric(SENTENCE_BERT_MODEL_PATH)
# #         print(f"DEBUG: Semantic Similarity Metric initialized. Model loaded: {metrics_instances['Semantic Similarity'].model is not None}")
        
# #         metrics_instances["Completeness"] = CompletenessMetric()
# #         print("DEBUG: Completeness Metric initialized.")
        
# #         metrics_instances["Conciseness"] = ConcisenessMetric()
# #         print("DEBUG: Conciseness Metric initialized.")
        
# #         metrics_instances["Trust & Factuality"] = TrustFactualityMetric()
# #         print("DEBUG: Trust & Factuality Metric initialized.")
        
# #         metrics_instances["Safety"] = SafetyMetric()
# #         print("DEBUG: Safety Metric initialized.")
        
# #         print("DEBUG: All metric models loaded successfully!")
# #         return metrics_instances
# #     except Exception as e:
# #         print(f"DEBUG: EXCEPTION during model loading: {e}")
# #         # Re-raise the exception to be caught by the calling context (Evaluator.__init__)
# #         # or handle it there with st.error and st.stop.
# #         raise e 

# # class Evaluator:
# #     """
# #     Core evaluation engine for LLM outputs.
# #     It orchestrates the application of selected metrics to the input data.
# #     """

# #     def __init__(self):
# #         """
# #         Initializes the Evaluator and retrieves necessary metric instances from the cached function.
# #         Handles potential errors during model loading.
# #         """
# #         try:
# #             self.metrics_instances = _get_cached_metric_instances_internal()
# #             st.toast("All metric models loaded successfully!", icon="✅")
# #         except Exception as e:
# #             st.error(f"Error loading metric models: {e}")
# #             self.metrics_instances = {} # Ensure instances are empty on failure
# #             st.stop() # Stop the Streamlit app if models can't load

# #     def evaluate_dataframe(self, df: pd.DataFrame, selected_metrics: list, custom_thresholds: dict = None, sensitive_keywords: list = None) -> pd.DataFrame:
# #         """
# #         Evaluates the LLM outputs in the DataFrame against selected metrics.

# #         Args:
# #             df (pd.DataFrame): DataFrame with 'query', 'llm_output', 'reference_answer' columns.
# #             selected_metrics (list): A list of metric names (strings) to apply.
# #             custom_thresholds (dict, optional): A dictionary of metric_name:threshold.
# #                                                 If provided, overrides default thresholds.
# #             sensitive_keywords (list, optional): A list of keywords for the SafetyMetric.

# #         Returns:
# #             pd.DataFrame: The DataFrame with added columns for each metric's score and pass/fail status.
# #         """
# #         if df.empty:
# #             st.warning("No data to evaluate. Please upload a valid dataset.")
# #             return df

# #         if not self.metrics_instances:
# #             st.error("Evaluation cannot proceed: Metric models were not initialized. Please check the console for errors during startup.")
# #             return df

# #         current_thresholds = custom_thresholds if custom_thresholds is not None else METRIC_THRESHOLDS

# #         for metric_name in selected_metrics:
# #             df[f'{metric_name} Score'] = np.nan
# #             df[f'{metric_name} Pass/Fail'] = 'N/A'

# #         progress_text = "Operation in progress. Please wait."
# #         my_bar = st.progress(0, text=progress_text)

# #         for i, row in tqdm(df.iterrows(), total=df.shape[0], desc="Evaluating LLM outputs"):
# #             query = row['query']
# #             llm_output = row['llm_output']
# #             reference_answer = row['reference_answer']

# #             for metric_name in selected_metrics:
# #                 if metric_name in self.metrics_instances:
# #                     metric_instance = self.metrics_instances[metric_name]
# #                     score = None
# #                     pass_fail = 'N/A'

# #                     try:
# #                         if metric_name == "Safety":
# #                             score = metric_instance.compute(llm_output=llm_output, sensitive_keywords=sensitive_keywords)
# #                         else:
# #                             score = metric_instance.compute(llm_output=llm_output, reference_answer=reference_answer, query=query)

# #                         df.loc[i, f'{metric_name} Score'] = score

# #                         threshold = current_thresholds.get(metric_name)
# #                         if threshold is not None:
# #                             if metric_name == "Safety":
# #                                 pass_fail = 'Pass' if score == threshold else 'Fail'
# #                             else:
# #                                 pass_fail = 'Pass' if score >= threshold else 'Fail'
# #                         df.loc[i, f'{metric_name} Pass/Fail'] = pass_fail

# #                     except Exception as e:
# #                         st.error(f"Error evaluating {metric_name} for row {i}: {e}")
# #                         print(f"DEBUG: Error evaluating {metric_name} for row {i}: {e}")
# #                         df.loc[i, f'{metric_name} Score'] = 'Error'
# #                         df.loc[i, f'{metric_name} Pass/Fail'] = 'Error'
# #                 else:
# #                     st.warning(f"Metric '{metric_name}' not found or not initialized. This should not happen if models loaded successfully.")
# #                     print(f"DEBUG: Metric '{metric_name}' not in self.metrics_instances. Keys: {self.metrics_instances.keys()}")

# #             my_bar.progress((i + 1) / df.shape[0], text=f"Evaluating row {i+1}/{df.shape[0]}")

# #         my_bar.empty()
# #         st.success("Evaluation complete!")
# #         return df

# #     def get_available_metrics(self) -> list:
# #         return list(AVAILABLE_METRICS.keys())

# #     def get_metric_thresholds(self) -> dict:
# #         return METRIC_THRESHOLDS
