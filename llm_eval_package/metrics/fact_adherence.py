# llm_eval_package/metrics/fact_adherence.py
from llm_eval_package.metrics.base import BaseMetric
import numpy as np # For np.nan
import warnings
import pandas as pd # For pd.isna

try:
    import nltk
    from nltk.stem import WordNetLemmatizer
    from nltk.tokenize import word_tokenize
    _NLTK_AVAILABLE = True
    try: # Check for necessary NLTK data
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/wordnet')
        nltk.data.find('corpora/omw-1.4')
    except LookupError: # More specific exception for missing data
        warnings.warn(
            "NLTK data (punkt, wordnet, omw-1.4) not found or NLTK itself is not fully configured. "
            "Fact Adherence will fall back to simple substring matching. "
            "To enable advanced matching, run in Python: \n"
            "import nltk\nnltk.download('punkt')\nnltk.download('wordnet')\nnltk.download('omw-1.4')"
        )
        _NLTK_AVAILABLE = False # Treat as unavailable if data is missing
except ImportError:
    _NLTK_AVAILABLE = False
    warnings.warn("NLTK library not found. FactAdherenceMetric will fall back to simple substring matching.")


class FactAdherenceMetric(BaseMetric):
    def __init__(self):
        super().__init__("Fact Adherence")
        self.nltk_ready = False
        if _NLTK_AVAILABLE:
            try:
                self.lemmatizer = WordNetLemmatizer()
                word_tokenize("test") # Test if punkt is available and working
                self.lemmatizer.lemmatize("test") # Test if wordnet is available
                self.nltk_ready = True
                print("DEBUG: NLTK Lemmatization is READY for Fact Adherence.")
            except Exception as e:
                warnings.warn(f"NLTK components (punkt/wordnet) for FactAdherenceMetric failed to initialize: {e}. Falling back to simple substring matching.")
        else:
             print("DEBUG: NLTK Lemmatization is NOT READY for Fact Adherence, falling back.")


    def _lemmatize_text(self, text):
        if not self.nltk_ready or not text or not isinstance(text, str):
             # Fallback for non-string, empty text, or if NLTK not ready
            return str(text).lower().split() if text else []
        
        tokens = word_tokenize(text.lower())
        lemmatized_tokens = [self.lemmatizer.lemmatize(token) for token in tokens]
        return lemmatized_tokens

    def _is_sublist(self, sublist, mainlist):
        if not sublist: return True 
        if not mainlist: return False
        len_sub = len(sublist)
        for i in range(len(mainlist) - len_sub + 1):
            if mainlist[i:i+len_sub] == sublist:
                return True
        return False

    def compute(self, llm_output: str, reference_answer: str = None, query: str = None, required_facts: str = None, **kwargs) -> float:
        if not required_facts or not str(required_facts).strip():
            return np.nan 

        facts_list_phrases = [fact.strip() for fact in str(required_facts).split(';') if fact.strip()]
        if not facts_list_phrases:
            return np.nan

        if not llm_output or not llm_output.strip():
            return 0.0 

        found_count = 0

        if self.nltk_ready:
            # Lemmatize the entire LLM output once and create a set of its words for efficient lookup
            lemmatized_llm_output_words = set(self._lemmatize_text(llm_output))
            
            for fact_phrase in facts_list_phrases:
                if not fact_phrase: continue # Skip empty fact phrases after split
                
                lemmatized_fact_phrase_words = self._lemmatize_text(fact_phrase)
                if not lemmatized_fact_phrase_words: continue # Skip if fact phrase becomes empty after lemmatization

                # Check if all lemmatized words from the current fact phrase are present in the LLM output
                # This is order-independent for words within the fact phrase.
                all_fact_words_found = True
                for fact_word in lemmatized_fact_phrase_words:
                    if fact_word not in lemmatized_llm_output_words:
                        all_fact_words_found = False
                        break # No need to check other words for this fact phrase
                
                if all_fact_words_found:
                    found_count += 1
        else: 
            # Fallback: Simple case-insensitive substring check for the entire fact phrase
            llm_output_lower = llm_output.lower()
            for fact_phrase in facts_list_phrases:
                if fact_phrase.lower() in llm_output_lower:
                    found_count += 1
        
        return found_count / len(facts_list_phrases)
    # def compute(self, llm_output: str, reference_answer: str = None, query: str = None, required_facts: str = None, **kwargs) -> float:
        
        
        
    #     if not required_facts or not str(required_facts).strip(): # Check if it's NaN, None, or empty string
    #         return np.nan 

    #     facts_list = [fact.strip() for fact in str(required_facts).split(';') if fact.strip()]
    #     if not facts_list: 
    #         return np.nan

    #     if not llm_output or not llm_output.strip(): 
    #         return 0.0 

    #     found_count = 0
    #     if self.nltk_ready:
    #         lemmatized_llm_tokens = self._lemmatize_text(llm_output)
                        
    #         print(f"DEBUG: NLTK Lemmatized LLM Tokens: {lemmatized_llm_tokens}")

    #         for fact_item in facts_list:
    #             lemmatized_fact_tokens = self._lemmatize_text(fact_item)
    #             print(f"DEBUG: NLTK Lemmatized FACT Tokens: {lemmatized_fact_tokens}")

    #             if not lemmatized_fact_tokens: continue
    #             if self._is_sublist(lemmatized_fact_tokens, lemmatized_llm_tokens):
    #                 found_count += 1
    #     else: 
    #         llm_output_lower = llm_output.lower()
    #         for fact_item in facts_list:
    #             if fact_item.lower() in llm_output_lower:
    #                 found_count += 1
        
    #     return found_count / len(facts_list)

    def get_score_description(self, score: float) -> str:
        if pd.isna(score): # Use pandas isna for checking np.nan
            return "Not Applicable: No valid required facts were provided for this test case."
        # ... (rest of descriptions for 1.0, 0.75, etc. as before) ...
        if score == 1.0: return "Excellent: All required facts were found."
        elif score >= 0.75: return "Good: Most required facts were found."
        elif score >= 0.5: return "Moderate: Some required facts found, several missing."
        elif score > 0.0: return "Low: Very few required facts were found."
        return "Poor: None of the required facts were found."
    



