import re
#import html

def sanitize_html(text: str) -> str:
    # Removes everything <a href="...">text</a>
    text = re.sub(r'<a\s+[^>]*?href=["\']https?://[^>]*?>.*?</a>', '', text, flags=re.IGNORECASE | re.DOTALL)

    # Remove all other HTML tags <...>
    text = re.sub(r'<[^>]+>', '', text)

    # Escape < and & (not in tags anymore)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')

    # Limits the maximum message length
    MAX_LENGTH = 4096
    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH - 4] + "..."

    return text.strip()