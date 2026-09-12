FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    FLREDDIT_DB=/data/flreddit.sqlite3

WORKDIR /app

RUN groupadd --system flreddit && useradd --system --gid flreddit --home /app flreddit

COPY pyproject.toml README.md LICENSE ./
COPY flreddit ./flreddit
RUN pip install --no-cache-dir .

COPY site ./site
RUN mkdir -p /data && chown -R flreddit:flreddit /app /data

USER flreddit
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/health', timeout=3)"

CMD ["python", "-m", "flreddit"]
