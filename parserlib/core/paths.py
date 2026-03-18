import re

def sanitize_filename(name: str, replacement: str = "_") -> str:
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1F]', replacement, name)

    if not sanitized:
        return replacement

    return sanitized