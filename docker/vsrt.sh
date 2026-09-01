#!/usr/bin/env bash
#
# vsrt.sh — 在 GPU 容器裡跑 VideoSrt 的 CLI（subtitle_gen.py）
#
# 用法（在 WSL 裡）：
#   docker/vsrt.sh VIDEO/影片.mp4 --model large-v3
#   docker/vsrt.sh --input VIDEO/影片.mp4 --task both --format srt vtt
#   docker/vsrt.sh --help
#
# 路徑處理：
#   - 接受 Windows 路徑（D:\ai\...）或 WSL 路徑，會自動轉換
#   - 專案目錄內的檔案直接經 /app 存取
#   - 專案目錄外的輸入檔，其所在資料夾會以唯讀掛到 /input
#   - 專案目錄外的輸出目錄會以可寫掛到 /output
#
# 環境變數：
#   VSRT_IMAGE  自訂 image 名稱（預設 videosrt:gpu）
#   VSRT_GPU=0  停用 GPU，強制純 CPU 跑
set -euo pipefail

IMAGE="${VSRT_IMAGE:-videosrt:gpu}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

BS='\'   # 反斜線，獨立成變數以免在各層轉義中被吃掉

# ── Windows 路徑 → WSL 路徑 ────────────────────────────────
# 判斷依據是開頭的「單一字母 + 冒號」，不去猜分隔符，
# D:\ai\x 與 D:/ai/x 都吃得下。
to_wsl_path() {
    local p="$1"
    local first="${p:0:1}" second="${p:1:1}"
    if [[ "$second" == ":" && "$first" =~ ^[A-Za-z]$ ]]; then
        local drive rest
        drive="$(printf '%s' "$first" | tr 'A-Z' 'a-z')"
        rest="${p:2}"
        rest="${rest//"$BS"//}"          # 反斜線一律換成正斜線
        rest="${rest#/}"                 # 去掉開頭多餘的斜線
        printf '/mnt/%s/%s' "$drive" "$rest"
    else
        printf '%s' "$p"
    fi
}

# 主機路徑 → 容器內路徑；順便登記需要的額外掛載。
#
# 結果放在全域 MAPPED 而不是用 stdout 回傳：這兩個函式會往 EXTRA_MOUNTS
# 累加，若透過 $( ) 取值就會跑在子 shell 裡，掛載參數會整個遺失。
declare -a EXTRA_MOUNTS=()
MAPPED=""
IN_MOUNTED=0
OUT_MOUNTED=0

map_input() {
    local host abs dir base
    host="$(to_wsl_path "$1")"
    dir="$(dirname "$host")"
    base="$(basename "$host")"
    dir="$(cd "$dir" 2>/dev/null && pwd)" || dir="$(dirname "$host")"
    abs="$dir/$base"
    if [[ "$abs" == "$PROJECT_DIR"/* ]]; then
        MAPPED="/app/${abs#"$PROJECT_DIR"/}"
        return
    fi
    # 掛成可寫：CLI 預設把字幕輸出到影片旁邊，唯讀會讓沒給 --output 的情況直接失敗
    if [[ $IN_MOUNTED -eq 0 ]]; then
        EXTRA_MOUNTS+=(-v "$dir:/input")
        IN_MOUNTED=1
    fi
    MAPPED="/input/$base"
}

map_output_dir() {
    local host abs
    host="$(to_wsl_path "$1")"
    abs="$(cd "$host" 2>/dev/null && pwd)" || abs="$host"
    if [[ "$abs" == "$PROJECT_DIR" ]]; then
        MAPPED="/app"
        return
    fi
    if [[ "$abs" == "$PROJECT_DIR"/* ]]; then
        MAPPED="/app/${abs#"$PROJECT_DIR"/}"
        return
    fi
    if [[ $OUT_MOUNTED -eq 0 ]]; then
        EXTRA_MOUNTS+=(-v "$abs:/output")
        OUT_MOUNTED=1
    fi
    MAPPED="/output"
}

# ── 改寫參數 ───────────────────────────────────────────────
declare -a ARGS=()
# 第一個參數若不是選項，視為輸入檔（vsrt.sh video.mp4 的簡寫）
if [[ $# -gt 0 && "$1" != -* ]]; then
    map_input "$1";           ARGS+=(--input "$MAPPED")
    shift
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        -i|--input)  map_input "$2";           ARGS+=("$1" "$MAPPED");        shift 2 ;;
        --input=*)   map_input "${1#*=}";      ARGS+=("--input=$MAPPED");     shift   ;;
        -o|--output) map_output_dir "$2";      ARGS+=("$1" "$MAPPED");        shift 2 ;;
        --output=*)  map_output_dir "${1#*=}"; ARGS+=("--output=$MAPPED");    shift   ;;
        *)           ARGS+=("$1");                                           shift   ;;
    esac
done

# ── 組 docker run ──────────────────────────────────────────
declare -a DOCKER_OPTS=(--rm)
[[ "${VSRT_GPU:-1}" != "0" ]] && DOCKER_OPTS+=(--gpus all)
# 有終端機才給 -t，讓 tqdm 進度條正常顯示；被導向檔案時不給，避免控制碼
[[ -t 1 ]] && DOCKER_OPTS+=(-t)

exec docker run "${DOCKER_OPTS[@]}" \
    -v "$PROJECT_DIR:/app" \
    "${EXTRA_MOUNTS[@]+"${EXTRA_MOUNTS[@]}"}" \
    -w /app \
    "$IMAGE" "${ARGS[@]+"${ARGS[@]}"}"
