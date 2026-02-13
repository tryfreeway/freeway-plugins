"""
Local test script for the Markdown Note plugin.

Usage:
    python test_plugin.py                    # Run default test
    python test_plugin.py -i                 # Interactive mode
    python test_plugin.py "Take note ..."    # Custom input

No API key needed - this plugin works completely offline!
"""

import sys


TEST_INPUT = "Take note meeting with Sarah about Q2 planning we discussed the budget timeline and need to follow up with finance tomorrow also remember to update the project roadmap"


# --- Mock Freeway Module ---
class MockFreeway:
    def __init__(self):
        self._text = TEST_INPUT
        self._output = None

    def get_setting(self, key):
        return None  # No settings needed

    def get_text(self):
        return self._text

    def get_trigger(self):
        return {"pattern": "Take note", "matchType": "startsWith"}

    def set_text(self, text):
        self._output = text
        print("\n" + "=" * 50)
        print("OUTPUT:")
        print("=" * 50)
        print(text)
        print("=" * 50 + "\n")

    def set_status_text(self, text):
        print(f"[Status] {text}")

    def set_indicator_color(self, color):
        pass  # Silent

    def log(self, message):
        print(f"[Log] {message}")


# Install mock before importing plugin
mock_freeway = MockFreeway()
sys.modules["freeway"] = mock_freeway

# Now import the plugin
from plugin import before_paste


def run_single_test(text):
    """Run a single test with the given input text."""
    mock_freeway._text = text
    print(f"Input: {text[:70]}{'...' if len(text) > 70 else ''}")
    print()
    before_paste()


def interactive_mode():
    """Run in interactive mode - test multiple inputs."""
    print("=" * 50)
    print("INTERACTIVE MODE (Local - No API needed)")
    print("Type your voice input (start with 'Take note')")
    print("Type 'quit' or 'exit' to stop")
    print("=" * 50)
    print()

    while True:
        try:
            user_input = input("Voice input> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        print()
        run_single_test(user_input)
        print()


def main():
    print("Markdown Note Plugin - Local Test")
    print("No API key required!\n")

    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-i", "--interactive"):
            interactive_mode()
        else:
            # Use command line args as input
            run_single_test(" ".join(sys.argv[1:]))
    else:
        # Run default test
        run_single_test(TEST_INPUT)


if __name__ == "__main__":
    main()
