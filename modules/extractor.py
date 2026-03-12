"""
extractor.py - 從 MP4/影片檔提取音訊
支援 H.264 / H.265 格式
輸出: 16kHz mono WAV (Whisper 最佳輸入格式)

FFmpeg 搜尋順序：
  1. 程式同目錄下的 ffmpeg\ffmpeg.exe（打包版內建）
  2. 系統 PATH 中的 ffmpeg
"""
import os
import sys
import tempfile
import ffmpeg


def _find_ffmpeg() -> str | None:
    """
    找 ffmpeg 執行檔路徑。
    優先用程式旁邊的 ffmpeg\ 資料夾（給打包版用）。
    """
    # PyInstaller 打包後，執行檔所在目錄
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    bundled = os.path.join(base_dir, "ffmpeg", "ffmpeg.exe")
    if os.path.isfile(bundled):
        return bundled

    return None   # 讓 ffmpeg-python 自己從 PATH 找


def extract_audio(video_path: str, output_path: str = None) -> str:
    """
    從影片檔提取音訊，輸出為 16kHz mono WAV。

    Args:
        video_path: 輸入影片路徑 (MP4 H.264/H.265)
        output_path: 輸出 WAV 路徑（None 則使用暫存檔）

    Returns:
        WAV 檔案路徑
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"找不到影片檔：{video_path}")

    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        output_path = tmp.name
        tmp.close()

    # 設定內建 ffmpeg 路徑（若存在）
    ffmpeg_exe = _find_ffmpeg()
    kwargs = {}
    if ffmpeg_exe:
        os.environ["PATH"] = os.path.dirname(ffmpeg_exe) + os.pathsep + os.environ.get("PATH", "")

    try:
        (
            ffmpeg
            .input(video_path)
            .output(
                output_path,
                acodec="pcm_s16le",   # 16-bit PCM
                ac=1,                  # mono
                ar=16000,              # 16kHz
                vn=None                # 不含視訊流
            )
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        stderr = e.stderr.decode("utf-8", errors="ignore") if e.stderr else "無詳細錯誤"
        raise RuntimeError(f"FFmpeg 音訊提取失敗：\n{stderr}")

    return output_path
