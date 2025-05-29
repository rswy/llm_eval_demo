# # import streamlit as st
# # import pandas as pd

# # class TutorialView:
# #     """
# #     Manages the display of the tutorial/how-to-use section in the Streamlit application.
# #     """

# #     def __init__(self):
# #         """
# #         Initializes the TutorialView.
# #         """
# #         pass

# #     def render_tutorial(self):
# #         """
# #         Renders the tutorial content.
# #         """
# #         st.header("Welcome to the LLM Evaluation Dashboard!")
# #         st.markdown(
# #             """
# #             This tool helps you evaluate the performance of your Large Language Models (LLMs)
# #             based on various natural language processing metrics. You can evaluate datasets
# #             where you provide the LLM's responses, or you can use this tool to fetch
# #             live responses from a configured RAG chatbot for your queries and then evaluate them.
# #             """
# #         )

# #         st.subheader("How to Use: Graphical User Interface (GUI)")
# #         st.markdown(
# #             """
# #             Follow these steps to evaluate your LLM using the dashboard:
# #             """
# #         )

# #         st.markdown("### Step 1: Upload Your Data")
# #         st.markdown(
# #             """
# #             - On the left sidebar, use the "Upload your dataset (CSV or JSON)" button to upload your evaluation data.
# #             - **Required columns for basic evaluation**: `query`, `llm_output`, `reference_answer`.
# #             - **For fetching live bot responses**: Your uploaded file needs at least a `query` column. The `llm_output` column will be populated by the tool. It's recommended to also include `reference_answer` if you plan to evaluate against it later.
# #             - **Optional columns**: `test_description`, `test_config` (useful for filtering/grouping).
# #             """
# #         )
# #         st.info("Example CSV/JSON structure (if `llm_output` is pre-filled):")
# #         example_data_prefilled = {
# #             'query': ['What is the capital of France?', 'Summarize Hamlet.'],
# #             'llm_output': ['Paris is the capital.', 'Hamlet is about revenge.'],
# #             'reference_answer': ['The capital of France is Paris.', 'Hamlet is a tragedy by Shakespeare...'],
# #             'test_description': ['Factual question', 'Summarization task'],
# #             'test_config': ['Geography', 'Literature']
# #         }
# #         example_df_prefilled = pd.DataFrame(example_data_prefilled)
# #         st.dataframe(example_df_prefilled, use_container_width=True)

# #         st.markdown(
# #             """
# #             If you intend to fetch live responses, your `llm_output` column can be empty or absent initially.
# #             """
# #         )

# #         st.markdown("### Step 2: Configure Bot Settings (Optional - For Fetching Live Responses)")
# #         st.markdown(
# #             """
# #             If you want the tool to get responses from your RAG chatbot:
# #             - **Select Bot Domain**: In the sidebar ("1b. Bot Domain Config"), choose the appropriate domain for your RAG chatbot (e.g., 'SG Branch', 'HR').
# #             - **API Token**: In the main dashboard area (after uploading data and before running evaluation), an optional field for "API Authorization Token (Bearer)" will appear.
# #                 - If your RAG bot requires an API token, you can enter it here.
# #                 - If not provided, the tool will attempt to use a default token configured in the backend.
# #                 - **Important**: Ensure the token used is valid and has the necessary permissions. For security, avoid using long-lived tokens if possible.
# #             """
# #         )

# #         st.markdown("### Step 3: Fetch Live Bot Responses (Optional)")
# #         st.markdown(
# #             """
# #             - If you've configured bot settings and want to get live responses:
# #             - Click the "🔗 **Fetch Bot Responses & Update Data**" button in the main area of the dashboard.
# #             - This will use the `query` column from your uploaded data, call the selected bot domain's API, and populate the `llm_output` column in the data table shown in the app.
# #             - The data preview will update to show the fetched responses.
# #             - If your uploaded data already contains the `llm_output` you wish to evaluate, you can skip this step.
# #             """
# #         )

# #         st.markdown("### Step 4: Select Task Type & Metrics (For Evaluation)")
# #         st.markdown(
# #             """
# #             These settings are for the evaluation phase that runs *after* you have the `llm_output` (either pre-filled or fetched).
# #             - **Select Task Type** `<Developer Version Only>`: In the sidebar, choose the task type (e.g., RAG FAQ). This can help pre-select relevant metrics.
# #             - **Select Metrics** `<Developer Version Only>`: In the sidebar, choose the metrics for evaluation (e.g., Semantic Similarity, Safety). Some may be pre-selected based on the task type.
# #             - _In the end-user version, Task Type and Metrics are typically fixed for simplicity (e.g., to RAG FAQ and Semantic Similarity)._
# #             """
# #         )

