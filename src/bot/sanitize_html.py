#from html import escape
import re

def sanitize_html(text: str) -> str:
    allowed_tags = ["i", "u", "s", "code", "pre", "a"]
    # Удаляем все теги кроме разрешенных
    return re.sub(r"</?(?!({}))(.*?)>".format("|".join(allowed_tags)), "", text)