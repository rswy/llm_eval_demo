# llm_eval_package/ui/results_view.py
import streamlit as st
import pandas as pd
from llm_eval_package.config import METRIC_THRESHOLDS, INTERPRETATION_CONFIG, DEFAULT_HIDDEN_COLUMNS_IN_RESULTS

class ResultsView:
    """
    Manages the display of evaluation results in the Streamlit application.
    """

    def __init__(self):
        pass

    def _color_score_gradient(self, s, metric_name, current_thresholds):
        # ... (existing code for coloring scores - no changes here)
        if not pd.api.types.is_numeric_dtype(s):
            return [''] * len(s) 

        styles = []
        threshold = current_thresholds.get(metric_name, 0.5) 

        for v in s:
            if pd.isna(v) or v == 'Error' or not isinstance(v, (int, float)): # Added check for non-numeric
                styles.append('background-color: #f0f2f6; color: #4a4a4a;') 
            elif metric_name == "Safety": 
                if v == 1.0:
                    styles.append('background-color: #d4edda; color: #155724;') 
                else:
                    styles.append('background-color: #f8d7da; color: #721c24;') 
            else:
                color_red = (255, 200, 200); color_yellow = (255, 255, 200); color_green = (200, 255, 200)
                if v >= threshold:
                    normalized_score = (v - threshold) / (1.0 - threshold) if (1.0 - threshold) > 0 else 0
                    r = int(color_yellow[0] + normalized_score * (color_green[0] - color_yellow[0]))
                    g = int(color_yellow[1] + normalized_score * (color_green[1] - color_yellow[1]))
                    b = int(color_yellow[2] + normalized_score * (color_green[2] - color_yellow[2]))
                    styles.append(f'background-color: rgb({r},{g},{b}); color: #1a1a1a;')
                else:
                    normalized_score = v / threshold if threshold > 0 else 0
                    r = int(color_red[0] + normalized_score * (color_yellow[0] - color_red[0]))
                    g = int(color_red[1] + normalized_score * (color_yellow[1] - color_red[1]))
                    b = int(color_red[2] + normalized_score * (color_yellow[2] - color_red[2]))
                    styles.append(f'background-color: rgb({r},{g},{b}); color: #1a1a1a;')
        return styles


    def _color_pass_fail(self, val):
        # ... (existing code for coloring Pass/Fail - no changes here)
        if val == 'Pass': return 'background-color: #d4edda; color: #155724;'
        elif val == 'Fail': return 'background-color: #f8d7da; color: #721c24;'
        elif val == 'Error': return 'background-color: #fff3cd; color: #856404;'
        else: return ''


    def render_results(self, df_evaluated: pd.DataFrame, selected_metrics: list, custom_thresholds: dict = None, overall_pass_fail_column: str = "Overall Pass/Fail"):
        if df_evaluated.empty:
            st.warning("No evaluation results to display.")
            return

        st.header("📊 Evaluation Results")
        current_thresholds = custom_thresholds if custom_thresholds is not None else METRIC_THRESHOLDS.copy()

        # Display overall summary
        self._display_summary(df_evaluated, selected_metrics, current_thresholds, "Overall Summary", overall_pass_fail_column=overall_pass_fail_column)
        
        self._display_metric_insights(df_evaluated, selected_metrics)

        # Display detailed results table
        self._display_detailed_table(df_evaluated, selected_metrics, current_thresholds, overall_pass_fail_column=overall_pass_fail_column)

        # --- NEW: Summary by Test Configuration ---
        if 'test_config' in df_evaluated.columns and df_evaluated['test_config'].nunique() > 1:
            st.markdown("---")
            st.subheader("📋 Summary by Test Configuration")
            
            unique_test_configs = df_evaluated['test_config'].unique()
            # Sort unique_test_configs if they are not None or NaN, otherwise keep them as is
            try:
                sorted_configs = sorted([cfg for cfg in unique_test_configs if pd.notna(cfg)])
                # Add back None or NaN if they existed
                if any(pd.isna(cfg) for cfg in unique_test_configs):
                    sorted_configs.append(None) # Or however you want to represent missing test_config
            except TypeError: # Handles mixtures of types that can't be sorted
                sorted_configs = unique_test_configs


            for config_name in sorted_configs:
                config_df = df_evaluated[df_evaluated['test_config'] == config_name]
                if pd.isna(config_name): # Handling for missing config names
                    display_name = "Uncategorized Tests"
                else:
                    display_name = str(config_name)

                with st.expander(f"Results for: **{display_name}** ({len(config_df)} test cases)"):
                    if not config_df.empty:
                        self._display_summary(config_df, selected_metrics, current_thresholds, title=None, overall_pass_fail_column=overall_pass_fail_column)
                    else:
                        st.caption("No data for this configuration.")
        # --- END NEW SECTION ---

    def _display_summary(self, df_summary: pd.DataFrame, selected_metrics: list, current_thresholds: dict, title: str = "Summary Report", overall_pass_fail_column: str = "Overall Pass/Fail"):
        if title:
            st.subheader(title)

        total_rows = len(df_summary)
        st.write(f"Total test cases in this group: **{total_rows}**")

        # --- NEW: Overall Pass Rate based on the new combined column ---
        if overall_pass_fail_column in df_summary.columns:
            overall_passed = (df_summary[overall_pass_fail_column] == 'Pass').sum()
            overall_failed = (df_summary[overall_pass_fail_column] == 'Fail').sum()
            overall_error = (df_summary[overall_pass_fail_column] == 'Error').sum() # Assuming 'Error' is possible
            overall_pass_rate = (overall_passed / total_rows) * 100 if total_rows > 0 else 0
            
            st.metric(label=f"**Overall Test Case Pass Rate**", value=f"{overall_pass_rate:.2f}%")
            st.markdown(f"<small>Passed: {overall_passed}, Failed: {overall_failed}, Errors: {overall_error} (based on selected criterion)</small>", unsafe_allow_html=True)
            st.markdown("---")
        # --- END NEW ---

        st.markdown("##### Metric-Specific Performance:")
        
        num_metrics = len(selected_metrics)
        # Determine number of columns for metrics, max 3-4 per row for readability
        cols_per_row = min(num_metrics, 3) 
        
        metric_summary_cols = st.columns(cols_per_row)
        col_idx = 0

        for i, metric in enumerate(selected_metrics):
            current_col = metric_summary_cols[col_idx % cols_per_row]
            with current_col:
                if f'{metric} Pass/Fail' in df_summary.columns:
                    pass_count = (df_summary[f'{metric} Pass/Fail'] == 'Pass').sum()
                    fail_count = (df_summary[f'{metric} Pass/Fail'] == 'Fail').sum()
                    error_count = (df_summary[f'{metric} Pass/Fail'] == 'Error').sum()
                    pass_rate = (pass_count / total_rows) * 100 if total_rows > 0 else 0
                    
                    st.metric(label=f"{metric} Pass Rate", value=f"{pass_rate:.2f}%")
                    st.caption(f"Pass: {pass_count}, Fail: {fail_count}, Error: {error_count}")
                
                if f'{metric} Score' in df_summary.columns:
                    # Convert to numeric, coercing errors. This will turn 'Error' strings into NaN.
                    numeric_scores = pd.to_numeric(df_summary[f'{metric} Score'], errors='coerce').dropna()
                    if not numeric_scores.empty:
                        avg_score = numeric_scores.mean()
                        threshold_val = current_thresholds.get(metric, "N/A")
                        threshold_display = f"{threshold_val:.2f}" if isinstance(threshold_val, (int,float)) else "N/A"
                        st.caption(f"Avg Score: {avg_score:.3f} (Thresh: {threshold_display})")
                    else:
                        st.caption(f"Avg Score: N/A")
                st.markdown("---") # Separator inside column after each metric block
            col_idx +=1


    def _display_detailed_table(self, df_evaluated: pd.DataFrame, selected_metrics: list, current_thresholds: dict, overall_pass_fail_column: str = "Overall Pass/Fail"):
        st.subheader("Detailed Results Table")
        
        columns_to_display = [col for col in df_evaluated.columns if col not in DEFAULT_HIDDEN_COLUMNS_IN_RESULTS]
        
        # Ensure 'Overall Pass/Fail' is one of the first columns if it exists
        if overall_pass_fail_column in columns_to_display:
            columns_to_display.remove(overall_pass_fail_column)
            # Try to insert after 'query', 'llm_output', 'reference_answer'
            insert_pos = 0
            core_cols = ['query', 'llm_output', 'reference_answer']
            present_core_cols = [c for c in core_cols if c in columns_to_display]
            if present_core_cols:
                insert_pos = max(columns_to_display.index(c) for c in present_core_cols) + 1
            columns_to_display.insert(insert_pos, overall_pass_fail_column)


        styled_df = df_evaluated[columns_to_display].style

        # Apply coloring
        for metric_name in selected_metrics:
            score_col = f'{metric_name} Score'
            if score_col in columns_to_display:
                styled_df = styled_df.apply(
                    self._color_score_gradient,
                    metric_name=metric_name,
                    current_thresholds=current_thresholds,
                    subset=[score_col]
                )
            
            pass_fail_col = f'{metric_name} Pass/Fail'
            if pass_fail_col in columns_to_display:
                styled_df = styled_df.applymap(self._color_pass_fail, subset=[pass_fail_col])
        
        # Style the new 'Overall Pass/Fail' column
        if overall_pass_fail_column in columns_to_display:
             styled_df = styled_df.applymap(self._color_pass_fail, subset=[overall_pass_fail_column])

        st.dataframe(styled_df, use_container_width=True, height=600) # Added height

    def _display_metric_insights(self, df_evaluated: pd.DataFrame, selected_metrics: list):
        # ... (existing code - no changes here for now, but could also be grouped by test_config if needed)
        st.markdown("---")
        st.subheader("💡 Metric Insights and Performance Summary")
        
        overall_pass_rates = {}
        for metric in selected_metrics:
            pass_col = f'{metric} Pass/Fail'
            if pass_col in df_evaluated.columns:
                total_rows = len(df_evaluated)
                pass_count = (df_evaluated[pass_col] == 'Pass').sum()
                pass_rate = (pass_count / total_rows) * 100 if total_rows > 0 else 0
                overall_pass_rates[metric] = pass_rate

        if overall_pass_rates:
            st.markdown("#### Overall Metric Performance (Across All Data):")
            for metric, rate in overall_pass_rates.items():
                if rate >= 80:
                    st.success(f"**{metric}**: Excellent! Pass rate: **{rate:.2f}%**.")
                elif rate >= 60:
                    st.info(f"**{metric}**: Good. Pass rate: **{rate:.2f}%**.")
                else:
                    st.warning(f"**{metric}**: Review Needed. Pass rate: **{rate:.2f}%**.")
            st.markdown("---")

        for metric in selected_metrics:
            insight_key = f"{metric.lower().replace(' ', '_').replace('&', '').strip()}_insight"
            insight_text = INTERPRETATION_CONFIG.get(insight_key, f"No specific insight available for {metric}.")
            st.markdown(f"**Understanding {metric}:** {insight_text}")

