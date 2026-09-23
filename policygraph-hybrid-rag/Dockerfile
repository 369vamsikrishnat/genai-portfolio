FROM python:3.11-slim

WORKDIR /app

# System dependency required by pytesseract
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Create non-root runtime user
RUN useradd -m appuser

# Ensure Hugging Face cache lives under /app so it remains available after USER appuser.
ENV HF_HOME=/app/.cache/huggingface

# Copy application
COPY . .

# Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    slowapi \
    pydantic \
    requests \
    streamlit \
    google-genai \
    langfuse \
    sentence-transformers \
    rank-bm25 \
    psycopg2-binary \
    pgvector \
    pymupdf \
    pytesseract \
    python-dotenv

# Warm both embedding models into the image to reduce Cloud Run cold starts
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('BAAI/bge-base-en-v1.5'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

RUN chown -R appuser /app

USER appuser

EXPOSE 8000
EXPOSE 8501

CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]