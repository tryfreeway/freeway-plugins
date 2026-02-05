import json
import urllib.request
import urllib.error
import freeway


SYSTEM_PROMPT = """
You are a professional editor.
Summarize the given text and output ONLY valid Markdown.

Use this format:

# Summary
## Main Topics
## Key Takeaways
## Action Items
"""


def _call_openai(api_key: str, model: str, text: str, timeout: int = 30) -> str:
    url = "https://api.openai.com/v1/responses"

    payload = {
        "model": model,
        "instructions": SYSTEM_PROMPT,
        "input": text,
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

    with urllib.request.urlopen(request, timeout=timeout) as response:
        response_data = json.loads(response.read().decode("utf-8"))

    output = response_data.get("output", [])
    for item in output:
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    return c.get("text", "").strip()

    raise RuntimeError("No text returned from OpenAI")


def before_paste():
    api_key = freeway.get_setting("api_key")
    if not api_key:
        return

    model = freeway.get_setting("model") or "gpt-5-nano"
    text = freeway.get_text()

    if not text or not text.strip():
        return

    freeway.set_status_text("Summarizing…")
    freeway.set_indicator_color("#10A37F")

    try:
        summary = _call_openai(api_key, model, text)
        freeway.set_text(summary)
        freeway.set_status_text("✓ Done")
    except Exception as e:
        freeway.set_status_text("Error")
        freeway.log(str(e))