# import streamlit as st
# import pandas as pd
# from llm_eval_package.config import METRIC_THRESHOLDS, INTERPRETATION_CONFIG, DEFAULT_HIDDEN_COLUMNS_IN_RESULTS # Updated import path

# class ResultsView:
#     """
#     Manages the display of evaluation results in the Streamlit application.
#     """

#     def __init__(self):
#         """
#         Initializes the ResultsView.
#         """
#         pass

#     def _color_score_gradient(self, s, metric_name, current_thresholds):
#         """
#         Applies a color gradient to score columns based on their value relative to a threshold.
#         Green for good, red for bad. Ensures text visibility.
#         """
#         if not pd.api.types.is_numeric_dtype(s):
#             return [''] * len(s) # Return empty styles for non-numeric columns

#         styles = []
#         threshold = current_thresholds.get(metric_name, 0.5) # Default threshold if not found

#         for v in s:
#             if pd.isna(v) or v == 'Error':
#                 styles.append('background-color: #f0f2f6; color: #4a4a4a;') # Light grey, dark text
#             elif metric_name == "Safety": # Safety is binary (1.0 for pass, 0.0 for fail)
#                 if v == 1.0:
#                     styles.append('background-color: #d4edda; color: #155724;') # Light green, dark green text
#                 else:
#                     styles.append('background-color: #f8d7da; color: #721c24;') # Light red, dark red text
#             else:
#                 # Use a color scale that ensures readability
#                 # Interpolate between a light red, a neutral yellow, and a light green
#                 # Values closer to 1.0 are greener, closer to 0.0 are redder.
#                 # Adjusting based on threshold for better visual relevance
                
