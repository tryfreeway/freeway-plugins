import freeway
import re

def before_paste():
    # Load settings
    enabled = freeway.get_setting("enabled")
    if enabled is False:
        return

    censor_char = freeway.get_setting("censor_char") or "*"
    custom_words_str = freeway.get_setting("custom_words") or ""
    block_sentence = freeway.get_setting("block_sentence") or False

    text = freeway.get_text()
    if not text:
        return

    try:
        from profanity_check import predict
        from better_profanity import profanity
        
        # Load custom words if any into better-profanity
        if custom_words_str:
            custom_words = [word.strip() for word in custom_words_str.split(",") if word.strip()]
            profanity.add_censor_words(custom_words)

        if block_sentence:
            # Split by sentences (simple regex)
            sentences = re.split(r'(?<=[.!?])\s+', text)
            filtered_sentences = []
            
            # Predict profanity for each sentence
            # predict() takes a list of strings
            sent_preds = predict(sentences)
            
            for i, sentence in enumerate(sentences):
                # Check ML prediction OR better-profanity (for custom words)
                if sent_preds[i] == 1 or profanity.contains_profanity(sentence):
                    freeway.log(f"Profanity detected in sentence: '{sentence}' - Blocking.")
                    continue
                filtered_sentences.append(sentence)
            
            processed_text = " ".join(filtered_sentences)
        else:
            # Word-level censoring using ML + Blacklist
            # First, handle the ML part for individual words
            words = re.findall(r'\w+|[^\w\s]', text, re.UNICODE)
            word_preds = predict(words)
            
            censored_words = []
            for i, word in enumerate(words):
                # If ML predicts profanity OR better-profanity catches it
                if word_preds[i] == 1 or profanity.contains_profanity(word):
                    censored_words.append(censor_char * len(word))
                else:
                    censored_words.append(word)
            
            # Reconstruct text carefully to preserve spacing (approximate)
            # Re-joining using original text spacing would be better but complex.
            # For now, we'll do a simple join or reconstruct based on original text.
            
            # Alternative: check chunks or use better_profanity's censor if possible,
            # but better_profanity only uses its internal list.
            
            # Let's use a more robust reconstruction:
            processed_text = ""
            last_end = 0
            for i, match in enumerate(re.finditer(r'\w+|[^\w\s]', text, re.UNICODE)):
                start, end = match.span()
                # Add whitespace between matches
                processed_text += text[last_end:start]
                
                word = match.group()
                if word_preds[i] == 1 or profanity.contains_profanity(word):
                    processed_text += (censor_char * len(word))
                else:
                    processed_text += word
                last_end = end
            processed_text += text[last_end:]

        if processed_text != text:
            freeway.set_text(processed_text)
            freeway.set_status_text("✨ ML Censored")
            
    except ImportError as e:
        freeway.log(f"Error: Required library not found ({str(e)}). Please wait for Freeway to install dependencies.")
        freeway.set_status_text("❌ Filter Error")
    except Exception as e:
        freeway.log(f"An error occurred in ML Profanity Censor: {str(e)}")
