# llm_eval_package/metrics/fact_adherence.py
from llm_eval_package.metrics.base import BaseMetric
import numpy as np
import warnings
import pandas as pd
import string # For punctuation

try:
    import nltk
    from nltk.stem import WordNetLemmatizer
    from nltk.tokenize import word_tokenize
    from nltk.corpus import wordnet # For POS tag mapping

    _NLTK_AVAILABLE = True
    # Check for necessary NLTK data and offer to download if missing
    # This is a simplified check; a more robust check might try nltk.download()
    # within a try-except block if permissions allow, or guide the user.
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/wordnet')
        nltk.data.find('corpora/omw-1.4')
        nltk.data.find('taggers/averaged_perceptron_tagger') # For nltk.pos_tag
    except LookupError:
        warnings.warn(
            "One or more NLTK data packages (punkt, wordnet, omw-1.4, averaged_perceptron_tagger) "
            "not found. Fact Adherence may fall back to simpler matching or be less accurate.\n"
            "Please run the following in a Python interpreter:\n"
            "import nltk\n"
            "nltk.download('punkt')\n"
            "nltk.download('wordnet')\n"
            "nltk.download('omw-1.4')\n"
            "nltk.download('averaged_perceptron_tagger')"
        )
        _NLTK_AVAILABLE = False # If essential data is missing, treat NLTK as not fully ready

except ImportError:
    _NLTK_AVAILABLE = False
    warnings.warn("NLTK library not found. FactAdherenceMetric will use simple substring matching.")

class FactAdherenceMetric(BaseMetric):
    def __init__(self):
        super().__init__("Fact Adherence")
        self.nltk_ready = False
        if _NLTK_AVAILABLE:
            try:
                self.lemmatizer = WordNetLemmatizer()
                word_tokenize("test") 
                nltk.pos_tag(word_tokenize("test")) 
                self.lemmatizer.lemmatize("tests", pos=wordnet.VERB) 
                self.nltk_ready = True
                print("DEBUG (FactAdherence): NLTK with POS-aware lemmatization is READY.")
            except Exception as e:
                warnings.warn(f"FactAdherenceMetric: NLTK components failed ({e}). Falling back.")
                self.nltk_ready = False
        else:
            print("DEBUG (FactAdherence): NLTK not available, falling back.")

    def _get_wordnet_pos(self, nltk_tag):
        if nltk_tag.startswith('J'): return wordnet.ADJ
        elif nltk_tag.startswith('V'): return wordnet.VERB
        elif nltk_tag.startswith('N'): return wordnet.NOUN
        elif nltk_tag.startswith('R'): return wordnet.ADV
        else: return wordnet.NOUN 

    def _process_text_for_matching(self, text: str):
        """Tokenizes, cleans (keeps alphanumeric, specific symbols like $), and lemmatizes text."""
        if not self.nltk_ready or not text or not isinstance(text, str):
            if not text or not isinstance(text, str): return []
            # Basic fallback: lower, split, remove common punctuation but try to keep $ and numbers
            # This fallback is less precise than NLTK path.
            processed_tokens = []
            # Allow specific symbols like $ and % to be part of tokens if attached to numbers
            # This regex attempts to keep currency/percentages and words.
            raw_tokens = re.findall(r'[\$€£¥]?\d+[.,\d]*%?|\w+', str(text).lower())
            for token in raw_tokens:
                # Remove standalone punctuation that might have been captured if not part of word/currency
                if token in string.punctuation and len(token) == 1: 
                    continue
                processed_tokens.append(token)
            return processed_tokens

        tokens = word_tokenize(text.lower())
        
        # Filter out most punctuation but keep $, %, and numbers as part of tokens if possible
        # and ensure tokens are not just standalone punctuation.
        # This also aims to handle cases like "$500" becoming ['$', '500'] by word_tokenize
        # and then tries to treat them as individual items or re-combine if necessary for facts.
        # For "all words must match", it's better if "$500" is treated as "500" and fact has "500".
        # Or if fact has "$500", it should tokenize to ['$','500'].
        
        # Let's simplify: keep alphanumeric, and specific symbols if they are part of what users might consider a "word" or value.
        # word_tokenize will separate '$' from '500'. We want to keep both if they are in the fact.
        # The previous filter `token.isalnum()` was too aggressive, removing '$'.

        cleaned_tokens = []
        for token in tokens:
            if token in string.punctuation: # Skip common standalone punctuation
                continue
            cleaned_tokens.append(token) 
            # Numbers will be kept as strings here. Lemmatizer doesn't change them.
            # Symbols like '$' will also be kept if word_tokenize treats them as tokens.

        if not cleaned_tokens: return []

        pos_tags = nltk.pos_tag(cleaned_tokens)
        lemmatized_tokens = [self.lemmatizer.lemmatize(token, self._get_wordnet_pos(tag)) for token, tag in pos_tags]
        
        # print(f"    Processed '{text}' -> {lemmatized_tokens}") # Debug individual processing
        return lemmatized_tokens

    def compute(self, llm_output: str, reference_answer: str = None, query: str = None, required_facts: str = None, **kwargs) -> float:
        if pd.isna(required_facts) or not str(required_facts).strip(): return np.nan 
        facts_list_phrases = [fact.strip() for fact in str(required_facts).split(';') if fact.strip()]
        if not facts_list_phrases: return np.nan
        if pd.isna(llm_output) or not str(llm_output).strip(): return 0.0
        
        llm_output_str = str(llm_output)
        found_count = 0

        # print(f"\nDEBUG (FactAdherence): Evaluating LLM Output: '{llm_output_str}'")
        # print(f"DEBUG (FactAdherence): Against Required Facts Input: '{required_facts}'")

        if self.nltk_ready:
            processed_llm_output_words_set = set(self._process_text_for_matching(llm_output_str))
            # print(f"DEBUG (FactAdherence): Processed LLM Output Tokens (Set): {processed_llm_output_words_set}")

            for i, fact_phrase in enumerate(facts_list_phrases):
                if not fact_phrase: continue
                
                processed_fact_phrase_words = self._process_text_for_matching(fact_phrase)
                # print(f"DEBUG (FactAdherence): Fact {i+1} ('{fact_phrase}') -> Processed Fact Tokens: {processed_fact_phrase_words}")
                if not processed_fact_phrase_words: continue

                all_fact_words_found = True
                for fact_word in processed_fact_phrase_words:
                    if fact_word not in processed_llm_output_words_set:
                        all_fact_words_found = False
                        # print(f"  Word '{fact_word}' from Fact {i+1} NOT FOUND.")
                        break 
                if all_fact_words_found:
                    found_count += 1
                    # print(f"  Fact {i+1} - MATCHED.")
                # else:
                    # print(f"  Fact {i+1} - NO MATCH.")
        else: 
            # Fallback: simple case-insensitive substring for WHOLE phrase
            # This fallback is less granular than the NLTK word-by-word check.
            # print("DEBUG (FactAdherence): Using FALLBACK SUBSTRING CHECK.")
            llm_output_lower = llm_output_str.lower()
            for fact_phrase in facts_list_phrases:
                if fact_phrase.lower() in llm_output_lower:
                    found_count += 1
        
        # print(f"DEBUG (FactAdherence): Found {found_count}/{len(facts_list_phrases)} facts.")
        return found_count / len(facts_list_phrases)