# #         st.markdown("### Step 5: Set Thresholds & Safety Keywords (For Evaluation)")
# #         st.markdown(
# #             """
# #             - **Thresholds**: In the sidebar, you can use default pass/fail thresholds for each metric or toggle "Use Custom Thresholds" to define your own.
# #             - **Safety Keywords** `<Developer Version Only>`: If the "Safety" metric is selected (and you're in developer mode), an input for sensitive keywords will appear. LLM outputs containing these keywords will fail the Safety metric.
# #             """
# #         )

# #         st.markdown("### Step 6: Run Evaluation")
# #         st.markdown(
# #             """
# #             - Once your data has the `query`, `reference_answer`, and `llm_output` columns ready, and you've configured your desired metrics:
# #             - Click the "🚀 **Run Evaluation**" button in the main dashboard area.
# #             - The tool will process your data and calculate scores for each selected metric.
# #             """
# #         )

# #         st.markdown("### Step 7: View Results & Download")
# #         st.markdown(
# #             """
# #             - After evaluation, the dashboard will display a summary report (pass rates, average scores) and a detailed table with scores for each test case.
# #             - You can download the full results as a CSV file using the "Download Results as CSV" button.
# #             """
# #         )

# #         st.markdown("---")
# #         st.subheader("How to Use: Command Line Interface (CLI)")
# #         st.markdown(
# #             """
# #             For automated batch processing, you can use the CLI. The process typically involves two main commands run from your project's root directory:
# #             1. `fetch-responses`: To get live responses from your RAG bot.
# #             2. `evaluate`: To evaluate the responses.
# #             """
# #         )

# #         st.markdown("#### Part 1: Fetching Live Bot Responses via CLI")
# #         st.markdown(
# #             """
# #             1.  **Prepare Input CSV**: Create a CSV file (e.g., `input_queries.csv`) with at least a `query` column. Include other columns like `reference_answer`, `id`, etc., as needed.
# #             2.  **API Token**:
# #                 - The script `llm_eval_package/data/rag_input_processor.py` contains default API configurations. **You MUST update the `DEFAULT_API_HEADERS` with a valid Bearer token in that file.**
# #                 - Alternatively, you can pass the token via the `--api_token` argument to the `fetch-responses` command.
# #             3.  **Run Command**:
# #                 ```bash
# #                 python main.py fetch-responses \\
# #                     --input_queries_csv path/to/your/input_queries.csv \\
# #                     --output_eval_data_csv path/to/output_with_responses.csv \\
# #                     --domain_key "SG Branch" \\
# #                     --query_column "query" \\
# #                     # Optional: --api_token "your_bearer_token_here"
# #                 ```
# #                 - Replace placeholders with your actual file paths and desired domain key (e.g., "HR", "Finance" - see `rag_input_processor.py` for available keys in `DEFAULT_DOMAINS`).
# #                 - This command reads `input_queries.csv`, calls the API for each query in the specified domain, and saves the results (including a new `llm_output` column) to `output_with_responses.csv`.
# #             """
# #         )

# #         st.markdown("#### Part 2: Evaluating Responses via CLI")
# #         st.markdown(
# #             """
# #             1.  **Input Data**: Use the output file generated from Part 1 (e.g., `output_with_responses.csv`) as input for this step. This file now contains the `llm_output` from the bot.
# #             2.  **Run Command**:
# #                 ```bash
# #                 python main.py evaluate \\
# #                     --input_file path/to/output_with_responses.csv \\
# #                     --output_file path/to/evaluation_results.csv \\
# #                     --metrics "Semantic Similarity,Safety" \\
# #                     --task_type "rag_faq" \\
# #                     # Optional: --custom_thresholds "Semantic Similarity=0.8"
# #                     # Optional: --sensitive_keywords "sensitive_word1,sensitive_word2"
# #                 ```
# #                 - This command evaluates the `llm_output` against the `reference_answer` using the specified metrics and saves the detailed results to `evaluation_results.csv`.
# #             """
# #         )
# #         st.markdown("---")
# #         st.markdown("Enjoy evaluating your LLMs!")
# # llm_eval_package/ui/tutorial_view.py
# import streamlit as st
# import pandas as pd

# class TutorialView:
#     """
#     Manages the display of the tutorial/how-to-use section in the Streamlit application.
#     """

#     def __init__(self):
#         pass

