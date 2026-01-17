import json
import re
import subprocess
import time
import urllib.error
import urllib.request

import freeway


DEFAULT_PROMPT = "Translate the following text to {language}. Output only the translation, nothing else."


def _extract_language(text: str) -> str:
    """
    Extract the language from the trigger pattern.
    Pattern: "Translate selection to [language] language"
    """
    # Normalize text for matching
    text_normalized = re.sub(r"[^\w\s]", "", text).strip().lower()

    # Match pattern: translate selection to X language
    match = re.match(r"translate\s+selection\s+to\s+([a-z]{1,15})\s+language", text_normalized)
    if match:
        return match.group(1).capitalize()

    return ""


def _get_clipboard_text() -> str:
    """Get text from clipboard using pbpaste (macOS)."""
    try:
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout
    except Exception:
        return ""


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

    # Extract language from the spoken command
    language = _extract_language(original_text)
    if not language:
        freeway.log("Could not determine target language from command.")
        return

    freeway.set_status_text("Copying selection…")

    # Press Cmd+C to copy selected text
    freeway.press_keys(["Command", "C"])
    time.sleep(0.15)
    freeway.release_keys(["Command", "C"])
    time.sleep(0.1)

    # Get clipboard content
    clipboard_text = _get_clipboard_text()

    if not clipboard_text or not clipboard_text.strip():
        freeway.log("Clipboard is empty; skipping.")
        freeway.set_status_text("No selection to translate")
        return

    clipboard_text = clipboard_text.strip()

    # Build the prompt
    system_prompt = prompt_template.replace("{language}", language)

    freeway.set_status_text(f"Translating to {language}…")
    freeway.set_indicator_color("#10A37F")  # OpenAI green

    try:
        response_text = _call_openai(api_key, model, system_prompt, clipboard_text)
        freeway.set_text(response_text)
        freeway.log(f"Translated selection to {language} with model {model}.")
        freeway.set_status_text(f"✓ Translated to {language}")
    except Exception as exc:
        freeway.log(f"OpenAI error: {exc}")
        freeway.set_status_text(f"Error: {str(exc)[:60]}")
