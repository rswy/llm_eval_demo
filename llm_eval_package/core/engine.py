import pandas as pd
import numpy as np
from tqdm import tqdm
import streamlit as st
import os

# Import metric classes from the new llm_eval_package.metrics sub-package
from llm_eval_package.metrics.fluency_similarity import SemanticSimilarityMetric
from llm_eval_package.metrics.completeness import CompletenessMetric
from llm_eval_package.metrics.conciseness import ConcisenessMetric
from llm_eval_package.metrics.trust_factuality import TrustFactualityMetric
from llm_eval_package.metrics.safety import SafetyMetric

# Import configuration from the new llm_eval_package.config module
from llm_eval_package.config import METRIC_THRESHOLDS, AVAILABLE_METRICS, SENTENCE_BERT_MODEL_PATH, MODEL_DIR, SENTENCE_BERT_MODEL
# Import ModelDownloader from utils
from llm_eval_package.utils import ModelDownloader


# Define the model loading function outside the class.
# This function is explicitly cached by @st.cache_resource.
@st.cache_resource
def _get_cached_metric_instances_internal():
    """
    Loads and caches all metric models required.
    This function is cached by st.cache_resource to optimize performance across Streamlit reruns.
    It avoids direct st. calls to prevent issues during initial module loading.
    """
    metrics_instances = {}
    
    # Check and potentially download Sentence-BERT model
    model_downloader = ModelDownloader()
    
    # Ensure the model path exists and contains model files
    if not os.path.exists(SENTENCE_BERT_MODEL_PATH) or not os.listdir(SENTENCE_BERT_MODEL_PATH):
        print(f"DEBUG: Model directory {SENTENCE_BERT_MODEL_PATH} is empty or does not exist. Attempting download.")
        st.info(f"Downloading required model '{SENTENCE_BERT_MODEL}' for Semantic Similarity. This may take a moment...")
        downloaded_path = model_downloader.download_and_save_model(SENTENCE_BERT_MODEL, MODEL_DIR)
        if not downloaded_path:
            raise Exception(f"Failed to download model '{SENTENCE_BERT_MODEL}'. Please check your internet connection or model name.")
        else:
            st.success(f"Model '{SENTENCE_BERT_MODEL}' downloaded successfully!")
    else:
        print(f"DEBUG: Model directory {SENTENCE_BERT_MODEL_PATH} already exists and contains files.")


    print(f"DEBUG: Attempting to load metric models from {SENTENCE_BERT_MODEL_PATH}")
    print(f"DEBUG: Does model path exist? {os.path.exists(SENTENCE_BERT_MODEL_PATH)}")
    print(f"DEBUG: Contents of model directory: {os.listdir(os.path.dirname(SENTENCE_BERT_MODEL_PATH)) if os.path.exists(os.path.dirname(SENTENCE_BERT_MODEL_PATH)) else 'Directory does not exist'}")

    try:
        metrics_instances["Semantic Similarity"] = SemanticSimilarityMetric(SENTENCE_BERT_MODEL_PATH)
        print(f"DEBUG: Semantic Similarity Metric initialized. Model loaded: {metrics_instances['Semantic Similarity'].model is not None}")
        
        metrics_instances["Completeness"] = CompletenessMetric()
        print("DEBUG: Completeness Metric initialized.")
        
        metrics_instances["Conciseness"] = ConcisenessMetric()
        print("DEBUG: Conciseness Metric initialized.")
        
        metrics_instances["Trust & Factuality"] = TrustFactualityMetric()
        print("DEBUG: Trust & Factuality Metric initialized.")
        
        metrics_instances["Safety"] = SafetyMetric()
        print("DEBUG: Safety Metric initialized.")
        
        print("DEBUG: All metric models loaded successfully!")
        return metrics_instances
    except Exception as e:
        print(f"DEBUG: EXCEPTION during model loading: {e}")
        # Re-raise the exception to be caught by the calling context (Evaluator.__init__)
        # or handle it there with st.error and st.stop.
        raise e 