#     def render_tutorial(self):
#         st.header("Evaluate your Large Language Models with confidence!")
#         st.info(
#             """
#             This tool helps you evaluate the performance of your bank's Large Language Models (LLMs)
#             based on key quality metrics. You can evaluate datasets where you provide the LLM's
#             responses, or use this tool to fetch live responses from a configured RAG chatbot
#             for your queries and then evaluate them.
#             """
#         )

#         # --- Section: Understanding Input Data ---
#         st.subheader("Understanding Your Input Data")
#         st.markdown(
#             """
#             To evaluate your LLM, you'll need to provide data in a specific CSV or JSON format.
#             Here's a breakdown of the columns:
#             """
#         )
#         cols_data = {
#             "Column Name": [
#                 "`query`",
#                 "`reference_answer`",
#                 "`llm_output`",
#                 "`required_facts`",
#                 "`test_description`",
#                 "`test_config`"
#             ],
#             "Requirement": [
#                 "**Required**",
#                 "**Required** (for most metrics)",
#                 "Required (can be auto-fetched)",
#                 "*Optional* (for Fact Adherence metric)",
#                 "*Optional*",
#                 "*Optional*"
#             ],
#             "Purpose": [
#                 "The question or prompt given to the LLM (e.g., 'What are the mortgage interest rates?').",
#                 "The ideal, human-written, or ground-truth answer to the query.",
#                 "The actual response generated by the LLM. If using the 'Fetch Bot Responses' feature, this column can be initially empty and will be populated by the tool.",
#                 "A list of specific facts that *must* be present in the `llm_output` for the response to be considered factually complete for the test case. Separate facts with a semicolon (e.g., 'Interest rate is 3.5%; Minimum loan is $100,000; Offer valid until Dec 31').",
#                 "A brief description of what this specific test case is trying to achieve (e.g., 'Verify current savings account interest rate query').",
#                 "A category or tag for the test case, useful for filtering or grouping results (e.g., 'SavingsAccount', 'MortgageInquiry', 'InternalPolicy'). See more examples below."
#             ]
#         }
#         st.table(pd.DataFrame(cols_data))

#         st.markdown("#### Example Data Structures for Banking Scenarios:")

#         st.markdown("##### 1. Bank Branch Operations Example:")
#         branch_data = {
#             'query': ["What are the Saturday hours for the Orchard branch?", "How do I open a new current account?"],
#             'llm_output': ["The Orchard branch is open from 9 AM to 1 PM on Saturdays.", "To open a new current account, you need to provide your NRIC, proof of address, and an initial deposit of $500. You can start the application online or visit any branch."],
#             'reference_answer': ["Orchard branch Saturday hours are 9:00 AM - 1:00 PM.", "To open a current account, please provide your NRIC or passport, recent proof of address (e.g., utility bill), and a minimum initial deposit of $500. Applications can be initiated online or at a branch."],
#             'required_facts': ["9 AM to 1 PM;Saturdays", "NRIC;proof of address;$500 deposit"],
#             'test_description': ["Check Orchard branch Saturday operating hours", "Verify steps for new current account opening"],
#             'test_config': ["Branch_Hours_Orchard", "AccountOpening_CurrentAccount"]
#         }
#         st.dataframe(pd.DataFrame(branch_data), use_container_width=True)

#         st.markdown("##### 2. Finance/Investment Product Example:")
#         finance_data = {
#             'query': ["What's the current interest rate for a 12-month fixed deposit?", "Explain the risks of unit trust investments."],
#             'llm_output': ["The current interest for a 12-month fixed deposit is 3.5% p.a. for amounts above $10,000.", "Unit trusts are subject to market fluctuations and there's no guarantee of returns. You might lose your principal investment."],
#             'reference_answer': ["For a 12-month fixed deposit, the promotional interest rate is 3.50% per annum for deposits of $10,000 and above. Standard rates apply for other amounts.", "Investing in unit trusts involves risks, including market risk where the value of your investment can go down as well as up. Past performance is not indicative of future results, and you may lose the principal amount invested. It is important to read the prospectus and understand the specific risks of a fund before investing."],
#             'required_facts': ["3.5% p.a.;12-month", "market fluctuations;no guarantee;lose principal"],
#             'test_description': ["Verify 12-month FD interest rate", "Explain unit trust investment risks accurately"],
#             'test_config': ["FixedDeposit_Rates_12M", "UnitTrust_RiskDisclosure"]
#         }
#         st.dataframe(pd.DataFrame(finance_data), use_container_width=True)

