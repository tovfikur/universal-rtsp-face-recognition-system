FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libboost-all-dev \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install CUDA-enabled PyTorch wheels (defaults compatible with CUDA 12.1+ drivers)
ARG TORCH_VERSION=2.4.1
ARG TORCHVISION_VERSION=0.19.1
ARG TORCHAUDIO_VERSION=2.4.1
ARG TORCH_CUDA_TAG=cu121
RUN pip install --no-cache-dir \
    torch==${TORCH_VERSION}+${TORCH_CUDA_TAG} \
    torchvision==${TORCHVISION_VERSION}+${TORCH_CUDA_TAG} \
    torchaudio==${TORCHAUDIO_VERSION}+${TORCH_CUDA_TAG} \
    --extra-index-url https://download.pytorch.org/whl/${TORCH_CUDA_TAG}

COPY backend /app/backend
COPY frontend /app/frontend

RUN mkdir -p /app/backend/data /app/backend/faces

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "app:app"]
