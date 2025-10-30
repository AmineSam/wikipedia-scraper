import re

def _has_tqdm():
    """Return True if tqdm is available, else False."""
    try:
        import tqdm
        return True
    except ImportError:
        return False


def _tqdm(iterable, **kwargs):
    """Apply tqdm progress bar if installed, else return iterable."""
    if _has_tqdm():
        from tqdm import tqdm
        return tqdm(iterable, **kwargs)
    return iterable


def _sanitize_text(text: str) -> str:
    """Clean Wikipedia text by removing citations and extra spaces."""
    text = re.sub(r"\\[.*?\\]", "", text)  # remove citations like [1], [a]
    text = re.sub(r"\\s+", " ", text)  # normalize spaces
    text = text.replace("\\xa0", " ").strip()  # clean non-breaking spaces
    return text
