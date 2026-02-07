import json
import os
import subprocess
import urllib.request
import urllib.error
import ssl
from datetime import datetime


try:
    import freeway
except ImportError:
    freeway = None

SYSTEM_PROMPT = """You are an intelligent productivity agent that transforms raw voice-to-text input
into structured, actionable outputs for real-world workflows.

Your goal is NOT to summarize.
Your goal is to UNDERSTAND intent and produce usable actions.

CORE RESPONSIBILITIES
1. Analyze the input text deeply.
2. Detect user intent.
3. Extract structured data.
4. Output clean, deterministic JSON.
5. Never hallucinate missing information.

INTENT DETECTION
Classify each detected item as ONE of:
- note        → general note or information
- task        → actionable to-do
- reminder    → time-based reminder
- meeting     → meeting, call, appointment
- idea        → idea, brainstorm, concept
- journal     → personal reflection / thoughts

If multiple intents exist → SPLIT into multiple items.

DATA EXTRACTION RULES
For EACH item extract:
- type        (intent type)
- title       (short, clear, human-readable)
- description (cleaned, structured text)
- due_date    (YYYY-MM-DD or null)
- time        (HH:MM or null)
- priority    (low | medium | high — inferred)
- tags        (relevant keywords)

Rules:
- NEVER invent dates or times.
- If unclear → null.
- Normalize messy speech into clean language.
- Remove filler words.
- Keep meaning intact.
- IMPORTANT: Support Russian date/time formats (e.g., "восемнадцать ноль-ноль" → 18:00, "послезавтра" → calculate date).
- If the user says "завтра" (tomorrow), use the current date to calculate it.
- CURRENT DATE: {current_date}

Return ONLY valid JSON.
No markdown. No explanations. No extra text.

Schema:
{
  "items": [
    {
      "type": "",
      "title": "",
      "description": "",
      "due_date": null,
      "time": null,
      "priority": "",
      "tags": []
    }
  ]
}
"""

def create_calendar_event(item):
    title = item.get("title", "No Title")
    description = item.get("description", "")
    due_date = item.get("due_date")
    time_str = item.get("time")

    if not due_date:
        return False

    try:
        y, m, dd = map(int, due_date.split('-'))
        h, mn = map(int, time_str.split(':')) if time_str else (0, 0)
    except:
        return False

    safe_title = title.replace('"', '\\"').replace('\n', ' ')[:100]
    safe_desc = description.replace('"', '\\"').replace('\n', ' ')[:500]

    applescript = f'''
    try
        set month_list to {{January, February, March, April, May, June, July, August, September, October, November, December}}
        set d_start to (current date)
        set year of d_start to {y}
        set month of d_start to (item {m} of month_list)
        set day of d_start to {dd}
        set time of d_start to ({h} * 3600 + {mn} * 60)
        set d_end to (d_start + 3600)

        tell application "Calendar"
            set t_cal to first calendar
            make new event at end of events of t_cal with properties {{summary:"{safe_title}", start date:d_start, end date:d_end, description:"{safe_desc}"}}
            return name of t_cal
        end tell
    on error msg number num
        return "ERROR_" & num & ": " & msg
    end try
    '''
    
    try:
        proc = subprocess.run(["osascript"], input=applescript, capture_output=True, text=True, check=True)
        res = proc.stdout.strip()
        if res.startswith("ERROR_"):
            return res
        return res
    except:
        return False

def core_process(input_text, settings_dict=None):
    if not input_text:
        return None

    import unicodedata
    input_text = unicodedata.normalize('NFC', input_text)
    
    import re
    input_text = re.sub(r"^(?i)(эй|hey)[,\s]*", "", input_text).strip()

    api_key = None
    model = "gpt-4o-mini"
    
    if settings_dict:
        api_key = settings_dict.get("openai_api_key")
        model = settings_dict.get("model") or model
    
    if not api_key and freeway:
        try:
            api_key = freeway.get_setting("openai_api_key")
            model = freeway.get_setting("model") or model
        except: pass

    if not api_key:
        try:
            settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, "r") as f:
                    s_data = json.load(f)
                    api_key = s_data.get("settings", {}).get("openai_api_key")
                    model = s_data.get("settings", {}).get("model") or model
        except: pass

    if not api_key:
        return "Error: Missing OpenAI API Key"

    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = SYSTEM_PROMPT.replace("{current_date}", current_date)

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": input_text}],
        "temperature": 0
    }

    try:
        context = ssl._create_unverified_context()
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=30, context=context) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content = res_data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"API Error: {str(e)}"

    try:
        json_str = content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
            
        data = json.loads(json_str)
        items = data.get("items", [])
        
        md_output = []
        for item in items:
            item_type = item.get("type", "note")
            title = item.get("title", "Untitled")
            desc = item.get("description", "")
            
            if item_type == "meeting" or item.get("due_date"):
                result = create_calendar_event(item)
                if isinstance(result, str) and not result.startswith("Error"):
                    status = f"📅 Created in {result}"
                else:
                    status = f"⚠️ Failed ({result})"
                md_output.append(f"### {status}: {title}")
            else:
                prefix = {"task": "[]", "reminder": "⏰", "idea": "💡", "journal": "📝"}.get(item_type, "•")
                md_output.append(f"### {prefix} {title}")
            
            if desc: md_output.append(desc)
            
            meta = []
            if item.get("due_date"): meta.append(f"Date: {item['due_date']}")
            if item.get("time"): meta.append(f"Time: {item['time']}")
            if meta: md_output.append("> " + " | ".join(meta))
            md_output.append("---")
            
        final_text = "\n\n".join(md_output)
        
        if freeway:
            try:
                freeway.set_text(final_text)
                freeway.set_status_text(f"Processed {len(items)} items")
            except: pass
            
        return final_text
    except Exception as e:
        return f"Parse Error: {str(e)}"

def before_transcribe():
    pass

def before_paste():
    try: text = freeway.get_text()
    except: text = None
    
    if text:
        res = core_process(text)
        if res:
            try: freeway.skip_paste()
            except: pass

def run(input_text, settings):
    return core_process(input_text, settings)

if __name__ == "__main__":
    input_text = os.environ.get("FREEWAY_TEXT")
    if not input_text:
        import sys
        if not sys.stdin.isatty():
            input_text = sys.stdin.read().strip()
    
    if input_text:
        print(core_process(input_text))