#                 # Define base colors (RGB tuples)
#                 color_red = (255, 200, 200) # Light Red
#                 color_yellow = (255, 255, 200) # Light Yellow
#                 color_green = (200, 255, 200) # Light Green

#                 if v >= threshold:
#                     # Scale from threshold to 1.0 (green)
#                     # Interpolate between yellow and green
#                     normalized_score = (v - threshold) / (1.0 - threshold) if (1.0 - threshold) > 0 else 0
#                     r = int(color_yellow[0] + normalized_score * (color_green[0] - color_yellow[0]))
#                     g = int(color_yellow[1] + normalized_score * (color_green[1] - color_yellow[1]))
#                     b = int(color_yellow[2] + normalized_score * (color_green[2] - color_yellow[2]))
#                     styles.append(f'background-color: rgb({r},{g},{b}); color: #1a1a1a;') # Dark text
#                 else:
#                     # Scale from 0.0 to threshold (red)
#                     # Interpolate between red and yellow
#                     normalized_score = v / threshold if threshold > 0 else 0
#                     r = int(color_red[0] + normalized_score * (color_yellow[0] - color_red[0]))
#                     g = int(color_red[1] + normalized_score * (color_yellow[1] - color_red[1]))
#                     b = int(color_red[2] + normalized_score * (color_yellow[2] - color_red[2]))
#                     styles.append(f'background-color: rgb({r},{g},{b}); color: #1a1a1a;') # Dark text
#         return styles

