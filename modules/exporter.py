"""
exporter.py - 字幕輸出模組
支援格式：SRT, VTT
"""
import os
from datetime import timedelta


def _fmt_time_srt(seconds: float) -> str:
    """轉換秒數為 SRT 時間格式：HH:MM:SS,mmm"""
    td = timedelta(seconds=seconds)
    total_s = int(td.total_seconds())
    ms = int((td.total_seconds() - total_s) * 1000)
    h = total_s // 3600
    m = (total_s % 3600) // 60
    s = total_s % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _fmt_time_vtt(seconds: float) -> str:
    """轉換秒數為 VTT 時間格式：HH:MM:SS.mmm"""
    return _fmt_time_srt(seconds).replace(",", ".")


def export_srt(segments, output_path: str, lang_label: str = "") -> str:
    """
    輸出 SRT 字幕檔。

    Args:
        segments: faster-whisper 的 segment 列表，每個含 start/end/text
        output_path: 輸出 .srt 檔案路徑
        lang_label: 語言標籤（不影響內容，僅供 log 使用）

    Returns:
        輸出路徑
    """
    lines = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{_fmt_time_srt(seg['start'])} --> {_fmt_time_srt(seg['end'])}")
        lines.append(seg["text"].strip())
        lines.append("")

    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))

    return output_path


def export_vtt(segments, output_path: str) -> str:
    """
    輸出 WebVTT 字幕檔。
    """
    lines = ["WEBVTT", ""]
    for i, seg in enumerate(segments, start=1):
        lines.append(f"{i}")
        lines.append(f"{_fmt_time_vtt(seg['start'])} --> {_fmt_time_vtt(seg['end'])}")
        lines.append(seg["text"].strip())
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path


def export_bilingual_srt(zh_segments, en_segments, output_path: str) -> str:
    """
    合併中英文 segments 輸出雙語 SRT。
    以中文時間軸為基準，英文作為第二行。
    """
    # 建立英文查找表（用 start 時間四捨五入當 key）
    en_map = {}
    for seg in en_segments:
        key = round(seg["start"], 1)
        en_map[key] = seg["text"].strip()

    lines = []
    for i, seg in enumerate(zh_segments, start=1):
        en_text = en_map.get(round(seg["start"], 1), "")
        zh_text = seg["text"].strip()

        lines.append(str(i))
        lines.append(f"{_fmt_time_srt(seg['start'])} --> {_fmt_time_srt(seg['end'])}")
        lines.append(zh_text)
        if en_text:
            lines.append(en_text)
        lines.append("")

    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))

    return output_path


def build_output_path(input_path: str, suffix: str, fmt: str) -> str:
    """
    根據輸入路徑建立輸出路徑。
    例：video.mp4 → video.zh.srt
    """
    base = os.path.splitext(input_path)[0]
    return f"{base}.{suffix}.{fmt}"
