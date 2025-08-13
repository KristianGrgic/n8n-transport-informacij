FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY pdf_extractor_clean.py .

RUN mkdir -p /tmp/pdf_parser

RUN python -c "from docling import DocumentConverter; converter = DocumentConverter(); print('Models preloaded')"

EXPOSE 8080

RUN pip install gunicorn

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 120 app:app