import re


def sanitize_html(text: str) -> str:
    """
    Limits the length and cleans incoming HTML messages from tags that are not allowed for output in Telegram.

    Attributes:
        text (str): input HTML message

    Returns:
        text (str): text allowed for output in Telegram
    """
    # Removes everything <a href="...">text</a>
    text = re.sub(r'<a\s+[^>]*?href=["\']https?://[^>]*?>.*?</a>', '', text, flags=re.IGNORECASE | re.DOTALL)

    # Remove all other HTML tags <...>
    text = re.sub(r'<[^>]+>', '', text)

    # Escape < and & (not in tags anymore)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')

    # Limits the maximum length of a single telegram message
    max_length = 4096
    if len(text) > max_length:
        text = text[:max_length - 4] + "..."

    return text.strip()