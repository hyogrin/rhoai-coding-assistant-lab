FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV SENTENCE_TRANSFORMERS_HOME=/app/models
ENV HF_HOME=/app/models

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY *.py .

ENV SOURCE_DIR=/data/source
ENV EMBED_MODEL=all-MiniLM-L6-v2

RUN chmod -R 777 /app/models

EXPOSE 8000

CMD ["python", "server.py"]
