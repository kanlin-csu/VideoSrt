"""
converter.py - 簡體中文 → 繁體中文（台灣標準）轉換
使用 OpenCC
"""
try:
    import opencc
    _CONVERTER = opencc.OpenCC("s2tw")   # 簡體 → 繁體（台灣）
    OPENCC_AVAILABLE = True
except ImportError:
    OPENCC_AVAILABLE = False
    _CONVERTER = None


def to_traditional(text: str) -> str:
    """
    將簡體中文轉換為繁體中文。
    若 OpenCC 未安裝，直接回傳原文。
    """
    if not OPENCC_AVAILABLE or _CONVERTER is None:
        return text
    return _CONVERTER.convert(text)
