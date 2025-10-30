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




def _sanitize_text(raw: str) -> str:
    """Clean Wikipedia intro text by removing references, phonetics, redirections, and extra spaces."""
    text = raw

    # Remove reference brackets like [1], [citation needed]
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"\((?:citation needed|clarification needed|who\?)\)", "", text, flags=re.IGNORECASE)

    # Remove IPA or phonetic sequences between /.../, (...), or [...]
    text = re.sub(
        r"[\/\[\(]\s*[ˈˌʔɡθðʃʒŋɪɛæɑɔʊɒəɚɝɾʌɜ̃ɲɾɫ̃ːa-zA-ZÀ-ž0-9\s\.\-ʼ'ˈˌʰʲʷʲ̩̯]+\s*[\)\/\]]",
        "",
        text,
    )

    # Remove sequences like "n i. k. l a s a ʁ. k. z i" (broken-down IPA letters)
    text = re.sub(r"(?:[a-zA-Zʁɡɪʊɔɐɛøœðʃʒŋɲɾɫ̃ː]\.\s*){2,}", "", text)

    # Remove textual phonetic hints (e.g., "van BYOO-rən", "bew-KAN-ən", "mən-ROH")
    text = re.sub(
        r"\b(?:van|bew|mən|BYOO|ROH|KAN|rən|bjuː|KOOL|ij|mən|roh|van)\b[-–—]?[A-Z\-a-z]+\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove pronunciation words in different languages (FR, NL, EN)
    text = re.sub(
        r"\b(Écouter|Prononciation|Prononcé|Pronounced|Pronunciation|Uitspraak|uitspraak|écouter)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove redirection or disambiguation messages (especially in French)
    text = re.sub(
        r"(redirige(?:nt)? ici|homonymes|article concerne|voir article|redirects? here)",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove leftover symbols and icons
    text = re.sub(r"[ⓘ➤▶►🔊🔈🔉]", "", text)

    # Clean punctuation and normalize spaces
    text = re.sub(r"\s*[;/,:]\s*", " ", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:])", r"\1", text)

    return text