#         st.markdown("##### 3. Wholesale Banking Example (Trade Finance):")
#         wholesale_data = {
#             'query': ["What documents are required for a Letter of Credit application?", "What is the typical processing time for an import LC?"],
#             'llm_output': ["For an LC, you need an application form, proforma invoice, and transport documents.", "Import LCs are usually processed in 2-3 business days."],
#             'reference_answer': ["To apply for a Letter of Credit, you generally need to submit a completed LC application form, a copy of the proforma invoice or sales contract, and details of the shipping terms. Additional documents may be required based on the transaction.", "The standard processing time for an import Letter of Credit, once all required documents are submitted correctly, is typically 2 to 3 working days."],
#             'required_facts': ["application form;proforma invoice", "2-3 business days"],
#             'test_description': ["Check required documents for LC application", "Verify processing time for import LC"],
#             'test_config': ["TradeFinance_LC_Docs", "TradeFinance_LC_ProcessingTime"]
#         }
#         st.dataframe(pd.DataFrame(wholesale_data), use_container_width=True)

#         st.markdown("##### 4. HR Policy Example (Internal for Bank Employees):")
#         hr_data = {
#             'query': ["What is the bank's policy on paternity leave?", "How many days of medical leave am I entitled to per year?"],
#             'llm_output': ["Eligible male employees get 2 weeks of paternity leave.", "You are entitled to 14 days of outpatient medical leave and 60 days of hospitalization leave annually."],
#             'reference_answer': ["Eligible male employees are entitled to 2 weeks of Government-Paid Paternity Leave (GPPL) and an additional 2 weeks of shared parental leave, subject to specific criteria.", "Employees are entitled to 14 days of paid outpatient sick leave and up to 60 days of paid hospitalisation leave per year, inclusive of the 14 days of outpatient sick leave."],
#             'required_facts': ["2 weeks paternity leave", "14 days outpatient;60 days hospitalization"],
#             'test_description': ["Verify paternity leave entitlement", "Verify medical leave entitlement"],
#             'test_config': ["HR_LeavePolicy_Paternity", "HR_LeavePolicy_Medical"]
#         }
#         st.dataframe(pd.DataFrame(hr_data), use_container_width=True)


#         # --- Section: GUI Workflow ---
#         st.subheader("How to Use: Graphical User Interface (GUI)")
#         st.markdown("Follow these steps for evaluation:")

#         st.markdown("##### Step 1: Upload Your Data File")
#         st.markdown(
#             """
#             - In the sidebar, click "Upload your dataset (CSV or JSON)".
#             - If your `llm_output` column is already populated, you can proceed directly to evaluation configuration (Step 4).
#             - If you want the tool to fetch live responses from your RAG chatbot, ensure your file has a `query` column. The `llm_output` column will be auto-populated in a later step.
#             """
#         )

#         st.markdown("##### Step 2: Configure Bot Settings (Only if Fetching Live Responses)")
#         st.markdown(
#             """
#             - **Select Bot Domain**: In the sidebar ("1b. Bot Domain Config"), choose the bot domain (e.g., 'SG Branch', 'HR').
#             - **API Token (Optional)**: In the main dashboard area, an "API Authorization Token (Bearer)" field will appear. Enter a valid token if needed. If left blank, a default token from the system configuration will be used (ensure it's correctly set up by your administrator).
#             """
#         )

#         st.markdown("##### Step 3: Fetch Live Bot Responses (Only if `llm_output` is not pre-filled)")
#         st.markdown(
#             """
#             - Click the "🔗 **Fetch Bot Responses & Update Data**" button in the main area.
#             - The tool will use the `query` column from your data to call the selected bot's API.
#             - The `llm_output` column in the data table will be updated with the bot's live responses.
#             """
#         )

#         st.markdown("##### Step 4: Select Metrics & Configure Evaluation Settings")
#         st.markdown(
#             """
#             - **Select Metrics** `<Developer Version Only>`: In the sidebar, choose the metrics for evaluation (e.g., Semantic Similarity, Fact Adherence, Safety).
#               _In the end-user version, specific metrics relevant to banking tasks are typically pre-selected._
#             - **Thresholds**: Define pass/fail thresholds for metrics in the sidebar, or use defaults.
#             - **Safety Keywords** `<Developer Version Only>`: For the "Safety" metric, specify any sensitive keywords.
#             - **Fact Adherence**: If using the "Fact Adherence" metric, ensure your uploaded data includes the `required_facts` column, with facts separated by semicolons (`;`).
#             """
#         )
#         st.markdown("###### Mapping Business Needs to Technical Metrics (Examples for Bankers):")
#         st.markdown(
#             """
#             Even if you're not familiar with the technical NLP metrics, here's how they relate to common banking evaluation goals:

#             * **Is the bot's answer relevant and does it mean the same as the correct answer?**
#                 * Use: `Semantic Similarity`
#                 * *Scenario*: A customer asks "What are the fees for a Fast transfer?" The bot responds with information about PayNow fees. While related to transfers, it's not what was asked. Semantic Similarity would score lower if the *meaning* deviates significantly from a reference answer about Fast transfer fees.
#             * **Does the bot provide all the key pieces of information it's supposed to?**
#                 * Use: `Completeness` (general coverage) and/or `Fact Adherence` (specific facts).
#                 * *Scenario (Completeness)*: A customer asks for details about a new savings account. The reference answer lists interest rate, minimum balance, fall-below fees, and eligibility. If the bot only mentions interest rate and minimum balance, `Completeness` would be lower.
#                 * *Scenario (Fact Adherence)*: For the same query, your `required_facts` column might list "Interest rate is 1.5%; Minimum balance $1000; Fall-below fee $2". The `Fact Adherence` metric checks if *these specific facts* are in the bot's response.
#             * **Is the bot's answer brief and to the point, without unnecessary chatter?**
#                 * Use: `Conciseness`
#                 * *Scenario*: Customer asks "Orchard branch phone number?" A concise answer is "The Orchard branch phone number is 6123-4567." A less concise one might be "Thank you for asking about our Orchard branch, which is one of our flagship locations. The phone number you requested for the Orchard branch is 6123-4567. Feel free to call them." `Conciseness` would score the first answer higher.
#             * **Is the bot's answer factually correct based on our standard information or specific points we define?**
#                 * Use: `Trust & Factuality` (compares to reference answer) and/or `Fact Adherence` (compares to your defined list of crucial facts).
#                 * *Scenario*: A query about loan eligibility criteria. The `Trust & Factuality` score will be high if the bot's response matches the official eligibility criteria in the `reference_answer`. `Fact Adherence` would check if specific criteria like "Minimum income S$30,000; Age 21-60" (from your `required_facts` column) are mentioned.
#             * **Does the bot avoid using inappropriate or restricted language/keywords?**
#                 * Use: `Safety`
#                 * *Scenario*: Ensuring the bot doesn't use overly casual slang, mention competitor products (if restricted), or discuss confidential internal codes. You'd list these as "sensitive keywords."
#             """
#         )


#         st.markdown("##### Step 5: Run Evaluation")
#         st.markdown(
#             """
#             - Click the "🚀 **Run Evaluation**" button in the main dashboard area.
#             - The tool calculates scores for each selected metric against your data.
#             """
#         )

#         st.markdown("##### Step 6: View Results & Download")
#         st.markdown(
#             """
#             - Results include a summary report and a detailed table with individual scores.
#             - Use the "Download Results as CSV" button to save the full report.
#             """
#         )

#         # --- Section: test_config Use Cases ---
#         st.subheader("Leveraging the `test_config` Column for Bank Branch Testing")
#         st.markdown(
#             """
#             The `test_config` column is optional but highly recommended for organizing your tests, especially in a dynamic environment like a bank branch. It allows you to categorize your test cases. Later, you can filter or group your evaluation results based on these configurations to analyze performance for specific areas.

#             Here are some scenarios where `test_config` can be very useful for bank branch testers:

#             * **Product Inquiries**:
#                 * `test_config: SavingsAccount_Features` (Query: "Tell me about the Mighty Savers account.")
#                 * `test_config: Mortgage_Application_Process` (Query: "How do I apply for a home loan?")
#                 * `test_config: CreditCard_Rewards_Sapphire` (Query: "What are the rewards for the Sapphire credit card?")
#             * **Process Guidance**:
#                 * `test_config: FundTransfer_FAST_Limit` (Query: "What's the daily limit for FAST transfers?")
#                 * `test_config: BillPayment_GIRO_Setup` (Query: "How to set up GIRO for my utility bill?")
#                 * `test_config: ChequeBook_Request` (Query: "How can I order a new cheque book?")
#             * **Problem Resolution / Customer Service**:
#                 * `test_config: CardLost_Reporting` (Query: "I lost my debit card, what should I do?")
#                 * `test_config: UnauthorisedTransaction_Dispute` (Query: "How do I dispute a transaction I don't recognize?")
#                 * `test_config: Feedback_ServiceQuality` (Query: "I want to provide feedback about the service at XYZ branch.")
#             * **Branch Information**:
#                 * `test_config: BranchLocator_Nearest_ Woodlands` (Query: "Where is the nearest branch to Woodlands MRT?")
#                 * `test_config: BranchServices_CashDepositMachine` (Query: "Does the Tampines branch have a cash deposit machine?")
#                 * `test_config: BranchHours_Sunday_JurongPoint` (Query: "Is Jurong Point branch open on Sundays?")
#             * **Campaigns/Promotions**:
#                 * `test_config: Promo_NewCustomer_FD` (Query: "What's the current fixed deposit promotion for new customers?")
#                 * `test_config: Campaign_HomeLoan_Cashback_Q2` (Query: "Tell me about the Q2 home loan cashback offer.")