#     def _color_pass_fail(self, val):
#         """Applies color to Pass/Fail column."""
#         if val == 'Pass':
#             return 'background-color: #d4edda; color: #155724;' # Light green, dark green text
#         elif val == 'Fail':
#             return 'background-color: #f8d7da; color: #721c24;' # Light red, dark red text
#         elif val == 'Error':
#             return 'background-color: #fff3cd; color: #856404;' # Light yellow/orange, dark yellow text
#         else:
#             return ''

#     def render_results(self, df_evaluated: pd.DataFrame, selected_metrics: list, custom_thresholds: dict = None):
#         """
#         Renders the evaluation results, including a summary and detailed table.

#         Args:
#             df_evaluated (pd.DataFrame): The DataFrame containing the evaluation results.
#             selected_metrics (list): A list of metric names that were evaluated.
#             custom_thresholds (dict, optional): A dictionary of custom thresholds used.
#                                                 If None, default thresholds are used.
#         """
#         if df_evaluated.empty:
#             st.warning("No evaluation results to display.")
#             return

#         st.header("📊 Evaluation Results")

#         # Determine which thresholds to use for display
#         current_thresholds = custom_thresholds if custom_thresholds is not None else METRIC_THRESHOLDS

#         # Display overall summary
#         self._display_summary(df_evaluated, selected_metrics, current_thresholds)
        
#         # Display metric insights (moved above detailed table)
#         self._display_metric_insights(df_evaluated, selected_metrics) # Pass df_evaluated for potential dynamic insights

#         # Display detailed results table
#         self._display_detailed_table(df_evaluated, selected_metrics, current_thresholds)


#     def _display_summary(self, df_evaluated: pd.DataFrame, selected_metrics: list, current_thresholds: dict):
#         """
#         Displays a summary of the evaluation results, including pass/fail rates and average scores.
#         """
#         st.subheader("Summary Report")

#         total_rows = len(df_evaluated)
#         st.write(f"Total test cases evaluated: **{total_rows}**")

#         summary_cols = st.columns(len(selected_metrics))
#         for i, metric in enumerate(selected_metrics):
#             if f'{metric} Pass/Fail' in df_evaluated.columns:
#                 pass_count = (df_evaluated[f'{metric} Pass/Fail'] == 'Pass').sum()
#                 fail_count = (df_evaluated[f'{metric} Pass/Fail'] == 'Fail').sum()
#                 error_count = (df_evaluated[f'{metric} Pass/Fail'] == 'Error').sum()
                
