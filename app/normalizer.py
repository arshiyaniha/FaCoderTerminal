from __future__ import annotations

import re

_ARABIC_TO_PERSIAN = str.maketrans({"ي": "ی", "ك": "ک", "ة": "ه"})
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_fa(text: str) -> str:
    value = (text or "").strip().translate(_ARABIC_TO_PERSIAN).translate(_DIGITS)
    value = value.replace("\u200c", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_for_match(text: str) -> str:
    value = normalize_fa(text).lower()
    value = re.sub(r"[،؛:!؟?.,()\[\]{}\"']", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()
