# Use the official Debian slim image as a base
FROM debian:stable-slim

# Install Tesseract OCR and necessary dependencies
RUN apt-get update && \
    apt-get install -y \
    tesseract-ocr-all \
    python3 \
    python3-pip \
    python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/tesseract-ocr/

ENV VIRTUAL_ENV=venv

# Create a virtual environment and install dependencies
RUN python3 -m venv venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy and install dependencies into the container
COPY requirements.txt /usr/tesseract-ocr/
RUN pip install --no-cache-dir -r requirements.txt 

# Copy sources and resources
COPY config.json /usr/tesseract-ocr/
COPY src/ /usr/tesseract-ocr/src/

ENTRYPOINT ["/usr/tesseract-ocr/venv/bin/python3", "/usr/tesseract-ocr/src/main.py"]
