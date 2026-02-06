import json
import re
import urllib.error
import urllib.request

import freeway


DEFAULT_PROMPT_TEMPLATE = """You are a DevOps expert. Generate complete, production-ready DevOps infrastructure files for the following tech stack: {tech_stack}

Generate the following files with proper formatting, comments, and best practices:

1. **Dockerfile** - Optimized, multi-stage build if applicable
2. **docker-compose.yml** - Complete service orchestration with all dependencies
3. **.github/workflows/ci.yml** - GitHub Actions CI/CD pipeline
4. **azure-pipelines.yml** - Azure DevOps CI/CD pipeline
5. **nginx.conf** - Reverse proxy configuration for production
6. **deploy.sh** - Production deployment script
7. **logging.conf** or appropriate logging configuration

Format the output exactly as follows (use === headers for each file):

=== Dockerfile ===
[complete Dockerfile content with comments]

=== docker-compose.yml ===
[complete docker-compose.yml content]

=== .github/workflows/ci.yml ===
[complete GitHub Actions workflow]

=== azure-pipelines.yml ===
[complete Azure DevOps pipeline]

=== nginx.conf ===
[complete Nginx configuration]

=== deploy.sh ===
[complete deployment script]

=== logging.conf ===
[complete logging configuration]

Important requirements:
- Use production best practices
- Include proper error handling
- Add helpful comments
- Ensure all configurations are valid and ready to use
- Consider security best practices
- Optimize for performance
- Include environment variable support where appropriate

Tech Stack: {tech_stack}"""


def _strip_trigger_prefix(text: str, pattern: str) -> str:
    """Strip the trigger pattern from the start of text if present."""
    if not text or not pattern:
        return text

    # Normalize for comparison: remove punctuation and lowercase
    text_normalized = re.sub(r"[^\w\s]", "", text).strip().lower()
    pattern_normalized = re.sub(r"[^\w\s]", "", pattern).strip().lower()

    if text_normalized.startswith(pattern_normalized):
        # Find where the pattern ends in the original text
        tokens = pattern_normalized.split()
        if not tokens:
            return text
        regex_pattern = r"^\s*" + r"[^\w]*".join(re.escape(t) for t in tokens) + r"[^\w]*"
        match = re.match(regex_pattern, text, re.IGNORECASE)
        if match:
            return text[match.end():].lstrip()

    return text


def _extract_tech_stack(text: str) -> str:
    """Extract and normalize tech stack description from input text."""
    if not text:
        return ""
    
    # Clean up common prefixes and normalize
    text = text.strip()
    
    # Remove common filler words
    text = re.sub(r"\b(i have|i need|generate|create|setup|for)\b", "", text, flags=re.IGNORECASE)
    text = text.strip()
    
    # Normalize separators (+, and, comma)
    text = re.sub(r"\s*\+\s*", " + ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s+and\s+", " + ", text, flags=re.IGNORECASE)
    
    return text.strip()


def _call_openai(api_key: str, model: str, prompt: str, timeout: int = 60) -> str:
    """Call OpenAI Responses API."""
    url = "https://api.openai.com/v1/responses"
    payload = {
        "model": model,
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

    # Extract text from response
    output = response_data.get("output") or []
    if output and isinstance(output, list):
        for item in output:
            if item.get("type") == "message":
                content = item.get("content") or []
                for c in content:
                    if c.get("type") == "output_text":
                        return c.get("text", "").strip()

    raise RuntimeError("No response returned from OpenAI.")


def before_paste():
    """Main plugin function - generates DevOps files from tech stack description."""
    api_key = freeway.get_setting("api_key")
    if not api_key:
        freeway.log("OpenAI API key is missing; skipping.")
        return

    model = freeway.get_setting("model") or "gpt-4o-mini"
    prompt_template = freeway.get_setting("prompt_template") or DEFAULT_PROMPT_TEMPLATE

    original_text = freeway.get_text()
    if not original_text:
        freeway.log("No text to process.")
        return

    # Get trigger pattern and strip it from text if present
    trigger = freeway.get_trigger()
    trigger_pattern = trigger.get("pattern") if trigger else None

    if trigger_pattern:
        tech_stack_text = _strip_trigger_prefix(original_text, trigger_pattern)
    else:
        tech_stack_text = original_text

    tech_stack_text = tech_stack_text.strip()
    if not tech_stack_text:
        freeway.log("No tech stack description found; skipping.")
        return

    # Extract and normalize tech stack
    tech_stack = _extract_tech_stack(tech_stack_text)
    if not tech_stack:
        tech_stack = tech_stack_text  # Fallback to original if extraction fails

    # Build prompt
    prompt = prompt_template.replace("{tech_stack}", tech_stack)

    freeway.set_status_text("Generating DevOps files…")
    freeway.set_indicator_color("#FF6B6B")  # DevOps red/orange color

    try:
        response_text = _call_openai(api_key, model, prompt)
        
        # Clean up response if needed
        response_text = response_text.strip()
        
        freeway.set_text(response_text)
        freeway.log(f"DevOps files generated successfully with model {model}.")
        freeway.set_status_text("✓ DevOps files generated")
    except Exception as exc:  # pragma: no cover - defensive
        freeway.log(f"OpenAI error: {exc}")
        error_msg = str(exc)
        if len(error_msg) > 60:
            error_msg = error_msg[:57] + "..."
        freeway.set_status_text(f"Error: {error_msg}")