#             By using `test_config` effectively, you can:
#             - Quickly identify if the LLM performs poorly for a specific product category (e.g., all `CreditCard` queries).
#             - Track improvements or regressions for a set of processes over time (e.g., `AccountOpening` related queries).
#             - Focus testing efforts on high-priority areas.
#             """
#         )


#         # --- Section: CLI Workflow ---
#         st.markdown("---")
#         st.subheader("How to Use: Command Line Interface (CLI)")
#         st.markdown(
#             """
#             For automated batch processing:
#             """
#         )
#         st.markdown("##### Part 1: Fetching Live Bot Responses via CLI")
#         st.markdown(
#             """
#             1.  **Prepare Input CSV**: Create a CSV (e.g., `input_queries.csv`) with a `query` column, and optionally `reference_answer`, `required_facts`, etc.
#             2.  **API Token**: **Crucially, update the `DEFAULT_API_HEADERS` in `llm_eval_package/data/rag_input_processor.py` with a valid Bearer token**, or use the `--api_token` argument.
#             3.  **Run Command**:
#                 ```bash
#                 python main.py fetch-responses \\
#                     --input_queries_csv path/to/your/input_queries.csv \\
#                     --output_eval_data_csv path/to/output_with_responses.csv \\
#                     --domain_key "SG Branch" \\
#                     # Optional: --api_token "your_bearer_token_here"
#                 ```
#                 This populates the `llm_output` column in `output_with_responses.csv`.
#             """
#         )
#         st.markdown("##### Part 2: Evaluating Responses via CLI")
#         st.markdown(
#             """
#             1.  **Input Data**: Use the CSV file from Part 1 (e.g., `output_with_responses.csv`).
#             2.  **Run Command**:
#                 ```bash
#                 python main.py evaluate \\
#                     --input_file path/to/output_with_responses.csv \\
#                     --output_file path/to/evaluation_results.csv \\
#                     --metrics "Semantic Similarity,Fact Adherence,Safety" \\
#                     # The --task_type argument is available but defaults to 'rag_faq' if omitted.
#                     # Optional: --custom_thresholds "Semantic Similarity=0.8,Fact Adherence=1.0"
#                     # Optional: --sensitive_keywords "confidential_info,restricted_term"
#                 ```
#             This evaluates `llm_output` and saves results to `evaluation_results.csv`.
#             """
#         )
#         st.markdown("---")
#         st.markdown("Enjoy evaluating your LLMs!")




# llm_eval_package/ui/tutorial_view.py
import streamlit as st
import pandas as pd

