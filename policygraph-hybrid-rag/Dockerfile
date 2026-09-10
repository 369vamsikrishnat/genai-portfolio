FROM python:3.11-slim

WORKDIR /app

COPY . .

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

EXPOSE 8000
EXPOSE 8501

CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]