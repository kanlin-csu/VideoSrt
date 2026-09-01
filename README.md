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

## 🐳 Docker 容器執行（NVIDIA GPU）

不想在主機上處理 CUDA / cuDNN 版本問題時，可以把語音識別放進容器跑。
容器只跑 **CLI**（`subtitle_gen.py`）；GUI 仍在主機端執行。

### 需求

- NVIDIA GPU + 主機驅動（Windows 使用者裝 Windows 版驅動即可，**WSL 內不必另裝驅動**）
- Docker Engine
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)，並執行過
  `sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`

驗證 GPU 有掛進容器：

```bash
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi
```

### 建置

```bash
docker build -t videosrt:gpu docker/
```

> build context 刻意指向 `docker/` 而非專案根目錄，避開 `venv/`、`models/`、
> `VIDEO/` 等數 GB 的檔案。base image 為 `nvidia/cuda:12.8.0-cudnn-runtime`，
> 已內含 CUDA 12.8 + cuDNN 9，正好對上 CTranslate2 4.8.x 的需求，
> 因此容器內不必再從 PyPI 下載 `nvidia-cudnn-cu12`。

### 執行

專案目錄與 `models/` 是以 bind-mount 掛進容器的，因此**改 `modules/` 不必重新 build**，
下載過的模型也直接沿用、不會重抓。

```bash
# WSL / Linux
docker/vsrt.sh VIDEO/影片.mp4 --model large-v3
docker/vsrt.sh --input VIDEO/影片.mp4 --task both --format srt vtt

# Windows PowerShell（轉呼叫 WSL，Windows 路徑可直接傳）
.\docker\vsrt.ps1 VIDEO\影片.mp4 --model large-v3
.\docker\vsrt.ps1 --input D:\影片\上課.mp4 --output D:\輸出
```

CLI 參數與主機版完全相同，見上一節。

不用包裝腳本、直接下 `docker run` 也可以：

```bash
docker run --rm -t --gpus all \
    -v /path/to/VideoSrt:/app -w /app \
    videosrt:gpu --input VIDEO/影片.mp4 --model large-v3
```

### 包裝腳本的環境變數

| 變數 | 預設 | 說明 |
|------|------|------|
| `VSRT_IMAGE` | `videosrt:gpu` | 改用其他 image 標籤 |
| `VSRT_GPU` | `1` | 設 `0` 停用 `--gpus all`，強制純 CPU |
| `VSRT_DISTRO` | `kali-linux` | 僅 `vsrt.ps1`：指定 WSL 發行版 |

### 路徑處理

`vsrt.sh` 會自動轉換路徑，不必自己算容器內位置：

- Windows 路徑（`D:\ai\...`）自動轉成 WSL 路徑
- 專案目錄內的檔案 → `/app/...`
- 專案目錄外的**輸入檔** → 其所在資料夾掛到 `/input`
  （可寫，因為沒給 `--output` 時字幕預設就輸出到影片旁邊）
- 專案目錄外的**輸出目錄** → 以可寫掛到 `/output`

### 已知取捨

- **每次執行都要重新載入模型**。large-v3 從 Windows 磁碟經 9p 讀進來約 14 秒，
  另外 Blackwell（sm_120）首次推論有約 40 秒的 JIT 編譯。要批次處理多支影片時，
  用一次 `docker run` 跑完會比每支各開一個容器划算。
- 暫存 WAV 寫在容器內的 `/tmp`，不會落到掛載的磁碟上。
- 容器以 root 執行。輸出寫到 Windows 磁碟（drvfs）沒有權限問題；
  若把專案放在 WSL 原生檔案系統，產出的檔案會是 root 所有。

---

## 📁 輸出檔案命名

以輸入檔 `video.mp4` 為例：

| 任務 | 輸出檔案 |
|------|----------|
| `transcribe` | `video.zh.srt` |
| `translate` | `video.en.srt` |
| `both` | `video.zh.srt`、`video.en.srt`、`video.bilingual.srt` |