class Evaluator:
    """
    Core evaluation engine for LLM outputs.
    It orchestrates the application of selected metrics to the input data.
    """

    def __init__(self):
        """
        Initializes the Evaluator and retrieves necessary metric instances from the cached function.
        Handles potential errors during model loading.
        """
        try:
            self.metrics_instances = _get_cached_metric_instances_internal()
            st.toast("All metric models loaded successfully!", icon="✅")
        except Exception as e:
            st.error(f"Error loading metric models: {e}")
            self.metrics_instances = {} # Ensure instances are empty on failure
            st.stop() # Stop the Streamlit app if models can't load

    def evaluate_dataframe(self, df: pd.DataFrame, selected_metrics: list, custom_thresholds: dict = None, sensitive_keywords: list = None) -> pd.DataFrame:
        """
        Evaluates the LLM outputs in the DataFrame against selected metrics.

        Args:
            df (pd.DataFrame): DataFrame with 'query', 'llm_output', 'reference_answer' columns.
            selected_metrics (list): A list of metric names (strings) to apply.
            custom_thresholds (dict, optional): A dictionary of metric_name:threshold.
                                                If provided, overrides default thresholds.
            sensitive_keywords (list, optional): A list of keywords for the SafetyMetric.

        Returns:
            pd.DataFrame: The DataFrame with added columns for each metric's score and pass/fail status.
        """
        if df.empty:
            st.warning("No data to evaluate. Please upload a valid dataset.")
            return df

        if not self.metrics_instances:
            st.error("Evaluation cannot proceed: Metric models were not initialized. Please check the console for errors during startup.")
            return df

        current_thresholds = custom_thresholds if custom_thresholds is not None else METRIC_THRESHOLDS

        for metric_name in selected_metrics:
            df[f'{metric_name} Score'] = np.nan
            df[f'{metric_name} Pass/Fail'] = 'N/A'

        progress_text = "Operation in progress. Please wait."
        my_bar = st.progress(0, text=progress_text)

        for i, row in tqdm(df.iterrows(), total=df.shape[0], desc="Evaluating LLM outputs"):
            query = row['query']
            llm_output = row['llm_output']
            reference_answer = row['reference_answer']

            for metric_name in selected_metrics:
                if metric_name in self.metrics_instances:
                    metric_instance = self.metrics_instances[metric_name]
                    score = None
                    pass_fail = 'N/A'

                    try:
                        if metric_name == "Safety":
                            score = metric_instance.compute(llm_output=llm_output, sensitive_keywords=sensitive_keywords)
                        else:
                            score = metric_instance.compute(llm_output=llm_output, reference_answer=reference_answer, query=query)

                        df.loc[i, f'{metric_name} Score'] = score

                        threshold = current_thresholds.get(metric_name)
                        if threshold is not None:
                            if metric_name == "Safety":
                                pass_fail = 'Pass' if score == threshold else 'Fail'
                            else:
                                pass_fail = 'Pass' if score >= threshold else 'Fail'
                        df.loc[i, f'{metric_name} Pass/Fail'] = pass_fail

                    except Exception as e:
                        st.error(f"Error evaluating {metric_name} for row {i}: {e}")
                        print(f"DEBUG: Error evaluating {metric_name} for row {i}: {e}")
                        df.loc[i, f'{metric_name} Score'] = 'Error'
                        df.loc[i, f'{metric_name} Pass/Fail'] = 'Error'
                else:
                    st.warning(f"Metric '{metric_name}' not found or not initialized. This should not happen if models loaded successfully.")
                    print(f"DEBUG: Metric '{metric_name}' not in self.metrics_instances. Keys: {self.metrics_instances.keys()}")

            my_bar.progress((i + 1) / df.shape[0], text=f"Evaluating row {i+1}/{df.shape[0]}")

        my_bar.empty()
        st.success("Evaluation complete!")
        return df

    def get_available_metrics(self) -> list:
        return list(AVAILABLE_METRICS.keys())

    def get_metric_thresholds(self) -> dict:
        return METRIC_THRESHOLDS
