FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first (cached layer); pinned versions come from requirements.lock.
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

# Then the application package.
COPY pyproject.toml .
COPY src ./src
RUN pip install --no-cache-dir --no-deps .

RUN useradd --create-home --uid 10001 mergeguard
USER mergeguard

EXPOSE 8000
CMD ["uvicorn", "mergeguard.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
