import streamlit as st
import pandas as pd
from llm_eval_package.config import METRIC_THRESHOLDS, INTERPRETATION_CONFIG, DEFAULT_HIDDEN_COLUMNS_IN_RESULTS # Updated import path

class ResultsView:
    """
    Manages the display of evaluation results in the Streamlit application.
    """

    def __init__(self):
        """
        Initializes the ResultsView.
        """
        pass

    def _color_score_gradient(self, s, metric_name, current_thresholds):
        """
        Applies a color gradient to score columns based on their value relative to a threshold.
        Green for good, red for bad. Ensures text visibility.
        """
        if not pd.api.types.is_numeric_dtype(s):
            return [''] * len(s) # Return empty styles for non-numeric columns

        styles = []
        threshold = current_thresholds.get(metric_name, 0.5) # Default threshold if not found

        for v in s:
            if pd.isna(v) or v == 'Error':
                styles.append('background-color: #f0f2f6; color: #4a4a4a;') # Light grey, dark text
            elif metric_name == "Safety": # Safety is binary (1.0 for pass, 0.0 for fail)
                if v == 1.0:
                    styles.append('background-color: #d4edda; color: #155724;') # Light green, dark green text
                else:
                    styles.append('background-color: #f8d7da; color: #721c24;') # Light red, dark red text
            else:
                # Use a color scale that ensures readability
                # Interpolate between a light red, a neutral yellow, and a light green
                # Values closer to 1.0 are greener, closer to 0.0 are redder.
                # Adjusting based on threshold for better visual relevance
                
                # Define base colors (RGB tuples)
                color_red = (255, 200, 200) # Light Red
                color_yellow = (255, 255, 200) # Light Yellow
                color_green = (200, 255, 200) # Light Green

                if v >= threshold:
                    # Scale from threshold to 1.0 (green)
                    # Interpolate between yellow and green
                    normalized_score = (v - threshold) / (1.0 - threshold) if (1.0 - threshold) > 0 else 0
                    r = int(color_yellow[0] + normalized_score * (color_green[0] - color_yellow[0]))
                    g = int(color_yellow[1] + normalized_score * (color_green[1] - color_yellow[1]))
                    b = int(color_yellow[2] + normalized_score * (color_green[2] - color_yellow[2]))
                    styles.append(f'background-color: rgb({r},{g},{b}); color: #1a1a1a;') # Dark text
                else:
                    # Scale from 0.0 to threshold (red)
                    # Interpolate between red and yellow
                    normalized_score = v / threshold if threshold > 0 else 0
                    r = int(color_red[0] + normalized_score * (color_yellow[0] - color_red[0]))
                    g = int(color_red[1] + normalized_score * (color_yellow[1] - color_red[1]))
                    b = int(color_red[2] + normalized_score * (color_yellow[2] - color_red[2]))
                    styles.append(f'background-color: rgb({r},{g},{b}); color: #1a1a1a;') # Dark text
        return styles

    def _color_pass_fail(self, val):
        """Applies color to Pass/Fail column."""
        if val == 'Pass':
            return 'background-color: #d4edda; color: #155724;' # Light green, dark green text
        elif val == 'Fail':
            return 'background-color: #f8d7da; color: #721c24;' # Light red, dark red text
        elif val == 'Error':
            return 'background-color: #fff3cd; color: #856404;' # Light yellow/orange, dark yellow text
        else:
            return ''

    def render_results(self, df_evaluated: pd.DataFrame, selected_metrics: list, custom_thresholds: dict = None):
        """
        Renders the evaluation results, including a summary and detailed table.

        Args:
            df_evaluated (pd.DataFrame): The DataFrame containing the evaluation results.
            selected_metrics (list): A list of metric names that were evaluated.
            custom_thresholds (dict, optional): A dictionary of custom thresholds used.
                                                If None, default thresholds are used.
        """
        if df_evaluated.empty:
            st.warning("No evaluation results to display.")
            return

        st.header("📊 Evaluation Results")

        # Determine which thresholds to use for display
        current_thresholds = custom_thresholds if custom_thresholds is not None else METRIC_THRESHOLDS

        # Display overall summary
        self._display_summary(df_evaluated, selected_metrics, current_thresholds)
        
        # Display metric insights (moved above detailed table)
        self._display_metric_insights(df_evaluated, selected_metrics) # Pass df_evaluated for potential dynamic insights

        # Display detailed results table
        self._display_detailed_table(df_evaluated, selected_metrics, current_thresholds)


    def _display_summary(self, df_evaluated: pd.DataFrame, selected_metrics: list, current_thresholds: dict):
        """
        Displays a summary of the evaluation results, including pass/fail rates and average scores.
        """
        st.subheader("Summary Report")

        total_rows = len(df_evaluated)
        st.write(f"Total test cases evaluated: **{total_rows}**")

        summary_cols = st.columns(len(selected_metrics))
        for i, metric in enumerate(selected_metrics):
            if f'{metric} Pass/Fail' in df_evaluated.columns:
                pass_count = (df_evaluated[f'{metric} Pass/Fail'] == 'Pass').sum()
                fail_count = (df_evaluated[f'{metric} Pass/Fail'] == 'Fail').sum()
                error_count = (df_evaluated[f'{metric} Pass/Fail'] == 'Error').sum()
                
                pass_rate = (pass_count / total_rows) * 100 if total_rows > 0 else 0

                with summary_cols[i]:
                    st.metric(label=f"{metric} Pass Rate", value=f"{pass_rate:.2f}%")
                    st.markdown(f"<small>Pass: {pass_count}, Fail: {fail_count}, Error: {error_count}</small>", unsafe_allow_html=True)
            
            if f'{metric} Score' in df_evaluated.columns:
                numeric_scores = pd.to_numeric(df_evaluated[f'{metric} Score'], errors='coerce').dropna()
                if not numeric_scores.empty:
                    avg_score = numeric_scores.mean()
                    threshold = current_thresholds.get(metric)
                    st.markdown(f"<small>Avg Score: {avg_score:.3f} (Threshold: {threshold:.2f})</small>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<small>Avg Score: N/A</small>", unsafe_allow_html=True)


    def _display_detailed_table(self, df_evaluated: pd.DataFrame, selected_metrics: list, current_thresholds: dict):
        """
        Displays the detailed evaluation results table with styling.
        Filters out default hidden columns.
        """
        st.subheader("Detailed Results")
        
        # Identify columns to display
        columns_to_display = [col for col in df_evaluated.columns if col not in DEFAULT_HIDDEN_COLUMNS_IN_RESULTS]
        
        # Create a Styler object from the filtered DataFrame
        styled_df = df_evaluated[columns_to_display].style

        # Apply color gradient to score columns
        for metric_name in selected_metrics:
            score_col = f'{metric_name} Score'
            if score_col in columns_to_display: # Check if the score column is in the displayed columns
                styled_df = styled_df.apply(
                    self._color_score_gradient,
                    metric_name=metric_name,
                    current_thresholds=current_thresholds,
                    subset=[score_col]
                )
            
            # Apply color to Pass/Fail columns
            pass_fail_col = f'{metric_name} Pass/Fail'
            if pass_fail_col in columns_to_display: # Check if the pass/fail column is in the displayed columns
                styled_df = styled_df.applymap(self._color_pass_fail, subset=[pass_fail_col])

        # Display the styled DataFrame
        st.dataframe(styled_df, use_container_width=True)

    def _display_metric_insights(self, df_evaluated: pd.DataFrame, selected_metrics: list):
        """
        Displays insights for each selected metric and an overall performance summary.
        """
        st.subheader("💡 Metric Insights and Performance Summary")
        
        # Overall Performance Summary
        overall_pass_rates = {}
        for metric in selected_metrics:
            pass_col = f'{metric} Pass/Fail'
            if pass_col in df_evaluated.columns:
                total_rows = len(df_evaluated)
                pass_count = (df_evaluated[pass_col] == 'Pass').sum()
                pass_rate = (pass_count / total_rows) * 100 if total_rows > 0 else 0
                overall_pass_rates[metric] = pass_rate

        if overall_pass_rates:
            st.markdown("#### Overall Performance at a Glance:")
            for metric, rate in overall_pass_rates.items():
                if rate >= 80:
                    st.success(f"**{metric}**: Excellent performance! Achieved a pass rate of **{rate:.2f}%**.")
                elif rate >= 60:
                    st.info(f"**{metric}**: Good performance. Achieved a pass rate of **{rate:.2f}%**.")
                else:
                    st.warning(f"**{metric}**: Review needed. Pass rate of **{rate:.2f}%** indicates potential issues.")
            st.markdown("---")

        # Individual Metric Insights
        for metric in selected_metrics:
            insight_key = f"{metric.lower().replace(' ', '_').replace('&', '').strip()}_insight"
            insight_text = INTERPRETATION_CONFIG.get(insight_key, f"No specific insight available for {metric}.")
            st.markdown(f"**{metric}:** {insight_text}")

