import base64
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request

import freeway


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


def _generate_image(api_key: str, model: str, prompt: str, size: str, quality: str, timeout: int = 120) -> bytes:
    """Call OpenAI Images API and return image bytes."""
    url = "https://api.openai.com/v1/images/generations"
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": quality,
        "output_format": "png",
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

    data_list = response_data.get("data") or []
    if not data_list:
        raise RuntimeError("No image data returned from OpenAI.")

    b64_json = data_list[0].get("b64_json")
    if not b64_json:
        raise RuntimeError("No base64 image data in response.")

    return base64.b64decode(b64_json)


def _copy_image_to_clipboard(image_path: str) -> None:
    """Copy image file to clipboard using AppleScript (macOS)."""
    # Use osascript to set clipboard to image
    script = f'set the clipboard to (read (POSIX file "{image_path}") as «class PNGf»)'
    subprocess.run(
        ["osascript", "-e", script],
        check=True,
        capture_output=True,
        timeout=10
    )


def before_paste():
    api_key = freeway.get_setting("api_key")
    if not api_key:
        freeway.log("OpenAI API key is missing; skipping.")
        return

    model = freeway.get_setting("model") or "gpt-image-1.5"
    prompt_prefix = freeway.get_setting("prompt_prefix") or ""
    size = freeway.get_setting("size") or "1024x1024"
    quality = freeway.get_setting("quality") or "medium"

    original_text = freeway.get_text()
    if not original_text:
        freeway.log("No text to process.")
        return

    # Get trigger pattern and strip it from text
    trigger = freeway.get_trigger()
    trigger_pattern = trigger.get("pattern") if trigger else None

    if trigger_pattern:
        image_prompt = _strip_trigger_prefix(original_text, trigger_pattern)
    else:
        image_prompt = original_text

    image_prompt = image_prompt.strip()
    if not image_prompt:
        freeway.log("No image description provided; skipping.")
        return

    # Add prefix if configured
    if prompt_prefix:
        image_prompt = prompt_prefix.strip() + " " + image_prompt

    freeway.set_status_text("Generating image…")
    freeway.set_indicator_color("#10A37F")  # OpenAI green

    try:
        # Generate image
        image_bytes = _generate_image(api_key, model, image_prompt, size, quality)
        freeway.log(f"Image generated with model {model}.")

        # Save to temp file
        temp_dir = freeway.get_temp_dir()
        if temp_dir:
            temp_path = os.path.join(temp_dir, "generated_image.png")
        else:
            # Fallback to system temp
            fd, temp_path = tempfile.mkstemp(suffix=".png")
            os.close(fd)

        with open(temp_path, "wb") as f:
            f.write(image_bytes)

        freeway.log(f"Image saved to {temp_path}")

        # Copy to clipboard
        freeway.set_status_text("Copying to clipboard…")
        _copy_image_to_clipboard(temp_path)

        freeway.log("Image copied to clipboard.")
        freeway.set_status_text("✓ Image copied to clipboard")

        # Cancel to prevent any paste action - image is in clipboard
        freeway.cancel()

    except Exception as exc:
        freeway.log(f"OpenAI error: {exc}")
        freeway.set_status_text(f"Error: {str(exc)[:60]}")
