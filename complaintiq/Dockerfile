FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
# EXTRAS=data,serve keeps the image small (hashing embedder). For real models use EXTRAS=data,serve,embed
ARG EXTRAS=data,serve
RUN pip install ".[${EXTRAS}]"
COPY scripts ./scripts
RUN chmod +x scripts/entrypoint.sh && useradd -m app && mkdir -p /app/data /app/artifacts && chown -R app /app
USER app
EXPOSE 8000 7860
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,os;urllib.request.urlopen('http://localhost:%s/health'%os.getenv('PORT','8000'))" || exit 1
ENTRYPOINT ["./scripts/entrypoint.sh"]
