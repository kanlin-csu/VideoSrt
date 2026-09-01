# VideoSrt CLI 容器（NVIDIA GPU）
#
# base image 已內含 CUDA 12.8 runtime + cuDNN 9，正好對上 CTranslate2 4.8.x
# 的需求，因此 pip 端不必再裝 nvidia-cublas-cu12 / nvidia-cudnn-cu12。
#
# 建置（context 指向 docker/，避開專案內 venv、models、VIDEO 等數 GB 的檔案）：
#   docker build -t videosrt:gpu docker/
FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    HF_HUB_DISABLE_TELEMETRY=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Ubuntu 24.04 的系統 Python 受 PEP 668 保護，不能直接 pip 裝，走 venv
RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

COPY requirements-docker.txt /tmp/requirements-docker.txt
RUN pip install --no-cache-dir -r /tmp/requirements-docker.txt

# 程式碼與模型由外部 bind-mount 進來（見 vsrt.sh），不燒進 image，
# 這樣改 modules/ 不必重新 build。
WORKDIR /app

ENTRYPOINT ["python", "subtitle_gen.py"]
CMD ["--help"]
