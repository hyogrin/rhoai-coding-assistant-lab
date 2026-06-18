FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV SENTENCE_TRANSFORMERS_HOME=/app/models
ENV HF_HOME=/app/models

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY *.py .

ENV DOCS_DIR=/data/docs
ENV EMBED_MODEL=all-MiniLM-L6-v2

RUN chmod -R 777 /app/models

EXPOSE 8000

CMD ["python", "server.py"]
