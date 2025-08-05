FROM python:3.12-slim-bullseye AS builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
    libpango-1.0-0 libpangoft2-1.0-0 \
    libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt .

RUN pip cache purge && \
    pip install --no-cache-dir --upgrade pip

# Asegúrate de que transformers y torch se instalan ANTES de las otras dependencias
RUN pip install --no-cache-dir torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir transformers==4.42.1

# Desinstalamos y reinstalamos OpenAI y httpx para asegurar la última versión y compatibilidad
RUN pip uninstall -y openai httpx && \
    pip install --no-cache-dir --default-timeout 1000 -r requirements.txt && \
    pip install --no-cache-dir --upgrade openai httpx

FROM python:3.12-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
    libpango-1.0-0 libpangoft2-1.0-0 \
    libpq5 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --group app

COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY wait-for-it.sh /usr/local/bin/wait-for-it.sh
RUN chmod +x /usr/local/bin/wait-for-it.sh

COPY --chown=app:app . .

RUN chmod +x /app/start.sh

USER app

ENV PORT 5001
EXPOSE 5001

CMD ["/app/start.sh"]