# # llm_eval_package/metrics/fact_adherence.py
# from llm_eval_package.metrics.base import BaseMetric
# import numpy as np # For np.nan
# import warnings

# try:
#     import nltk
#     from nltk.stem import WordNetLemmatizer
#     from nltk.tokenize import word_tokenize
#     # Attempt to download necessary NLTK data if not found, with a flag
#     _NLTK_AVAILABLE = True
#     try:
#         nltk.data.find('tokenizers/punkt')
#         nltk.data.find('corpora/wordnet')
#         nltk.data.find('corpora/omw-1.4') # Open Multilingual WordNet, often needed with WordNet
#     except nltk.downloader.DownloadError:
#         # This part is tricky in a non-interactive setup.
#         # For now, we assume if the import works, the data *should* be there
#         # or the user needs to download it manually as per NLTK's instructions.
#         # A more robust solution might involve trying to download within the code,
#         # but that can have side effects or require internet.
#         # warnings.warn("NLTK data (punkt, wordnet, omw-1.4) not found. Fact Adherence might be less accurate or fall back. Run: nltk.download('punkt'); nltk.download('wordnet'); nltk.download('omw-1.4')")
#         pass # Let it try, will fail gracefully in compute if tokenization/lemmatization fails
# except ImportError:
#     _NLTK_AVAILABLE = False
#     warnings.warn("NLTK library not found. FactAdherenceMetric will fall back to simple substring matching and may be less accurate for morphological variations.")




# class FactAdherenceMetric(BaseMetric):
#     """
#     A metric to evaluate if a list of required facts are present in the LLM output.
#     Facts in the 'required_facts' input should be separated by semicolons (;).
#     Uses lemmatization for more robust matching if NLTK is available.
#     """

