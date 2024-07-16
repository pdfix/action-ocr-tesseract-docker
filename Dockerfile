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


# Copy the source code and requirements.txt into the container
COPY src/ /usr/tesseract-ocr/src/
COPY requirements.txt /usr/tesseract-ocr/


RUN pip install --no-cache-dir -r requirements.txt 


ENTRYPOINT ["venv/bin/python3", "src/main.py"]
