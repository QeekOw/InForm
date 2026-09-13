# Dockerfile for InForm Donut OCR Engine (Open-Source Self-Hosted)
# Builds a production-ready Gradio/REST server for live Donut inference.
# Checkpoint is fetched from Hugging Face Hub (QeeeeK/donut-inbody).

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=7860 \
    HOST=0.0.0.0 \
    INFORM_DONUT_CKPT="QeeeeK/donut-inbody"

WORKDIR /app

# Install git and system runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py /app/app.py
COPY README.md /app/README.md

# Non-root user for security (standard Hugging Face & Cloud Run UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

EXPOSE 7860

CMD ["python", "app.py"]
