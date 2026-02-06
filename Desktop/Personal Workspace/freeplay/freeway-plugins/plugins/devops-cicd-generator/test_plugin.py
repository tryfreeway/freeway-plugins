#!/usr/bin/env python3

import os
import sys
import json


class MockFreeway:
    def __init__(self):
        self.settings = {
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
            "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            "prompt_template": None,
        }
        self.text = ""
        self.trigger = {"pattern": "I have", "matchType": "startsWith"}
        self.status_text = ""
        self.indicator_color = ""
        self.logs = []
    
    def get_setting(self, key):
        return self.settings.get(key)
    
    def get_text(self):
        return self.text
    
    def set_text(self, text):
        print("\n" + "=" * 80)
        print("GENERATED OUTPUT:")
        print("=" * 80)
        print(text)
        print("=" * 80 + "\n")
    
    def get_trigger(self):
        return self.trigger
    
    def set_status_text(self, text):
        self.status_text = text
        print(f"[STATUS] {text}")
    
    def set_indicator_color(self, color):
        self.indicator_color = color
    
    def log(self, message):
        self.logs.append(message)
        print(f"[LOG] {message}")
    
    def get_temp_dir(self):
        return "/tmp"


sys.modules['freeway'] = MockFreeway()

from plugin import before_paste, _extract_tech_stack, _strip_trigger_prefix


def test_tech_stack_extraction():
    print("\n" + "=" * 80)
    print("TESTING: Tech Stack Extraction")
    print("=" * 80)
    
    test_cases = [
        ("I have Node.js and PostgreSQL", "Node.js + PostgreSQL"),
        ("I have .NET Core + Angular + Redis", ".NET Core + Angular + Redis"),
        ("I have Python Flask, MySQL, and Nginx", "Python Flask, MySQL, Nginx"),
        ("Node.js and MongoDB", "Node.js + MongoDB"),
    ]
    
    for input_text, expected_pattern in test_cases:
        result = _extract_tech_stack(input_text)
        print(f"Input: '{input_text}'")
        print(f"Output: '{result}'")
        print(f"Expected pattern: '{expected_pattern}'")
        print()


def test_trigger_stripping():
    print("\n" + "=" * 80)
    print("TESTING: Trigger Prefix Stripping")
    print("=" * 80)
    
    test_cases = [
        ("I have Node.js", "I have", "Node.js"),
        ("I have .NET Core + Angular", "I have", ".NET Core + Angular"),
        ("Node.js and PostgreSQL", "I have", "Node.js and PostgreSQL"),
    ]
    
    for text, pattern, expected in test_cases:
        result = _strip_trigger_prefix(text, pattern)
        print(f"Text: '{text}'")
        print(f"Pattern: '{pattern}'")
        print(f"Result: '{result}'")
        print(f"Expected: '{expected}'")
        print(f"Match: {'✓' if result.strip() == expected else '✗'}")
        print()


def test_plugin_integration():
    print("\n" + "=" * 80)
    print("TESTING: Full Plugin Integration")
    print("=" * 80)
    
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("\n⚠️  WARNING: OPENAI_API_KEY environment variable not set!")
        print("   Set it to test the full integration:")
        print("   export OPENAI_API_KEY='sk-...'")
        print("\n   Skipping API call test...")
        return
    
    mock_freeway = sys.modules['freeway']
    mock_freeway.text = "I have Node.js and PostgreSQL"
    mock_freeway.settings["api_key"] = api_key
    
    print(f"\nTest Input: '{mock_freeway.text}'")
    print(f"API Key: {'Set' if api_key else 'Not Set'}")
    print(f"Model: {mock_freeway.settings['model']}")
    print("\nCalling before_paste()...")
    print("-" * 80)
    
    try:
        before_paste()
        print("\n✓ Plugin executed successfully!")
        print(f"\nLogs: {len(mock_freeway.logs)} entries")
        for log in mock_freeway.logs:
            print(f"  - {log}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("\n" + "=" * 80)
    print("DEVOPS & CI/CD GENERATOR PLUGIN - TEST SUITE")
    print("=" * 80)
    
    test_tech_stack_extraction()
    test_trigger_stripping()
    test_plugin_integration()
    
    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)
    print("\nNote: To test with actual OpenAI API:")
    print("  1. Get API key from https://platform.openai.com/api-keys")
    print("  2. Set environment variable: export OPENAI_API_KEY='sk-...'")
    print("  3. Run this script again")
    print()


if __name__ == "__main__":
    main()
