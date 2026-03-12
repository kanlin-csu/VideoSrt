"""
subtitle_gen.py - 自動字幕生成工具 (CLI)
========================================
支援：MP4 H.264 / H.265
輸出：繁體中文 SRT / 英文 SRT / 雙語 SRT / VTT

使用方式：
  python subtitle_gen.py --input video.mp4
  python subtitle_gen.py --input video.mp4 --lang zh --task both
  python subtitle_gen.py --input video.mp4 --model large-v2 --format srt vtt
  python subtitle_gen.py --input video.mp4 --device cpu
"""

import argparse
import os
import sys
import time
import tempfile

from colorama import init, Fore, Style

init(autoreset=True)  # colorama Windows 相容


# ──────────────────────────────────────────────────────────────
# 工具函式
# ──────────────────────────────────────────────────────────────

def banner():
    print(Fore.CYAN + Style.BRIGHT + """
╔══════════════════════════════════════════════╗
║      🎬  自動字幕生成工具  v1.0 (CLI)       ║
║   faster-whisper + FFmpeg + OpenCC           ║
╚══════════════════════════════════════════════╝
""")


def step(msg: str):
    print(Fore.GREEN + f"\n▶ {msg}")


def info(msg: str):
    print(Fore.WHITE + f"  {msg}")


def warn(msg: str):
    print(Fore.YELLOW + f"  ⚠  {msg}")


def error(msg: str):
    print(Fore.RED + f"  ✗  {msg}")


def success(msg: str):
    print(Fore.CYAN + f"  ✔  {msg}")


def elapsed(t0: float) -> str:
    s = time.time() - t0
    return f"{s:.1f}s" if s < 60 else f"{int(s//60)}m{int(s%60)}s"


# ──────────────────────────────────────────────────────────────
# 主程式
# ──────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        prog="subtitle_gen",
        description="自動字幕生成工具 - MP4 → SRT/VTT (繁中/英文/雙語)",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--input", "-i",
        required=True,
        metavar="VIDEO",
        help="輸入影片路徑 (MP4, H.264/H.265)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        metavar="DIR",
        help="輸出目錄 (預設：與影片相同目錄)",
    )
    parser.add_argument(
        "--model", "-m",
        default="medium",
        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
        help="Whisper 模型大小\n  medium (預設, ~3GB VRAM)\n  large-v2 (更精準, ~5.5GB VRAM)",
    )
    parser.add_argument(
        "--lang", "-l",
        default=None,
        metavar="LANG",
        help="語言代碼：zh, en, ja...\n  (預設：自動偵測)",
    )
    parser.add_argument(
        "--task", "-t",
        default="transcribe",
        choices=["transcribe", "translate", "both"],
        help="識別任務：\n"
             "  transcribe - 保留原語言 (繁中, 預設)\n"
             "  translate  - 輸出英文\n"
             "  both       - 同時輸出繁中與英文雙語",
    )
    parser.add_argument(
        "--format", "-f",
        nargs="+",
        default=["srt"],
        choices=["srt", "vtt"],
        metavar="FMT",
        help="輸出格式 (可複選)：srt vtt\n  例：--format srt vtt",
    )
    parser.add_argument(
        "--device", "-d",
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="運算裝置：auto(自動)/cuda(GPU)/cpu",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Beam search 大小 (預設: 5，越大越精準但越慢)",
    )
    parser.add_argument(
        "--no-trad",
        action="store_true",
        help="不轉換繁體中文 (保留 Whisper 原始輸出)",
    )

    return parser.parse_args()


