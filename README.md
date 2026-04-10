# VideoSrt — 自動字幕生成工具

從影片自動生成繁體中文 / 英文 / 雙語字幕，支援 **GUI 拖拉操作**與 **CLI 命令列**兩種使用方式。

底層使用 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 進行語音識別，Mac Apple Silicon 另支援 [mlx-whisper](https://github.com/ml-explore/mlx-examples) 硬體加速。

---

## ✨ 主要功能

- **GUI 介面**：拖拉影片即可開始，即時進度條顯示轉錄速度與剩餘時間
- **CLI 介面**：腳本化、批次處理皆適用
- 支援多種影片格式：MP4、MKV、MOV、AVI、WEBM、M4V（H.264 / H.265）
- 輸出格式：`.srt`、`.vtt`，支援繁中、英文、雙語合併
- 簡體中文自動轉繁體（OpenCC）
- 自動偵測 CUDA GPU 加速；Mac M1/M2/M3 自動使用 MLX 加速
- 六種模型大小可選（tiny → large-v3），彈性平衡速度與精準度

---

## 🛠️ 安裝

### 系統需求

- Python 3.8 – 3.12（**請勿使用 3.13 以上**，部分依賴套件尚未支援）
- FFmpeg（需加入系統 PATH）
  - Windows：至 [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) 下載，解壓後將 `bin` 加入 PATH
  - macOS：`brew install ffmpeg`
- （選用）NVIDIA GPU + CUDA Toolkit → 啟用 GPU 加速

### 安裝 Python 套件

```bash
# 建立虛擬環境（建議）
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS / Linux

# 安裝套件
pip install -r requirements.txt
```

> GPU 加速需要支援 CUDA 的 PyTorch，請參考 [PyTorch 官網](https://pytorch.org/get-started/locally/) 安裝對應版本。
> Mac Apple Silicon 使用者不需額外設定，程式會自動切換至 mlx-whisper。

---

## 🖥️ GUI 使用方式（Windows）

雙擊 `launch_gui.bat` 啟動，不會出現黑色 console 視窗。

```
launch_gui.bat
```

或直接執行：

```bash
python gui.py
```

**操作流程：**
1. 將影片拖拉至視窗上方區域（需安裝 `tkinterdnd2`），或點擊選擇影片
2. 確認輸出目錄（預設與影片同目錄）
3. 選擇模型大小、語言、任務類型、輸出格式
4. 按下「▶ 開始生成字幕」

> 安裝 tkinterdnd2 以啟用拖拉功能：`pip install tkinterdnd2`

---

## ⌨️ CLI 使用方式

```bash
# 基本：生成繁中字幕
python subtitle_gen.py --input video.mp4

# 同時輸出繁中 + 英文雙語字幕
python subtitle_gen.py --input video.mp4 --task both

# 指定高精準模型，同時輸出 SRT 與 VTT
python subtitle_gen.py --input video.mp4 --model large-v2 --format srt vtt

# 強制 CPU，指定語言為日文
python subtitle_gen.py --input video.mp4 --device cpu --lang ja
```

---

## ⚙️ CLI 參數清單

| 參數 | 縮寫 | 預設值 | 說明 |
|------|------|--------|------|
| `--input` | `-i` | **(必填)** | 輸入影片路徑 |
| `--output` | `-o` | 影片同目錄 | 字幕輸出目錄 |
| `--model` | `-m` | `medium` | 模型大小：`tiny` / `base` / `small` / `medium` / `large-v2` / `large-v3` |
| `--lang` | `-l` | 自動偵測 | 語言代碼：`zh`、`en`、`ja` … |
| `--task` | `-t` | `transcribe` | `transcribe` 轉錄 / `translate` 翻譯成英文 / `both` 雙語 |
| `--format` | `-f` | `srt` | 輸出格式（可複選）：`srt`、`vtt` |
| `--device` | `-d` | `auto` | `auto` / `cuda` / `cpu` |
| `--beam-size` | | `5` | Beam search 大小，越大越精準但越慢 |
| `--no-trad` | | — | 停用簡轉繁，保留 Whisper 原始輸出 |

---

## 📁 輸出檔案命名

以輸入檔 `video.mp4` 為例：

| 任務 | 輸出檔案 |
|------|----------|
| `transcribe` | `video.zh.srt` |
| `translate` | `video.en.srt` |
| `both` | `video.zh.srt`、`video.en.srt`、`video.bilingual.srt` |