class TutorialView:
    def __init__(self):
        pass

    def render_tutorial(self):
        st.markdown("<h2 style='text-align: center; color: #4CAF50;'>🚀 LLM Evaluation Guide 🚀</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Your one-stop guide to evaluating LLMs effectively!</p>", unsafe_allow_html=True)
        st.markdown("---")

        st.info("🎯 **Goal**: This tool helps assess your LLM's performance. You can use pre-existing LLM responses or fetch live ones from your RAG chatbot for evaluation against various quality metrics.")

        # Section 1: Input Data
        with st.expander("💾 Step 1: Preparing Your Input Data", expanded=True):
            st.markdown(
                """
                Your foundation for evaluation is a **CSV or JSON file**. Here's what it needs:
                """
            )
            # Using columns for better layout of field definitions
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### **Required Fields** ✨")
                st.markdown("- **`query`**: The question/prompt for the LLM.")
                st.markdown("- **`reference_answer`**: The ideal/correct answer.")
                st.markdown("- **`llm_output`**: The LLM's actual response. *(Can be empty if using 'Fetch Bot Responses' feature)*")

            with col2:
                st.markdown("##### *Optional Fields* (Recommended) 📝")
                st.markdown("- **`required_facts`**: Critical facts the LLM *must* mention. Separate with semicolons (`;`). *Used by the 'Fact Adherence' metric.* (e.g., `Interest is 3.5%; Min. deposit $1000`)")
                st.markdown("- **`test_description`**: What this test case aims to verify.")
                st.markdown("- **`test_config`**: Category for grouping (e.g., `SavingsAccount`, `HR_Policy_Leave`).")

            st.markdown("---")
            st.markdown("##### 🏦 Banking Scenario Examples:")
            # Tabs for different banking examples
            tab_branch, tab_finance, tab_hr = st.tabs(["🏢 Branch Ops", "💰 Finance/Investments", "👥 HR Policy"])

            with tab_branch:
                st.caption("Example: Bank Branch Operations")
                branch_data = {
                    'query': ["Orchard branch Saturday hours?", "How to open a current account?"],
                    'llm_output': ["Open 9 AM - 1 PM Saturdays.", "Provide NRIC, address proof, $500 deposit. Apply online or at branch."],
                    'reference_answer': ["Orchard branch is open 9:00 AM - 1:00 PM on Saturdays.", "Provide NRIC/passport, proof of address, min. $500 deposit. Apply online or visit."],
                    'required_facts': ["9 AM to 1 PM;Saturdays", "NRIC;proof of address;$500 deposit"],
                    'test_description': ["Check Orchard Sat hours", "Verify current account opening steps"],
                    'test_config': ["Branch_Hours_Orchard", "AccountOpening_Current"]
                }
                st.dataframe(pd.DataFrame(branch_data), use_container_width=True)

            with tab_finance:
                st.caption("Example: Finance/Investment Products")
                finance_data = {
                    'query': ["12-month FD rate?", "Risks of unit trusts?"],
                    'llm_output': ["12-month FD is 3.5% p.a. for >$10k.", "Unit trusts subject to market fluctuations, no guaranteed returns, potential principal loss."],
                    'reference_answer': ["12-month FD promotional rate is 3.50% p.a. for $10k+ deposits.", "Unit trusts involve market risk (value can fall), past performance not indicative of future, potential principal loss. Read prospectus."],
                    'required_facts': ["3.5% p.a.;12-month", "market fluctuations;no guarantee;lose principal"],
                    'test_description': ["Verify 12m FD rate", "Explain unit trust risks"],
                    'test_config': ["FixedDeposit_Rates_12M", "UnitTrust_RiskDisclosure"]
                }
                st.dataframe(pd.DataFrame(finance_data), use_container_width=True)

            with tab_hr:
                st.caption("Example: HR Policy (Internal)")
                hr_data = {
                    'query': ["Paternity leave policy?", "Annual medical leave entitlement?"],
                    'llm_output': ["Eligible males get 2 weeks paternity leave.", "14 days outpatient, 60 days hospitalization leave annually."],
                    'reference_answer': ["Eligible male employees get 2 weeks GPPL + 2 weeks shared parental leave (subject to criteria).", "14 days paid outpatient sick leave, up to 60 days paid hospitalisation leave (inclusive of outpatient)."],
                    'required_facts': ["2 weeks paternity leave", "14 days outpatient;60 days hospitalization"],
                    'test_description': ["Verify paternity leave", "Verify medical leave days"],
                    'test_config': ["HR_Leave_Paternity", "HR_Leave_Medical"]
                }
                st.dataframe(pd.DataFrame(hr_data), use_container_width=True)

        # Section 2: GUI Workflow
        with st.expander("🖥️ Using the Dashboard (GUI Workflow)", expanded=False):
            st.markdown(
                """
                **1. Upload Data**: Use the sidebar "Upload Dataset" button.
                """
            )
            st.image("https://storage.googleapis.com/gemini-prod/images/2024/05/29/18_00_00_000000_BQAE.png", caption="Sidebar: Upload & Bot Config", width=300) # Placeholder - replace with actual image if possible

            st.markdown(
                """
                **2. Configure Bot (If Fetching Live Responses)**:
                   - **Bot Domain**: Select in sidebar (e.g., 'SG Branch').
                   - **API Token**: Optionally enter in the main panel (field appears after data upload).
                """
            )
            st.markdown(
                """
                **3. Fetch Live Responses (Optional)**:
                   - Click "🔗 **Fetch Bot Responses & Update Data**" in the main panel.
                   - This populates/updates the `llm_output` column in your data table.
                """
            )
            st.markdown(
                """
                **4. Configure Evaluation**:
                   - **Metrics**: Select in sidebar (e.g., Semantic Similarity, Fact Adherence). *(Developer Mode may show more options)*
                   - **Overall Pass/Fail Logic**: Choose how a test case passes based on multiple metrics (e.g., "All metrics must pass").
                   - **Thresholds**: Set pass/fail scores for each metric.
                   - **Safety Keywords**: If using "Safety" metric, define sensitive terms. *(Developer Mode)*
                """
            )
            st.image("https://storage.googleapis.com/gemini-prod/images/2024/05/29/18_05_00_000000_BQAE.png", caption="Main Panel: Fetch & Evaluate Buttons", width=400) # Placeholder

            st.markdown(
                """
                **5. Run Evaluation**: Click "🚀 **Run Evaluation**".
                **6. View Results**: Analyze summaries, detailed tables, and download reports.
                """
            )

        # Section 3: Mapping Business Needs to Metrics
        with st.expander("💡 Mapping Bank UAT Goals to Metrics", expanded=False):
            st.markdown(
                """
                Connect your testing goals to the tool's metrics:

                - **"Is the bot's answer relevant and correct in meaning?"**
                  ➡️ Use `Semantic Similarity`.
                  *Example*: Bot gives PayNow info for a FAST transfer query. Low similarity expected.

                - **"Did the bot provide all critical pieces of information?"**
                  ➡️ Use `Fact Adherence` (for specific, must-have facts from your `required_facts` column).
                  ➡️ Use `Completeness` (for general coverage against the `reference_answer`).
                  *Example*: For a loan query, `Fact Adherence` checks if "Interest 3.5%" and "Min. loan $10k" are stated.

                - **"Is the answer concise, no fluff?"**
                  ➡️ Use `Conciseness`.
                  *Example*: Bot gives a lengthy intro before answering a simple phone number query. Lower score.

                - **"Is the answer factually accurate against our gold standard?"**
                  ➡️ Use `Trust & Factuality` (compares to `reference_answer`).
                  ➡️ Reinforce with `Fact Adherence` for key data points.

                - **"Does the bot avoid restricted terms or harmful language?"**
                  ➡️ Use `Safety` (define keywords like "internal_code_xyz", "competitor_promo").
                """
            )

        # Section 4: Using `test_config`
        with st.expander("🗂️ Power of `test_config` for Bank Testers", expanded=False):
            st.markdown(
                """
                The `test_config` column helps you categorize tests. This is invaluable for analyzing results for specific banking areas.
                After evaluation, the "Results" page will show a "Summary by Test Configuration" section.

                **Bank Branch Examples for `test_config`**:
                - `AccountOpening_Savings`: Queries about opening savings accounts.
                - `CardServices_LostCard`: Procedures for lost/stolen cards.
                - `BranchInfo_Jurong_Hours`: Specific branch operating hours.
                - `LoanProduct_HomeLoan_Rates`: Inquiries about home loan interest rates.
                - `DigitalBanking_PayNow_Setup`: Questions on setting up PayNow.
                - `CustomerFeedback_Complaints`: How the bot handles complaint-like queries.

                This allows you to see, for example, if the bot excels at `BranchInfo` but struggles with `LoanProduct` details.
                """
            )


        # Section 5: CLI Workflow
        with st.expander("⌨️ Using the Command Line (CLI)", expanded=False):
            st.markdown(
                """
                For automation or batch processing:
                **Important**: First, ensure a valid API token is in `llm_eval_package/data/rag_input_processor.py` or use the `--api_token` argument.
                """
            )
            st.markdown("##### **Part 1: Fetch Live Responses**")
            st.code(
                """
python main.py fetch-responses \\
    --input_queries_csv data/my_bank_queries.csv \\
    --output_eval_data_csv data/bank_queries_with_responses.csv \\
    --domain_key "SG Branch" \\
    # --api_token "YOUR_TOKEN_IF_NOT_IN_SCRIPT"
                """, language="bash"
            )
            st.caption("This adds `llm_output` to your query file.")

            st.markdown("##### **Part 2: Evaluate Responses**")
            st.code(
                """
python main.py evaluate \\
    --input_file data/bank_queries_with_responses.csv \\
    --output_file results/bank_evaluation_report.csv \\
    --metrics "Semantic Similarity,Fact Adherence,Safety" \\
    # --custom_thresholds "Fact Adherence=1.0,Safety=1.0" \\
    # --sensitive_keywords "internal_use_only,competitor_xyz"
                """, language="bash"
            )
            st.caption("This generates your evaluation report.")

        st.markdown("---")
        st.success("You're all set! Happy Evaluating! 🎉")