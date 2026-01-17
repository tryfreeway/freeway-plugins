import json
import re
import urllib.error
import urllib.request

import freeway


DEFAULT_PROMPT = "Translate the following text to {language}. Output only the translation, nothing else."


def _strip_trigger_prefix(text: str, pattern: str) -> str:
    """Strip the trigger pattern from the start of text if present."""
    if not text or not pattern:
        return text

    text_normalized = re.sub(r"[^\w\s]", "", text).strip().lower()
    pattern_normalized = re.sub(r"[^\w\s]", "", pattern).strip().lower()

    if text_normalized.startswith(pattern_normalized):
        tokens = pattern_normalized.split()
        if not tokens:
            return text
        regex_pattern = r"^\s*" + r"[^\w]*".join(re.escape(t) for t in tokens) + r"[^\w]*"
        match = re.match(regex_pattern, text, re.IGNORECASE)
        if match:
            return text[match.end():].lstrip()

    return text


def _parse_language_and_text(text: str) -> tuple[str, str]:
    """
    Parse the language and text to translate from the input.
    Example: "Spanish Hello world" -> ("Spanish", "Hello world")
    """
    text = text.strip()
    if not text:
        return "", ""

    # First word is the language, rest is text to translate
    parts = text.split(None, 1)
    if len(parts) == 2:
        return parts[0].capitalize(), parts[1]
    elif len(parts) == 1:
        return parts[0].capitalize(), ""

    return "", ""


def _call_openai(api_key: str, model: str, system_prompt: str, user_content: str, timeout: int = 30) -> str:
    """Call OpenAI Chat Completions API."""
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.3,
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_detail = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code}: {error_detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}") from e

    choices = response_data.get("choices") or []
    if choices:
        message = choices[0].get("message", {})
        content = message.get("content")
        if content:
            return content.strip()
    raise RuntimeError("No response returned from OpenAI.")


def before_paste():
    api_key = freeway.get_setting("api_key")
    if not api_key:
        freeway.log("OpenAI API key is missing; skipping.")
        return

    model = freeway.get_setting("model") or "gpt-5-mini"
    prompt_template = freeway.get_setting("prompt") or DEFAULT_PROMPT

    original_text = freeway.get_text()
    if not original_text:
        freeway.log("No text to process.")
        return

    # Get trigger pattern and strip it from text
    trigger = freeway.get_trigger()
    trigger_pattern = trigger.get("pattern") if trigger else None

    if trigger_pattern:
        payload = _strip_trigger_prefix(original_text, trigger_pattern)
    else:
        payload = original_text

    payload = payload.strip()
    if not payload:
        freeway.log("No payload after trigger; skipping.")
        return

    # Parse language and text to translate
    language, text_to_translate = _parse_language_and_text(payload)

    if not language:
        freeway.log("Could not determine target language.")
        return

    if not text_to_translate:
        freeway.log("No text to translate.")
        return

    # Build the prompt
    system_prompt = prompt_template.replace("{language}", language)

    freeway.set_status_text(f"Translating to {language}…")
    freeway.set_indicator_color("#10A37F")  # OpenAI green

    try:
        response_text = _call_openai(api_key, model, system_prompt, text_to_translate)
        freeway.set_text(response_text)
        freeway.log(f"Translated to {language} with model {model}.")
        freeway.set_status_text(f"✓ Translated to {language}")
    except Exception as exc:
        freeway.log(f"OpenAI error: {exc}")
        freeway.set_status_text(f"Error: {str(exc)[:60]}")