def run():
    banner()
    args = parse_args()

    # ── 驗證輸入檔 ───────────────────────────────────────────
    input_path = os.path.abspath(args.input)
    if not os.path.isfile(input_path):
        error(f"找不到輸入檔：{input_path}")
        sys.exit(1)

    ext = os.path.splitext(input_path)[1].lower()
    if ext not in (".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"):
        warn(f"非常見影片格式，仍嘗試處理：{ext}")

    # ── 輸出目錄 ─────────────────────────────────────────────
    if args.output:
        output_dir = os.path.abspath(args.output)
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = os.path.dirname(input_path)

    base_name = os.path.splitext(os.path.basename(input_path))[0]

    # ── 匯入模組（延遲匯入以快速顯示使用說明）────────────────
    from modules.extractor import extract_audio
    from modules.recognizer import load_model, transcribe
    from modules.exporter import export_srt, export_vtt, export_bilingual_srt

    total_t0 = time.time()

    # ── Step 1: 音訊提取 ─────────────────────────────────────
    step("Step 1/3：提取音訊")
    info(f"來源：{input_path}")
    t0 = time.time()

    tmp_wav = None
    try:
        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_wav_path = tmp_wav.name
        tmp_wav.close()

        extract_audio(input_path, tmp_wav_path)
        success(f"音訊提取完成 ({elapsed(t0)})")
    except Exception as e:
        error(f"音訊提取失敗：{e}")
        _cleanup(tmp_wav)
        sys.exit(1)

    # ── Step 2: 載入模型 ─────────────────────────────────────
    step("Step 2/3：載入 Whisper 模型")
    t0 = time.time()
    try:
        model = load_model(
            model_size=args.model,
            device=args.device,
        )
        success(f"模型載入完成 ({elapsed(t0)})")
    except Exception as e:
        error(f"模型載入失敗：{e}")
        _cleanup(tmp_wav_path)
        sys.exit(1)

    # ── Step 3: 語音識別 ─────────────────────────────────────
    step("Step 3/3：語音識別")
    t0 = time.time()

    try:
        outputs = []  # list of (segments, suffix)

        if args.task in ("transcribe", "both"):
            info("執行轉錄（繁體中文）...")
            segs_zh, detected_lang = transcribe(
                model,
                tmp_wav_path,
                language=args.lang,
                task="transcribe",
                to_trad=not args.no_trad,
                beam_size=args.beam_size,
            )
            outputs.append((segs_zh, "zh"))

        if args.task in ("translate", "both"):
            info("執行翻譯（英文）...")
            segs_en, _ = transcribe(
                model,
                tmp_wav_path,
                language=args.lang,
                task="translate",
                to_trad=False,
                beam_size=args.beam_size,
            )
            outputs.append((segs_en, "en"))

        success(f"語音識別完成 ({elapsed(t0)})")

    except Exception as e:
        error(f"語音識別失敗：{e}")
        _cleanup(tmp_wav_path)
        sys.exit(1)
    finally:
        _cleanup(tmp_wav_path)

    # ── 輸出字幕檔 ───────────────────────────────────────────
    print()
    saved_files = []

    if args.task == "both" and len(outputs) == 2:
        segs_zh, _ = outputs[0]
        segs_en, _ = outputs[1]

        # 雙語 SRT（中英合併）
        if "srt" in args.format:
            out = os.path.join(output_dir, f"{base_name}.bilingual.srt")
            export_bilingual_srt(segs_zh, segs_en, out)
            saved_files.append(out)

        # 單語 SRT
        zh_srt = os.path.join(output_dir, f"{base_name}.zh.srt")
        export_srt(segs_zh, zh_srt)
        saved_files.append(zh_srt)

        en_srt = os.path.join(output_dir, f"{base_name}.en.srt")
        export_srt(segs_en, en_srt)
        saved_files.append(en_srt)

        # VTT 輸出
        if "vtt" in args.format:
            from modules.exporter import export_vtt
            zh_vtt = os.path.join(output_dir, f"{base_name}.zh.vtt")
            export_vtt(segs_zh, zh_vtt)
            saved_files.append(zh_vtt)

            en_vtt = os.path.join(output_dir, f"{base_name}.en.vtt")
            export_vtt(segs_en, en_vtt)
            saved_files.append(en_vtt)

    else:
        for segs, lang_suffix in outputs:
            if "srt" in args.format:
                out = os.path.join(output_dir, f"{base_name}.{lang_suffix}.srt")
                export_srt(segs, out)
                saved_files.append(out)

            if "vtt" in args.format:
                out = os.path.join(output_dir, f"{base_name}.{lang_suffix}.vtt")
                export_vtt(segs, out)
                saved_files.append(out)

    # ── 完成摘要 ─────────────────────────────────────────────
    print(Fore.CYAN + Style.BRIGHT + "\n" + "═" * 50)
    print(Fore.CYAN + Style.BRIGHT + f"  ✅  完成！總耗時：{elapsed(total_t0)}")
    print(Fore.CYAN + Style.BRIGHT + "═" * 50)

    print(Fore.WHITE + "\n  輸出檔案：")
    for f in saved_files:
        print(Fore.GREEN + f"    📄 {f}")

    print()


def _cleanup(path):
    """刪除暫存 WAV 檔"""
    if path and isinstance(path, str) and os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


if __name__ == "__main__":
    run()
