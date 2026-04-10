"""
gui.py - 自動字幕生成工具 (GUI)
使用 tkinter（Python 內建），適用 Windows 點擊圖示執行
支援拖拉影片直接開始轉檔（需安裝 tkinterdnd2）
"""
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import os
import sys
import tempfile

# 嘗試載入 drag-and-drop 支援（pip install tkinterdnd2）
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _DND_AVAILABLE = True
except ImportError:
    _DND_AVAILABLE = False


class SubtitleGenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("自動字幕生成工具 v1.0")
        self.root.resizable(False, False)

        # ── 狀態變數 ───────────────────────────────────────────
        self.input_var    = tk.StringVar()
        self.output_var   = tk.StringVar()
        self.model_var    = tk.StringVar(value="medium")
        self.lang_var     = tk.StringVar()
        self.task_var     = tk.StringVar(value="transcribe")
        self.fmt_srt      = tk.BooleanVar(value=True)
        self.fmt_vtt      = tk.BooleanVar(value=False)
        self.device_var   = tk.StringVar(value="auto")
        self.beam_var     = tk.IntVar(value=5)
        self.no_trad_var  = tk.BooleanVar(value=False)
        self.progress_var = tk.DoubleVar(value=0.0)
        self._running     = False

        self._build_ui()

    # ── UI 建構 ─────────────────────────────────────────────────
    def _build_ui(self):
        pad = dict(padx=10, pady=4)

        # 拖拉區域
        f_drop = ttk.LabelFrame(self.root, text=" 拖拉影片到此處，或按下方瀏覽按鈕選擇 ", padding=8)
        f_drop.grid(row=0, column=0, **pad, sticky="ew")

        self.drop_label = tk.Label(
            f_drop,
            text="🎬  將影片拖拉到此處",
            font=("Microsoft JhengHei", 13),
            fg="#555555",
            bg="#f0f0f0",
            relief="groove",
            width=60,
            height=3,
            cursor="hand2",
        )
        self.drop_label.grid(row=0, column=0, columnspan=3, pady=(0, 4), sticky="ew")
        self.drop_label.bind("<Button-1>", lambda e: self._browse_input())

        if _DND_AVAILABLE:
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)
        else:
            self.drop_label.config(
                text="🎬  點擊選擇影片\n（安裝 tkinterdnd2 可啟用拖拉功能）"
            )

        # 影片選擇
        f0 = ttk.LabelFrame(self.root, text=" 路徑設定 ", padding=8)
        f0.grid(row=1, column=0, **pad, sticky="ew")

        ttk.Label(f0, text="輸入影片：").grid(row=0, column=0, sticky="w")
        ttk.Entry(f0, textvariable=self.input_var, width=54).grid(row=0, column=1, padx=(4, 2))
        ttk.Button(f0, text="瀏覽…", width=6, command=self._browse_input).grid(row=0, column=2)

        ttk.Label(f0, text="輸出目錄：").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(f0, textvariable=self.output_var, width=54).grid(row=1, column=1, padx=(4, 2), pady=(4, 0))
        ttk.Button(f0, text="瀏覽…", width=6, command=self._browse_output).grid(row=1, column=2, pady=(4, 0))

        # 模型設定
        f1 = ttk.LabelFrame(self.root, text=" 模型設定 ", padding=8)
        f1.grid(row=2, column=0, **pad, sticky="ew")

        ttk.Label(f1, text="模型大小：").grid(row=0, column=0, sticky="w")
        ttk.Combobox(f1, textvariable=self.model_var,
                     values=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
                     state="readonly", width=12).grid(row=0, column=1, sticky="w", padx=4)

        ttk.Label(f1, text="運算裝置：").grid(row=0, column=2, sticky="w", padx=(20, 0))
        ttk.Combobox(f1, textvariable=self.device_var,
                     values=["auto", "cuda", "cpu"],
                     state="readonly", width=8).grid(row=0, column=3, sticky="w", padx=4)

        ttk.Label(f1, text="語言代碼：").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(f1, textvariable=self.lang_var, width=8).grid(row=1, column=1, sticky="w", padx=4, pady=(4, 0))
        ttk.Label(f1, text="(空白 = 自動偵測　zh / en / ja …)").grid(
            row=1, column=2, columnspan=2, sticky="w", pady=(4, 0))

        ttk.Label(f1, text="Beam Size：").grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Spinbox(f1, from_=1, to=10, textvariable=self.beam_var, width=5).grid(
            row=2, column=1, sticky="w", padx=4, pady=(4, 0))

        # 輸出設定
        f2 = ttk.LabelFrame(self.root, text=" 輸出設定 ", padding=8)
        f2.grid(row=3, column=0, **pad, sticky="ew")

        ttk.Label(f2, text="識別任務：").grid(row=0, column=0, sticky="w")
        for col, (val, lbl) in enumerate(
            [("transcribe", "轉錄（繁中）"), ("translate", "翻譯（英文）"), ("both", "雙語並輸")],
            start=1,
        ):
            ttk.Radiobutton(f2, text=lbl, variable=self.task_var, value=val).grid(
                row=0, column=col, padx=8)

        ttk.Label(f2, text="輸出格式：").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Checkbutton(f2, text="SRT", variable=self.fmt_srt).grid(row=1, column=1, pady=(4, 0))
        ttk.Checkbutton(f2, text="VTT", variable=self.fmt_vtt).grid(row=1, column=2, pady=(4, 0))
        ttk.Checkbutton(f2, text="不轉繁體", variable=self.no_trad_var).grid(
            row=1, column=3, padx=16, pady=(4, 0))

        # 進度
        f3 = ttk.LabelFrame(self.root, text=" 進度 ", padding=8)
        f3.grid(row=4, column=0, **pad, sticky="ew")

        self.progress_bar = ttk.Progressbar(
            f3, variable=self.progress_var, maximum=100, length=590)
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.status_lbl = ttk.Label(f3, text="就緒")
        self.status_lbl.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.time_lbl = ttk.Label(f3, text="")
        self.time_lbl.grid(row=1, column=1, sticky="e", pady=(2, 0))

        # 日誌
        f4 = ttk.LabelFrame(self.root, text=" 執行日誌 ", padding=8)
        f4.grid(row=5, column=0, **pad, sticky="nsew")

        self.log = scrolledtext.ScrolledText(
            f4, width=78, height=10, state="disabled", font=("Consolas", 9))
        self.log.grid(row=0, column=0)

        # 按鈕列
        fb = ttk.Frame(self.root, padding=(10, 4))
        fb.grid(row=6, column=0, sticky="ew")

        ttk.Button(fb, text="清除日誌", command=self._clear_log).pack(side="right", padx=4)
        self.start_btn = ttk.Button(fb, text="▶  開始生成字幕", command=self._start)
        self.start_btn.pack(side="right", padx=4)

    # ── 檔案瀏覽 ────────────────────────────────────────────────
    def _set_input(self, path: str):
        """設定輸入影片路徑並更新 UI"""
        path = path.strip().strip("{}")   # tkinterdnd2 在路徑有空格時加大括號
        if not path:
            return
        self.input_var.set(path)
        fname = os.path.basename(path)
        self.drop_label.config(text=f"🎬  {fname}", fg="#1a7abf")
        if not self.output_var.get():
            self.output_var.set(os.path.dirname(path))

    def _on_drop(self, event):
        """拖拉影片進入視窗"""
        self._set_input(event.data)

    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="選擇影片檔",
            filetypes=[
                ("影片檔", "*.mp4 *.mkv *.mov *.avi *.webm *.m4v"),
                ("所有檔案", "*.*"),
            ],
        )
        if path:
            self._set_input(path)

    def _browse_output(self):
        path = filedialog.askdirectory(title="選擇輸出目錄")
        if path:
            self.output_var.set(path)

    # ── 日誌工具（執行緒安全）────────────────────────────────────
    def _log(self, msg: str):
        def _append():
            self.log.configure(state="normal")
            self.log.insert("end", msg.rstrip() + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.root.after(0, _append)

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # ── 進度更新 callback（從背景執行緒呼叫）────────────────────
    def _on_progress(self, pct: float, speed_x: float, elapsed_sec: float, remaining_sec: float):
        def _update():
            self.progress_var.set(pct * 100)
            if pct >= 1.0:
                self.status_lbl.config(text="識別完成")
                self.time_lbl.config(text=f"耗時：{self._fmt_sec(elapsed_sec)}")
            else:
                self.status_lbl.config(
                    text=f"識別中 {pct * 100:.1f}%   速度：{speed_x:.1f}x")
                self.time_lbl.config(text=f"剩餘：{self._fmt_sec(remaining_sec)}")
        self.root.after(0, _update)

    @staticmethod
    def _fmt_sec(sec: float) -> str:
        s = int(sec)
        return f"{s // 60}m{s % 60:02d}s" if s >= 60 else f"{s}s"

    # ── 啟動流程 ─────────────────────────────────────────────────
    def _start(self):
        if self._running:
            return

        input_path = self.input_var.get().strip()
        if not input_path or not os.path.isfile(input_path):
            messagebox.showerror("錯誤", "請選擇有效的輸入影片")
            return

        fmt = []
        if self.fmt_srt.get():
            fmt.append("srt")
        if self.fmt_vtt.get():
            fmt.append("vtt")
        if not fmt:
            messagebox.showerror("錯誤", "請至少勾選一種輸出格式（SRT / VTT）")
            return

        self._running = True
        self.start_btn.config(state="disabled")
        self.progress_var.set(0)
        self.status_lbl.config(text="初始化中…")
        self.time_lbl.config(text="")
        self._clear_log()

        threading.Thread(target=self._worker, args=(input_path, fmt), daemon=True).start()

    # ── 背景工作執行緒 ───────────────────────────────────────────
    def _worker(self, input_path: str, fmt: list):
        """依序執行：音訊提取 → 模型載入 → 語音識別 → 字幕輸出"""

        # 把模組的 print 導向日誌視窗
        class _Redirect:
            def __init__(self, log_fn):
                self._log = log_fn
            def write(self, msg):
                if msg.strip():
                    self._log(msg)
            def flush(self):
                pass

        old_stdout = sys.stdout
        sys.stdout = _Redirect(self._log)
        tmp_wav_path = None

        try:
            output_dir = self.output_var.get().strip() or os.path.dirname(input_path)
            os.makedirs(output_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(input_path))[0]

            from modules.extractor import extract_audio
            from modules.recognizer import load_model, transcribe
            from modules.exporter import export_srt, export_vtt, export_bilingual_srt

            # Step 1：提取音訊
            self._log("▶ Step 1/3：提取音訊")
            self.root.after(0, lambda: self.status_lbl.config(text="Step 1/3：提取音訊…"))
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp_wav_path = tmp.name
            tmp.close()
            extract_audio(input_path, tmp_wav_path)
            self._log("  ✔ 音訊提取完成")

            # Step 2：載入模型
            self._log("▶ Step 2/3：載入 Whisper 模型")
            self.root.after(0, lambda: self.status_lbl.config(text="Step 2/3：載入模型…"))
            model = load_model(model_size=self.model_var.get(), device=self.device_var.get())
            self._log("  ✔ 模型載入完成")

            # Step 3：語音識別
            self._log("▶ Step 3/3：語音識別")
            self.root.after(0, lambda: self.status_lbl.config(text="Step 3/3：語音識別中…"))

            lang    = self.lang_var.get().strip() or None
            task    = self.task_var.get()
            to_trad = not self.no_trad_var.get()
            beam    = self.beam_var.get()

            outputs = []
            if task in ("transcribe", "both"):
                self._log("  執行轉錄（繁體中文）…")
                segs_zh, _ = transcribe(
                    model, tmp_wav_path, language=lang,
                    task="transcribe", to_trad=to_trad,
                    beam_size=beam, progress_callback=self._on_progress,
                )
                outputs.append((segs_zh, "zh"))

            if task in ("translate", "both"):
                self._log("  執行翻譯（英文）…")
                segs_en, _ = transcribe(
                    model, tmp_wav_path, language=lang,
                    task="translate", to_trad=False,
                    beam_size=beam, progress_callback=self._on_progress,
                )
                outputs.append((segs_en, "en"))

            # 輸出字幕檔
            saved = []
            if task == "both" and len(outputs) == 2:
                segs_zh, _ = outputs[0]
                segs_en, _ = outputs[1]
                if "srt" in fmt:
                    out = os.path.join(output_dir, f"{base_name}.bilingual.srt")
                    export_bilingual_srt(segs_zh, segs_en, out)
                    saved.append(out)
                for segs, lsuf in [(segs_zh, "zh"), (segs_en, "en")]:
                    out = os.path.join(output_dir, f"{base_name}.{lsuf}.srt")
                    export_srt(segs, out)
                    saved.append(out)
                if "vtt" in fmt:
                    for segs, lsuf in [(segs_zh, "zh"), (segs_en, "en")]:
                        out = os.path.join(output_dir, f"{base_name}.{lsuf}.vtt")
                        export_vtt(segs, out)
                        saved.append(out)
            else:
                for segs, lsuf in outputs:
                    if "srt" in fmt:
                        out = os.path.join(output_dir, f"{base_name}.{lsuf}.srt")
                        export_srt(segs, out)
                        saved.append(out)
                    if "vtt" in fmt:
                        out = os.path.join(output_dir, f"{base_name}.{lsuf}.vtt")
                        export_vtt(segs, out)
                        saved.append(out)

            self._log("\n輸出檔案：")
            for f in saved:
                self._log(f"  📄 {f}")

            result_msg = f"完成！共 {len(saved)} 個字幕檔已儲存至：\n{output_dir}"
            self.root.after(0, lambda: messagebox.showinfo("完成", result_msg))
            self.root.after(0, lambda: self.status_lbl.config(text="完成！"))

        except Exception as e:
            err = str(e)
            self._log(f"\n✗ 發生錯誤：{err}")
            self.root.after(0, lambda: messagebox.showerror("錯誤", err))
            self.root.after(0, lambda: self.status_lbl.config(text="發生錯誤"))

        finally:
            sys.stdout = old_stdout
            if tmp_wav_path and os.path.exists(tmp_wav_path):
                os.remove(tmp_wav_path)
            self._running = False
            self.root.after(0, lambda: self.start_btn.config(state="normal"))


def main():
    if _DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    SubtitleGenApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
