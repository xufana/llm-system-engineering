import datetime
import math


def calculator(expression: str) -> str:
    """Evaluate a mathematical expression. Supports the full math module.

    Args:
        expression: Python expression, e.g. "2**10" or "math.sqrt(144)"
    """
    try:
        allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
        allowed["math"] = math  # allow math.sqrt() style expressions
        return str(eval(expression, {"__builtins__": {}}, allowed))
    except Exception as e:
        return f"Error: {e}"


def get_current_time() -> str:
    """Return the current UTC date and time."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def count_words(text: str) -> str:
    """Count words and characters in a text string.

    Args:
        text: The text to analyze
    """
    words = text.split()
    return f"Words: {len(words)}, Characters: {len(text)}"
