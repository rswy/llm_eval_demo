import streamlit as st
from pathlib import Path
import sys
import time # Import time for sleep

# Ensure tasks module can be found for mock data generation (if not already in sys.path)
try:
    # This path assumes llm_eval_package is one level up from ui/sidebar_view.py
    project_root_for_mock_data = Path(__file__).resolve().parent.parent.parent
    if str(project_root_for_mock_data) not in sys.path:
        sys.sys.path.insert(0, str(project_root_for_mock_data))
    
    # Import mock data functions from their new location
    from llm_eval_package.data.generator import generate_mock_data_flat, save_mock_data
    MOCK_DATA_GENERATOR_AVAILABLE = True
except ImportError as e:
    st.warning(f"Could not import mock data generator: {e}. Mock data generation button will be disabled.")
    MOCK_DATA_GENERATOR_AVAILABLE = False


from llm_eval_package.config import ( # Updated import path
    AVAILABLE_METRICS, METRIC_THRESHOLDS, TASK_TYPE_MAPPING, 
    TASK_METRICS_PRESELECTION, ENABLE_TASK_SELECTION, ENABLE_METRIC_SELECTION, DEVELOPER_MODE # Import new flags
)

class SidebarView:
    """
    Manages the display and interaction of the sidebar in the Streamlit application.
    This includes data upload, metric selection, and evaluation controls.
    """

    def __init__(self):
        """
        Initializes the SidebarView.
        """
        pass

    def render_sidebar(self, file_uploader_key: int):
        """
        Renders the sidebar components and returns the user's selections.

        Args:
            file_uploader_key (int): A key used to manage the state of the file uploader.

        Returns:
            tuple: A tuple containing:
                - uploaded_file (streamlit.runtime.uploaded_file_manager.UploadedFile or None): The uploaded data file.
                - selected_metrics (list): A list of metric names selected by the user.
                - run_evaluation (bool): True if the 'Run Evaluation' button was clicked, False otherwise.
                - custom_thresholds (dict or None): A dictionary of custom thresholds if enabled, else None.
                - sensitive_keywords (list): A list of user-defined sensitive keywords.
                - selected_task_type (str): The selected task type.
                - go_to_instructions (bool): True if 'Go to Instructions' button was clicked.
        """
        st.sidebar.title("LLM Evaluation Tool")
        # Add a small logo/icon
        # st.sidebar.image("path/to/your/logo.png", use_column_width=True) # If you have a logo image
        st.sidebar.markdown("---")

        # Go to Instructions Button
        go_to_instructions = st.sidebar.button("💡 Go to Instructions", help="Learn how to use the tool.")
        st.sidebar.markdown("---") # Separator

        # 1. Data Upload Section
        st.sidebar.header("1. Upload Data")
        # Pass the key to the file uploader
        uploaded_file = st.sidebar.file_uploader("Upload your dataset (CSV or JSON)", type=["csv", "json"], key=f"file_uploader_{file_uploader_key}")

        # Add Mock Data Generation Button
        if MOCK_DATA_GENERATOR_AVAILABLE:
            if st.sidebar.button("✨ Generate Mock Data", help="Generate a sample dataset for testing."):
                with st.spinner("Generating mock data..."):
                    try:
                        # Define output directory relative to project root dynamically
                        # This path assumes the 'data' folder is at the project root
                        project_root = Path(__file__).resolve().parent.parent.parent
                        data_dir = project_root / "data"

                        mock_data = generate_mock_data_flat(num_samples_per_task=3)
                        save_mock_data(mock_data, output_dir=data_dir, base_filename="llm_eval_mock_data_generated")
                        st.toast("Mock data generated and saved to 'data/' folder! Please upload the generated file.", icon="✅") # Changed to st.toast
                        time.sleep(3) # Keep toast visible for 3 seconds
                        st.rerun() # Rerun to allow user to immediately load the new data
                    except Exception as e:
                        st.sidebar.error(f"Error generating mock data: {e}")
        else:
            st.sidebar.info("Mock data generator not available. Check dependencies/imports.")


        # 2. Task Type Selection (Conditional based on ENABLE_TASK_SELECTION)
        selected_task_type = None
        if ENABLE_TASK_SELECTION:
            st.sidebar.header("2. Select Task Type")
            selected_task_type_display = st.sidebar.selectbox(
                "Choose the task type for evaluation:",
                options=list(TASK_TYPE_MAPPING.values()),
                format_func=lambda x: x, # The format_func is applied to the options
                help="Select the type of task your LLM performs to get relevant metric suggestions."
            )
            selected_task_type = next(key for key, value in TASK_TYPE_MAPPING.items() if value == selected_task_type_display)
        else:
            # If disabled (end-user mode), fix to RAG FAQ
            selected_task_type = "rag_faq" # Fixed for end-user mode
            st.sidebar.info(f"Task Type fixed to: **{TASK_TYPE_MAPPING[selected_task_type]}** (Developer Mode Off)")


        # 3. Metric Selection Section (Conditional based on ENABLE_METRIC_SELECTION)
        selected_metrics = []
        if ENABLE_METRIC_SELECTION:
            st.sidebar.header("3. Select Metrics")
            preselected_metrics = TASK_METRICS_PRESELECTION.get(selected_task_type, [])
            preselected_metrics = [
                metric for metric in preselected_metrics if metric in AVAILABLE_METRICS
            ]
            all_metric_names = list(AVAILABLE_METRICS.keys())

            selected_metrics = st.sidebar.multiselect(
                "Choose metrics for evaluation:",
                options=all_metric_names,
                default=preselected_metrics,
                help="Select the metrics to evaluate your LLM's performance."
            )
        else:
            # If disabled (end-user mode), fix to Semantic Similarity
            selected_metrics = ["Semantic Similarity"] # Fixed for end-user mode
            st.sidebar.info(f"Metrics fixed to: **{', '.join(selected_metrics)}** (Developer Mode Off)")


        # 4. Threshold Settings
        st.sidebar.header("4. Threshold Settings")
        # In end-user mode, this is the only adjustable setting
        use_custom_thresholds = st.sidebar.checkbox(
            "Use Custom Thresholds", 
            value=True if not DEVELOPER_MODE else False, # Default to True for end-user
            help="Toggle to define your own pass/fail cut-off scores for each metric."
        )

        custom_thresholds = {}
        if use_custom_thresholds:
            st.sidebar.write("Set custom thresholds for selected metrics:")
            for metric_name in selected_metrics:
                default_threshold = METRIC_THRESHOLDS.get(metric_name, 0.5) # Default to 0.5 if not found
                # For Safety metric, the threshold is typically 1.0 (pass if 1.0)
                if metric_name == "Safety":
                    st.sidebar.markdown(f"**{metric_name}**: Output is considered safe if score is 1.0 (no sensitive keywords detected).")
                    custom_thresholds[metric_name] = 1.0 # Fixed threshold for Safety
                else:
                    custom_thresholds[metric_name] = st.sidebar.number_input(
                        f"{metric_name} Threshold",
                        min_value=0.0,
                        max_value=1.0,
                        value=float(default_threshold),
                        step=0.01,
                        key=f"custom_threshold_{metric_name}", # Unique key for each input
                        help=f"Set the minimum score for '{metric_name}' to be considered 'Pass'."
                    )
        else:
            custom_thresholds = None # Indicate that default thresholds should be used
            st.sidebar.info("Using default thresholds for all metrics.")


        # 5. Safety Keyword Input (if Safety metric is selected and in developer mode)
        sensitive_keywords = []
        if "Safety" in selected_metrics and DEVELOPER_MODE: # Only show in developer mode
            st.sidebar.header("5. Safety Keywords")
            keywords_input = st.sidebar.text_area(
                "Enter sensitive keywords (comma-separated):",
                "profanity, hate speech, violence, explicit, harmful", # Example defaults
                help="Define keywords that, if found in LLM output, will flag the response as 'unsafe'."
            )
            if keywords_input:
                sensitive_keywords = [k.strip() for k in keywords_input.split(',') if k.strip()]
            
            if not sensitive_keywords:
                st.sidebar.warning("No sensitive keywords entered for Safety metric. It will always pass.")

        # Removed Run Evaluation button from sidebar_view
        run_evaluation = False 

        return (
            uploaded_file,
            selected_metrics,
            run_evaluation, # This will always be False now
            custom_thresholds,
            sensitive_keywords,
            selected_task_type,
            go_to_instructions
        )
