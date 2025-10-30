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


import re

IPA_CHARS = "ˈˌɑɐɒæɓʙβɔɕçɖðʤɘəɚɛɜɝɞɟɠɢʛɣħɦɧɪɨʝɭɬɫʟɱɲŋɳɴøɵʘɸθœɶɺɻʀʂʃᵻʉʊʋⱱʍχʎʏʒʑʐʔʕʢʡːˑ̩̯̃̈"
# “token” here means a short 1–3 char piece common in IPA strings (a, ʁ., k, ə etc.)
IPA_TOKEN = rf"[A-Za-zÀ-ÖØ-öø-ÿ{IPA_CHARS}]{{1,3}}(?:\s*[.\u00B7]\s*)?"

def _sanitize_text(raw: str) -> str:
    """Remove refs, IPA/phonetics (even dangling), audio cues, then normalize spacing/punctuation."""
    text = raw

    # 1) Remove Wikipedia refs like [1], [note], etc.
    text = re.sub(r"\[[^\]]*\]", "", text)

    # 2) Remove common editorial tags
    text = re.sub(r"\((?:citation needed|clarification needed|who\?)\)", "", text, flags=re.IGNORECASE)

    # 3) Remove explicit “pronunciation/audio” words & symbols in FR/NL/EN
    text = re.sub(r"\b(Écouter|Ecouter|Listen|Audio|Pronounced|Pronunciation|prononcé|prononciation|uitspraak)\b",
                  "", text, flags=re.IGNORECASE)
    text = re.sub(r"[ⓘ➤▶►🔊🔈🔉]", "", text)

    # 4) Remove slashed phonetics: / ... /
    text = re.sub(r"/[^/\n]{2,}/", "", text)

    # 5) Remove parenthetical blocks that look like IPA sequences:
    #    (a ʁ. k. z i) or ( n i. k ɔ. l a s ) etc. (≥ 3 short IPA tokens)
    text = re.sub(rf"\(\s*(?:{IPA_TOKEN}\s*){{3,}}\)", "", text)

    # 6) Remove dangling IPA sequences that end with ')', without an opening '(':
    #    e.g. "ʒ a k ʃ i ʁ a k )" or "ʃ a ʁ l d ə ɡ o l )"
    text = re.sub(rf"(?:\s*(?:{IPA_TOKEN}))+?\s*\)", "", text)

    # 7) Remove empty/near-empty parentheses left behind: () or ( )
    text = re.sub(r"\(\s*\)", "", text)

    # 8) Normalize spaces around punctuation and collapse whitespace
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s*([,;:])\s*", r" \1 ", text)   # keep a single space around , ; :
    text = re.sub(r"\s*([.])\s*", r"\1 ", text)      # sentence periods: stick to previous word, space after
    text = re.sub(r"\s+", " ", text).strip()

    return text
