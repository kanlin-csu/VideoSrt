"""
recognizer.py - 語音識別模組
使用 faster-whisper，支援 CUDA (GTX 1660) 加速
"""
import sys
import platform
import os


def _load_cuda_dlls():
    """
    Windows 上，透過 pip 安裝的 nvidia-cublas-cu12 / nvidia-cudnn-cu12
    會把 DLL 放在 site-packages/nvidia/*/bin，但該路徑預設不在 PATH 上，
    導致 CTranslate2 找不到 cublas64_12.dll。此處手動掛載這些目錄。
    在非 Windows 或未安裝這些套件時安靜略過。
    """
    if sys.platform != "win32":
        return
    try:
        import nvidia
    except ImportError:
        return
    base = list(nvidia.__path__)[0]
    for sub in ("cublas", "cudnn", "cuda_nvrtc"):
        d = os.path.join(base, sub, "bin")
        if os.path.isdir(d):
            try:
                os.add_dll_directory(d)
            except (OSError, AttributeError):
                pass
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")


_load_cuda_dlls()

from faster_whisper import WhisperModel
from modules.converter import to_traditional

# 判斷是否為 Mac Apple Silicon (M1/M2/M3) 環境
IS_MAC_ARM = sys.platform == "darwin" and platform.machine() == "arm64"


