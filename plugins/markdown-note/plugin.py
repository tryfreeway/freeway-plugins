import re

import freeway


# Keywords that indicate action items
ACTION_KEYWORDS = [
    "need to", "needs to", "have to", "has to", "must",
    "should", "remember to", "don't forget", "follow up",
    "make sure", "todo", "to do", "action item",
]


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


def _split_into_segments(text: str) -> list:
    """Split text into segments based on common speech patterns."""
    # Split on common conjunctions and punctuation
    separators = r'\band\b|\balso\b|\bthen\b|\bplus\b|,|;|\.'
    segments = re.split(separators, text, flags=re.IGNORECASE)
    # Clean up and filter empty segments
    return [s.strip() for s in segments if s.strip()]


def _extract_title(segments: list) -> str:
    """Extract a title from the first segment."""
    if not segments:
        return "Note"

    first = segments[0]
    # Capitalize first letter of each word for title
    words = first.split()
    if len(words) > 8:
        words = words[:8]  # Limit title length

    title = " ".join(words).title()
    # Remove trailing action words from title
    for keyword in ACTION_KEYWORDS:
        if title.lower().endswith(keyword):
            title = title[:-len(keyword)].strip()

    return title if title else "Note"


def _is_action_item(text: str) -> bool:
    """Check if text contains action item keywords."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in ACTION_KEYWORDS)


def _clean_action_text(text: str) -> str:
    """Clean up action item text for display."""
    result = text
    # Capitalize first letter
    if result:
        result = result[0].upper() + result[1:] if len(result) > 1 else result.upper()
    return result


def _format_as_markdown(text: str) -> str:
    """Convert voice input to structured Markdown note."""
    segments = _split_into_segments(text)

    if not segments:
        return f"# Note\n\n- {text}"

    # Extract title from first meaningful segment
    title = _extract_title(segments)

    # Separate action items from regular points
    bullet_points = []
    action_items = []

    for segment in segments:
        if not segment:
            continue

        if _is_action_item(segment):
            action_items.append(_clean_action_text(segment))
        else:
            # Capitalize first letter
            point = segment[0].upper() + segment[1:] if len(segment) > 1 else segment.upper()
            bullet_points.append(point)

    # Build markdown output
    lines = [f"# {title}", ""]

    # Add bullet points (skip first if it's the same as title)
    for point in bullet_points:
        if point.lower().strip() != title.lower().strip():
            lines.append(f"- {point}")

    # Add action items section if any
    if action_items:
        lines.append("")
        lines.append("## Action Items")
        for action in action_items:
            lines.append(f"- [ ] {action}")

    return "\n".join(lines)


def before_paste():
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
        freeway.log("No content after trigger; skipping.")
        return

    freeway.set_status_text("Creating note...")
    freeway.set_indicator_color("#22C55E")  # Green

    try:
        result = _format_as_markdown(payload)
        freeway.set_text(result)
        freeway.log("Markdown note created locally.")
        freeway.set_status_text("✓ Note created")
    except Exception as exc:
        freeway.log(f"Error: {exc}")
        freeway.set_status_text(f"Error: {str(exc)[:60]}")
