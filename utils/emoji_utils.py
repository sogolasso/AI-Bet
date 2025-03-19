"""
Utility functions for handling emojis in text messages.
This helps avoid encoding issues when logging or displaying emojis.
"""

import re
import sys
import unicodedata

def remove_emojis(text):
    """
    Remove emojis and other non-ASCII characters from text.
    Useful for logging in environments with limited charset support.
    """
    if not text:
        return ""
    
    # Pattern to match emoji characters
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251" 
        "]+"
    )
    
    return emoji_pattern.sub(r'', text)

def sanitize_for_console(text):
    """
    Sanitize text for console output by replacing emojis with their descriptions
    or removing them if description is not available.
    """
    if not text:
        return ""
    
    # Check if we're in a terminal that supports UTF-8
    if sys.stdout.encoding and 'utf' in sys.stdout.encoding.lower():
        return text
    
    # Otherwise, remove emojis
    return remove_emojis(text)

def emoji_to_html(text):
    """
    Convert emoji characters to HTML entities for safe transmission in HTML messages.
    """
    if not text:
        return ""
    
    result = ""
    for char in text:
        if ord(char) > 127:
            # Convert non-ASCII to HTML numeric entity
            result += f"&#{ord(char)};"
        else:
            result += char
            
    return result

def get_safe_emoji(emoji, fallback=""):
    """
    Returns the emoji if the environment supports it, otherwise returns the fallback.
    """
    try:
        # Test if we can encode the emoji in the current encoding
        emoji.encode(sys.stdout.encoding)
        return emoji
    except (UnicodeEncodeError, AttributeError):
        return fallback 