#     def __init__(self):
#         super().__init__("Fact Adherence")
#         if _NLTK_AVAILABLE:
#             print("NLTK AVAILABLE")
#             try:
#                 self.lemmatizer = WordNetLemmatizer()
#                 # Test tokenization to ensure 'punkt' is truly available
#                 word_tokenize("test") 
                
#                 self.nltk_ready = True
#             except Exception as e:
#                 warnings.warn(f"NLTK components (punkt/wordnet) for FactAdherenceMetric failed to initialize: {e}. Falling back to simple substring matching.")
#                 self.nltk_ready = False

#         else:
#             self.nltk_ready = False
#             print("nltk_ready NOT READY CUZ NOT AVAILABLE")

#     def _lemmatize_text(self, text):
#         if not self.nltk_ready or not text:
#             return text.lower().split() # Fallback or simple tokenization if no lemmatization
        
#         tokens = word_tokenize(text.lower())
#         # Lemmatize each word. Try to get part-of-speech for better lemmatization if possible,
#         # but for simplicity, default to noun (WordNetLemmatizer's default if no pos).
#         # A more advanced version could use nltk.pos_tag.
#         lemmatized_tokens = [self.lemmatizer.lemmatize(token) for token in tokens]
#         return lemmatized_tokens

#     def _is_sublist(self, sublist, mainlist):
#         """Checks if sublist is an ordered sublist of mainlist."""
#         if not sublist: return True # Empty sublist is always found
#         if not mainlist: return False # Cannot find in empty list
        
#         len_sub = len(sublist)
#         for i in range(len(mainlist) - len_sub + 1):
#             if mainlist[i:i+len_sub] == sublist:
#                 return True
#         return False

#     def compute(self, llm_output: str, reference_answer: str = None, query: str = None, required_facts: str = None, **kwargs) -> float:
#         if not required_facts or not required_facts.strip():
#             return np.nan # Return NaN if no facts are required (N.A. score)

#         facts_list = [fact.strip() for fact in required_facts.split(';') if fact.strip()]

#         print(f"Length of facts list: {len(facts_list)}")

#         if not facts_list: # After stripping, if no valid facts remain
#             return np.nan # Return NaN if no valid facts were actually provided

#         if not llm_output or not llm_output.strip(): # If LLM output is empty, it cannot contain any facts
#             return 0.0 

#         found_count = 0

#         if self.nltk_ready:
#             # print("DEBUG: Using NLTK Lemmatization for Fact Adherence") # For debugging
#             lemmatized_llm_tokens = self._lemmatize_text(llm_output)
            
#             print(f"LEMMATIZED LLM TOKENS:{lemmatized_llm_tokens}")
#             for fact_item in facts_list:
#                 lemmatized_fact_tokens = self._lemmatize_text(fact_item)
#                 print(f"LEMMATIZED FACT TOKENS:{lemmatized_fact_tokens}")
#                 if not lemmatized_fact_tokens: continue # Skip empty facts after processing
#                 if self._is_sublist(lemmatized_fact_tokens, lemmatized_llm_tokens):
#                     found_count += 1

#         else: # Fallback to simple substring checking
#             print("DEBUG: Using simple substring check for Fact Adherence") # For debugging

#             llm_output_lower = llm_output.lower()
#             for fact_item in facts_list:
#                 if fact_item.lower() in llm_output_lower:
#                     found_count += 1
        
#         return found_count / len(facts_list)

#     def get_score_description(self, score: float) -> str:
#         if pd.isna(score): # Handle np.nan score
#             return "Not Applicable: No valid required facts were provided for this test case."
#         if score == 1.0:
#             return "Excellent: All required facts were found in the LLM output."
#         elif score >= 0.75:
#             return "Good: Most of the required facts were found."
#         elif score >= 0.5:
#             return "Moderate: Some required facts were found, but several are missing."
#         elif score > 0.0:
#             return "Low: Very few required facts were found."
#         else: # score == 0.0
#             return "Poor: None of the required facts were found in the LLM output."