import json
import re
import urllib.error
import urllib.parse
import urllib.request

import freeway


DEFAULT_PROMPT = (
    "Convert the following text to well-formatted Markdown syntax. "
    "Output only the Markdown, nothing else.\n\nText:\n{text}"
)


def _strip_trigger_prefix(text: str, pattern: str) -> str:
    """Strip the trigger pattern from the start of text if present."""
    if not text or not pattern:
        return text

    # Normalize for comparison: remove punctuation and lowercase
    text_normalized = re.sub(r"[^\w\s]", "", text).strip().lower()
    pattern_normalized = re.sub(r"[^\w\s]", "", pattern).strip().lower()

    if text_normalized.startswith(pattern_normalized):
        # Find where the pattern ends in the original text
        # Build regex to match pattern words with optional punctuation between them
        tokens = pattern_normalized.split()
        if not tokens:
            return text
        regex_pattern = r"^\s*" + r"[^\w]*".join(re.escape(t) for t in tokens) + r"[^\w]*"
        match = re.match(regex_pattern, text, re.IGNORECASE)
        if match:
            return text[match.end():].lstrip()

    return text


def _call_openai(api_key: str, model: str, prompt: str, timeout: int = 30) -> str:
    """Call OpenAI Chat Completions API."""
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
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

    # Get trigger pattern and strip it from text if present
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

    prompt = prompt_template.replace("{text}", payload)

    freeway.set_status_text("Converting to Markdown…")
    freeway.set_indicator_color("#10A37F")  # OpenAI green

    try:
        response_text = _call_openai(api_key, model, prompt)
        freeway.set_text(response_text)
        freeway.log(f"Converted to Markdown with model {model}.")
        freeway.set_status_text("✓ Converted to Markdown")
    except Exception as exc:
        freeway.log(f"OpenAI error: {exc}")
        freeway.set_status_text(f"Error: {str(exc)[:60]}")
