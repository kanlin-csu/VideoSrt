"""
recognizer.py - 語音識別模組
使用 faster-whisper，支援 CUDA (GTX 1660) 加速
"""
from faster_whisper import WhisperModel
from modules.converter import to_traditional


# 支援的模型大小
AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]

# GTX 1660 6GB 建議
#   medium   → ~3GB VRAM，速度快（預設）
#   large-v2 → ~5.5GB VRAM，精準度更高


def load_model(model_size: str = "medium", device: str = "auto", compute_type: str = "auto") -> WhisperModel:
    """
    載入 Whisper 模型。

    Args:
        model_size: 模型大小 (tiny/base/small/medium/large-v2/large-v3)
        device: "cuda" / "cpu" / "auto"（自動偵測 GPU）
        compute_type: "float16" / "int8" / "auto"

    Returns:
        WhisperModel 實例
    """
    import torch

    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    if compute_type == "auto":
        # GTX 1660 支援 float16，CPU 建議用 int8 加速
        compute_type = "float16" if device == "cuda" else "int8"

    print(f"  載入模型: {model_size}  裝置: {device}  精度: {compute_type}")

    # 指定下載路徑，避免 Mac/Linux 權限或找不到預設路徑的問題
    import os
    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    os.makedirs(model_dir, exist_ok=True)

    model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        download_root=model_dir
    )
    return model


def transcribe(
    model: WhisperModel,
    audio_path: str,
    language: str = None,
    task: str = "transcribe",
    to_trad: bool = True,
    beam_size: int = 5,
    progress_callback=None,   # fn(pct:float, speed_x:float, elapsed:float, remaining:float)
) -> list:
    """
    執行語音識別，附即時進度條與 GUI callback 支援。

    Args:
        model: 已載入的 WhisperModel
        audio_path: WAV 音訊路徑
        language: 語言代碼 (zh/en/ja/...)，None 則自動偵測
        task: "transcribe"（保留原語言）或 "translate"（翻譯成英文）
        to_trad: 是否將簡體中文轉為繁體中文
        beam_size: beam search 大小（越大越精準但越慢）
        progress_callback: 選配，fn(pct, speed_x, elapsed_sec, remaining_sec)

    Returns:
        list of dict，每個含 start, end, text
    """
    import time
    from tqdm import tqdm

    segments_iter, info = model.transcribe(
        audio_path,
        language=language,
        task=task,
        beam_size=beam_size,
        vad_filter=True,               # 過濾靜音片段
        vad_parameters=dict(
            min_silence_duration_ms=300
        ),
    )

    detected_lang = info.language
    lang_prob = info.language_probability
    total_duration = info.duration  # 音訊總秒數

    print(f"  偵測語言: {detected_lang} (信心度: {lang_prob:.1%})")
    print(f"  影片長度: {_fmt_duration(total_duration)}")

    results = []
    t0 = time.time()

    # 進度條：以音訊秒數為單位
    with tqdm(
        total=round(total_duration),
        unit="秒",
        desc="  轉錄進度",
        bar_format="{desc}: {percentage:3.0f}%|{bar}| {n:.0f}/{total:.0f}秒 [{elapsed}<{remaining}, {rate_fmt}]",
        dynamic_ncols=True,
        colour="cyan",
    ) as pbar:
        last_pos = 0.0

        for seg in segments_iter:
            text = seg.text.strip()

            # 更新進度條（推進到 segment 結束時間）
            advance = max(0.0, seg.end - last_pos)
            pbar.update(round(advance))
            last_pos = seg.end

            # 計算速度與剩餘時間
            elapsed_real = time.time() - t0
            speed_x = (last_pos / elapsed_real) if elapsed_real > 0 and last_pos > 0 else 0.0
            remaining = ((total_duration - last_pos) / speed_x) if speed_x > 0 else 0.0
            pct = min(last_pos / total_duration, 1.0) if total_duration > 0 else 0.0

            pbar.set_postfix_str(f"{speed_x:.1f}x 速", refresh=False)

            # 通知 GUI（若有提供 callback）
            if progress_callback:
                progress_callback(pct, speed_x, elapsed_real, remaining)

            if not text:
                continue

            # 若識別語言是中文且要求繁體，進行轉換
            if to_trad and task == "transcribe" and detected_lang in ("zh", "yue"):
                text = to_traditional(text)

            results.append({
                "start": seg.start,
                "end": seg.end,
                "text": text,
            })

    # 完成通知
    if progress_callback:
        progress_callback(1.0, 0.0, time.time() - t0, 0.0)

    return results, detected_lang


def _fmt_duration(seconds: float) -> str:
    """秒數格式化為 HH:MM:SS"""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"
