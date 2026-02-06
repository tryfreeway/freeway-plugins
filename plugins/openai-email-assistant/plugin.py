import json
import re
import urllib.error
import urllib.request

import freeway


SYSTEM_PROMPT = "You are an assistant that writes email drafts."


def _strip_trigger_prefix(text: str, pattern: str) -> str:
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


def _call_openai(api_key: str, model: str, prompt: str, timeout: int = 30) -> str:
    url = "https://api.openai.com/v1/responses"
    payload = {
        "model": model,
        "instructions": SYSTEM_PROMPT,
        "input": prompt,
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

    output = response_data.get("output") or []
    for item in output:
        if item.get("type") == "message":
            content = item.get("content") or []
            for c in content:
                if c.get("type") == "output_text":
                    return c.get("text", "").strip()

    raise RuntimeError("No response returned from OpenAI.")


def _parse_subject_body(text: str):
    if not text:
        return None, None

    subject = None
    body = None

    lines = [line.rstrip() for line in text.splitlines()]
    for i, line in enumerate(lines):
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            remaining = lines[i + 1 :]
            if remaining:
                if remaining[0].lower().startswith("body:"):
                    remaining = remaining[1:]
                body = "\n".join(remaining).strip()
            break

    if subject is None and lines and lines[0].lower().startswith("body:"):
        body = "\n".join(lines[1:]).strip()

    return subject, body


def _sentence_case(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    cased = []
    for sentence in sentences:
        s = sentence.strip()
        if not s:
            continue
        cased.append(s[0].upper() + s[1:])
    return " ".join(cased)


def _fallback_subject(text: str) -> str:
    words = re.findall(r"\w+", text)
    if not words:
        return "Draft email"
    return " ".join(words[:7])


def _extract_recipient_and_topic(text: str):
    cleaned = text.strip()
    recipient = None
    topic = None

    match = re.match(r"^(to\s+[^,]+)(?:,|\s+)(.*)$", cleaned, flags=re.IGNORECASE)
    if match:
        recipient = match.group(1).strip()[3:].strip()
        cleaned = match.group(2).strip()

    topic_match = re.match(r"^(about|regarding|re:?)\s+(.*)$", cleaned, flags=re.IGNORECASE)
    if topic_match:
        topic = topic_match.group(2).strip()
        cleaned = topic

    return recipient, topic, cleaned


def _fallback_body(text: str, recipient: str = None) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    body = _sentence_case(cleaned)
    if recipient:
        return f"Hi {recipient},\n\n{body}"
    return body


def before_paste():
    api_key = freeway.get_setting("api_key")
    model = freeway.get_setting("model") or "gpt-5-nano"
    tone = freeway.get_setting("tone") or "professional"

    original_text = freeway.get_text()
    if not original_text or not original_text.strip():
        freeway.log("No text to process.")
        return

    trigger = freeway.get_trigger()
    trigger_pattern = trigger.get("pattern") if trigger else None
    payload = _strip_trigger_prefix(original_text, trigger_pattern or "").strip()

    if not payload:
        freeway.log("No payload after trigger; skipping.")
        return

    prompt = (
        "Convert the following into a complete email with subject and body.\n"
        f"Tone: {tone}\n"
        "Output format:\n"
        "Subject: <one line>\n"
        "Body:\n"
        "<multi-line email body>\n\n"
        f"Input:\n\"{payload}\""
    )

    subject = None
    body = None

    if api_key:
        freeway.set_status_text("Drafting email…")
        freeway.set_indicator_color("#10A37F")
        try:
            response_text = _call_openai(api_key, model, prompt)
            parsed_subject, parsed_body = _parse_subject_body(response_text)
            if parsed_subject:
                subject = parsed_subject
            if parsed_body:
                body = parsed_body
            if not body:
                body = response_text
            freeway.log(f"Draft generated with {model}.")
        except Exception as exc:
            freeway.log(f"OpenAI error: {exc}")
            subject = None
            body = None
    else:
        freeway.log("OpenAI API key is missing; using fallback.")

    if not body:
        recipient, topic, remaining = _extract_recipient_and_topic(payload)
        subject = subject or (topic if topic else _fallback_subject(remaining))
        body = _fallback_body(remaining or payload, recipient=recipient)
    if not subject:
        subject = _fallback_subject(body)

    formatted = f"Subject: {subject}\n\nBody:\n{body}"
    freeway.set_text(formatted)
    freeway.set_status_text("✓ Email draft ready")