def _cuda_available() -> bool:
    """
    偵測是否有可用的 CUDA GPU，不依賴 torch（本專案未安裝 torch）。
    直接問 CTranslate2 認得幾張 CUDA 裝置。
    """
    try:
        from ctranslate2 import get_cuda_device_count
        return get_cuda_device_count() > 0
    except Exception:
        return False


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
    if device == "auto":
        device = "cuda" if _cuda_available() else "cpu"

    if compute_type == "auto":
        # GTX 1660 支援 float16，CPU 建議用 int8 加速
        compute_type = "float16" if device == "cuda" else "int8"

    print(f"  載入模型: {model_size}  裝置: {device}  精度: {compute_type}")

    if IS_MAC_ARM and device != "cpu":
        # 在 Mac ARM 環境下，若使用者沒有強制指定 cpu，則改用 mlx-whisper
        # MLX-Whisper 使用 Hugging Face 上的 MLX 社群模型路徑
        mlx_model_name = f"mlx-community/whisper-{model_size}-mlx"
        print(f"  [Mac 專屬] 啟動 MLX-Whisper 硬體加速引擎: {mlx_model_name}")
        return mlx_model_name

    # 原有 faster-whisper 載入邏輯 (Windows, Linux, 或 Mac 強制純 CPU 模式)
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
    batch_size: int = 8,
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
        batch_size: 批次推論大小。>1 時啟用 BatchedInferencePipeline，
            以 VAD 切段後平行送入 GPU，速度通常快 2~4 倍、GPU 使用率更高。
            設為 1（或 0）則走傳統逐段模式。8GB 顯存 + large-v3 建議 8。
        progress_callback: 選配，fn(pct, speed_x, elapsed_sec, remaining_sec)

    Returns:
        list of dict，每個含 start, end, text
    """
    import time
    from tqdm import tqdm

    results = []
    t0 = time.time()
    
    # ── MLX-Whisper 處理邏輯 ──
    if isinstance(model, str):
        import mlx_whisper
        print("  正在使用 MLX-Whisper 處理音訊中，請稍候...")
        
        # mlx_whisper 沒有 yield 機制，一次性回傳結果
        mlx_result = mlx_whisper.transcribe(
            audio_path,
            path_or_hf_repo=model,
            language=language,
            task=task,
            word_timestamps=False,
            # 在 MLX 中沒有直接對應 beam_size，這裡依賴其內部預設
        )
        
        detected_lang = mlx_result.get("language", language or "unknown")
        print(f"  偵測語言: {detected_lang}")
        
        # 轉換 mlx_whisper 格式到系統所需格式
        for seg in mlx_result.get("segments", []):
            text = seg.get("text", "").strip()
            if not text:
                continue
                
            if to_trad and task == "transcribe" and detected_lang in ("zh", "yue"):
                text = to_traditional(text)
                
            results.append({
                "start": seg.get("start", 0.0),
                "end": seg.get("end", 0.0),
                "text": text,
            })
            
    # ── 原有 faster-whisper 處理邏輯 ──
    else:
        vad_params = dict(min_silence_duration_ms=300)

        if batch_size and batch_size > 1:
            # 批次模式：以 VAD 切段後平行送入 GPU，速度更快、GPU 使用率更高
            from faster_whisper import BatchedInferencePipeline
            engine = BatchedInferencePipeline(model=model)
            print(f"  批次模式啟用 (batch_size={batch_size})")
            segments_iter, info = engine.transcribe(
                audio_path,
                language=language,
                task=task,
                beam_size=beam_size,
                batch_size=batch_size,
                word_timestamps=True,          # 供後續拆成「一句一列」
                vad_parameters=vad_params,
            )
        else:
            # 逐段模式（傳統）
            segments_iter, info = model.transcribe(
                audio_path,
                language=language,
                task=task,
                beam_size=beam_size,
                vad_filter=True,               # 過濾靜音片段
                vad_parameters=vad_params,
            )

        detected_lang = info.language
        lang_prob = info.language_probability
        total_duration = info.duration  # 音訊總秒數

        print(f"  偵測語言: {detected_lang} (信心度: {lang_prob:.1%})")
        print(f"  影片長度: {_fmt_duration(total_duration)}")

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

                # 將 segment 切成「一句一列」的字幕
                # （批次模式的長段會在此依標點與長度拆短；逐段模式維持原樣）
                for cs, ce, ctext in _seg_to_cues(seg):
                    ctext = ctext.strip()
                    if not ctext:
                        continue
                    # 若識別語言是中文且要求繁體，進行轉換
                    if to_trad and task == "transcribe" and detected_lang in ("zh", "yue"):
                        ctext = to_traditional(ctext)
                    results.append({
                        "start": cs,
                        "end": ce,
                        "text": ctext,
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


# ── 字幕斷句：把批次模式的長段拆成「一句一列」 ──
_HARD_PUNCT = "。！？!?…"          # 句尾標點：硬斷句
_SOFT_PUNCT = "，、,;；：:"          # 次級標點：過長時的軟斷點


def _char_width(ch: str) -> int:
    """全形/CJK 字元算 2，其餘算 1，用來估算字幕列的視覺寬度。"""
    o = ord(ch)
    if (0x4E00 <= o <= 0x9FFF or   # CJK 統一表意
            0x3040 <= o <= 0x30FF or   # 日文假名
            0xAC00 <= o <= 0xD7A3 or   # 韓文
            0xFF00 <= o <= 0xFFEF or   # 全形符號
            0x3000 <= o <= 0x303F):    # CJK 標點
        return 2
    return 1


def _text_width(s: str) -> int:
    return sum(_char_width(c) for c in s)


def _split_words_to_cues(words, max_width: int = 40):
    """
    依標點與長度，把帶時間戳的字詞序列切成多列字幕（一句一列）。
      - 遇句尾標點（。！？）即斷句
      - 過長且遇次級標點（，、）也斷
      - 真的太長（>1.4x）則強制斷，避免單列爆長
    max_width 以視覺寬度計（CJK 算 2），40 約等於 20 個中文字。
    每列時間 = 該列首字開始、末字結束。
    """
    cues = []
    buf = []
    for w in words:
        buf.append(w)
        text = "".join(x.word for x in buf).strip()
        if not text:
            buf = []
            continue
        width = _text_width(text)
        last = text[-1]
        if last in _HARD_PUNCT or \
                (width >= max_width and last in _SOFT_PUNCT) or \
                width >= max_width * 1.4:
            cues.append((buf[0].start, buf[-1].end, text))
            buf = []
    if buf:
        text = "".join(x.word for x in buf).strip()
        if text:
            cues.append((buf[0].start, buf[-1].end, text))
    return cues


def _seg_to_cues(seg):
    """有字詞時間戳（批次模式）→ 拆成一句一列；否則整段一列（逐段模式行為不變）。"""
    words = getattr(seg, "words", None)
    if not words:
        return [(seg.start, seg.end, seg.text)]
    cues = _split_words_to_cues(words)
    return cues if cues else [(seg.start, seg.end, seg.text)]