#                 pass_rate = (pass_count / total_rows) * 100 if total_rows > 0 else 0

#                 with summary_cols[i]:
#                     st.metric(label=f"{metric} Pass Rate", value=f"{pass_rate:.2f}%")
#                     st.markdown(f"<small>Pass: {pass_count}, Fail: {fail_count}, Error: {error_count}</small>", unsafe_allow_html=True)
            
#             if f'{metric} Score' in df_evaluated.columns:
#                 numeric_scores = pd.to_numeric(df_evaluated[f'{metric} Score'], errors='coerce').dropna()
#                 if not numeric_scores.empty:
#                     avg_score = numeric_scores.mean()
#                     threshold = current_thresholds.get(metric)
#                     st.markdown(f"<small>Avg Score: {avg_score:.3f} (Threshold: {threshold:.2f})</small>", unsafe_allow_html=True)
#                 else:
#                     st.markdown(f"<small>Avg Score: N/A</small>", unsafe_allow_html=True)


#     def _display_detailed_table(self, df_evaluated: pd.DataFrame, selected_metrics: list, current_thresholds: dict):
#         """
#         Displays the detailed evaluation results table with styling.
#         Filters out default hidden columns.
#         """
#         st.subheader("Detailed Results")
        
#         # Identify columns to display
#         columns_to_display = [col for col in df_evaluated.columns if col not in DEFAULT_HIDDEN_COLUMNS_IN_RESULTS]
        
#         # Create a Styler object from the filtered DataFrame
#         styled_df = df_evaluated[columns_to_display].style

#         # Apply color gradient to score columns
#         for metric_name in selected_metrics:
#             score_col = f'{metric_name} Score'
#             if score_col in columns_to_display: # Check if the score column is in the displayed columns
#                 styled_df = styled_df.apply(
#                     self._color_score_gradient,
#                     metric_name=metric_name,
#                     current_thresholds=current_thresholds,
#                     subset=[score_col]
#                 )
            
#             # Apply color to Pass/Fail columns
#             pass_fail_col = f'{metric_name} Pass/Fail'
#             if pass_fail_col in columns_to_display: # Check if the pass/fail column is in the displayed columns
#                 styled_df = styled_df.applymap(self._color_pass_fail, subset=[pass_fail_col])

#         # Display the styled DataFrame
#         st.dataframe(styled_df, use_container_width=True)

#     def _display_metric_insights(self, df_evaluated: pd.DataFrame, selected_metrics: list):
#         """
#         Displays insights for each selected metric and an overall performance summary.
#         """
#         st.subheader("💡 Metric Insights and Performance Summary")
        
#         # Overall Performance Summary
#         overall_pass_rates = {}
#         for metric in selected_metrics:
#             pass_col = f'{metric} Pass/Fail'
#             if pass_col in df_evaluated.columns:
#                 total_rows = len(df_evaluated)
#                 pass_count = (df_evaluated[pass_col] == 'Pass').sum()
#                 pass_rate = (pass_count / total_rows) * 100 if total_rows > 0 else 0
#                 overall_pass_rates[metric] = pass_rate

#         if overall_pass_rates:
#             st.markdown("#### Overall Performance at a Glance:")
#             for metric, rate in overall_pass_rates.items():
#                 if rate >= 80:
#                     st.success(f"**{metric}**: Excellent performance! Achieved a pass rate of **{rate:.2f}%**.")
#                 elif rate >= 60:
#                     st.info(f"**{metric}**: Good performance. Achieved a pass rate of **{rate:.2f}%**.")
#                 else:
#                     st.warning(f"**{metric}**: Review needed. Pass rate of **{rate:.2f}%** indicates potential issues.")
#             st.markdown("---")

#         # Individual Metric Insights
#         for metric in selected_metrics:
#             insight_key = f"{metric.lower().replace(' ', '_').replace('&', '').strip()}_insight"
#             insight_text = INTERPRETATION_CONFIG.get(insight_key, f"No specific insight available for {metric}.")
#             st.markdown(f"**{metric}:** {insight_text}")

