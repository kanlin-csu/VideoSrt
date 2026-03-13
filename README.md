# Movie2Str (自動字幕生成工具)

這是一個基於命令列 (CLI) 的自動字幕生成工具，使用 `faster-whisper` 進行高精準度且快速的語音識別。它可以從影片中提取音訊、自動生成字幕，並支援輸出繁體中文、英文，甚至是中英雙語字幕。

## ✨ 主要功能

- 支援多種影片格式（MP4, MKV, MOV, AVI, WEBM, M4V 包含 H.264 / H.265 編碼）。
- 自動將簡體中文轉換為**繁體中文**（使用 OpenCC）。
- 支援翻譯功能，可將外語直接翻譯成英文。
- 支援**中英雙語**字幕輸出。
- 支援輸出 `.srt` 與 `.vtt` 兩種常見字幕格式。
- 自動偵測 GPU (CUDA) 加速，若無 GPU 則會退回使用 CPU 進行運算。
- 提供多種 Whisper 模型大小選擇 (tiny 到 large-v3)，可根據電腦硬體效能自由調整。

---

## 🛠️ 安裝說明

### 系統必備條件

1. **Python 3.8+** 或更新版本。
2. **FFmpeg**：
   - 本程式需要調用系統底層的三方工具 FFmpeg 進行音訊提取。
   - **Windows 安裝方式**：可以從 [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) 或 [BtbN](https://github.com/BtbN/FFmpeg-Builds/releases) 下載編譯好的執行檔，並將 `bin` 資料夾加入到系統的環境變數 `Path` 中。
   - **macOS (Mac) 安裝方式**：強烈建議使用 [Homebrew](https://brew.sh/) 進行安裝。在您的終端機中輸入以下指令：
     ```bash
     brew install ffmpeg
     ```
3. **NVIDIA GPU 驅動與 CUDA (選用，僅限 Windows / Linux)**：若要使用 GPU 加速，請確保電腦已安裝相對應的 NVIDIA 驅動程式與 CUDA Toolkit。
   - **Mac 用戶注意**：Apple Silicon (M1/M2/M3 等) 及絕大多數 Mac 機型**不支援** CUDA。腳本在執行時會自動轉向 CPU 運算，`faster-whisper` 在 Mac 的 CPU 上也有相當出色的執行效率。

### 安裝 Python 套件

建議使用虛擬環境 (如 `venv` 或 `conda`) 來避免套件衝突：

```bash
# 建立並啟用虛擬環境 (選用)
python -m venv venv
venv\Scripts\activate

# 安裝依賴套件
pip install -r requirements.txt
```

> **注意：** 若要啟動 GPU 運算，確保環境中的 PyTorch 支援 CUDA。可以參考 [PyTorch 官方網站](https://pytorch.org/get-started/locally/) 進行具體安裝（例如：`pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118` 或對應版本）。

---

## 🚀 使用說明

基本使用方式非常簡單，只需指定輸入影片檔案即可：

### 1. 基本範例 (預設生成繁中字幕)
```bash
python subtitle_gen.py --input video.mp4
```
這會在 `video.mp4` 所在的目錄下，產生 `video.zh.srt` 繁體中文字幕檔。

### 2. 輸出中英雙語字幕
```bash
python subtitle_gen.py --input video.mp4 --task both
```
這會同時辨識原始語言 (繁中) 與翻譯語言 (英文)，並匯出 `video.bilingual.srt` 雙語字幕，以及獨立的中文與英文字幕。

### 3. 指定高精準度模型與輸出格式
若您的顯示卡 VRAM 足夠且需要更高的辨識精準度，可以使用 `large-v2` 或 `large-v3` 模型，同時輸出 `srt` 與 `vtt` 格式：
```bash
python subtitle_gen.py --input video.mp4 --model large-v2 --format srt vtt
```
*(注意：`large-v2` 模型約需 5.5GB 以上的 VRAM，`medium` 預設模型則約需 3GB。)*

### 4. 強制使用 CPU 運算並指定語言
```bash
python subtitle_gen.py --input video.mp4 --device cpu --lang ja
```

---

## ⚙️ 詳細參數清單

| 參數 | 縮寫 | 預設值 | 說明 |
| --- | --- | --- | --- |
| `--input` | `-i` | **(必填)** | 輸入影片路徑 (如：`.mp4`, `.mkv`) |
| `--output` | `-o` | 影片同目錄 | 指定字幕的輸出目錄 |
| `--model` | `-m` | `medium` | Whisper 模型大小 (`tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3`) |
| `--lang` | `-l` | (自動偵測) | 影片語言代碼 (如：`zh` 簡中/繁中, `en` 英文, `ja` 日文) |
| `--task` | `-t` | `transcribe` | 任務類型：<br> `transcribe` (轉錄原本語言)<br> `translate` (翻譯為英文)<br> `both` (同時執行轉錄與翻譯) |
| `--format` | `-f` | `srt` | 輸出字幕格式 (可複選 `srt`, `vtt`) |
| `--device` | `-d` | `auto` | 運算裝置：`auto` (自動偵測CUDA), `cuda` (GPU), `cpu` |
| `--beam-size` | | `5` | Beam search 的大小，數值越大越精準但較吃資源與時間 |
| `--no-trad` | | `False` | 加上此參數時，**停止**自動將結果轉換為繁體中文 |

## 📁 輸出檔案命名規則

程式將會根據你的選項輸出以下檔案格式（假設輸入檔案名為 `video.mp4`）：
- `video.zh.srt` (中文版單語字幕)
- `video.en.srt` (英文版單語字幕)
- `video.bilingual.srt` (中英雙語字幕 - 當 `task` 為 `both` 時)
