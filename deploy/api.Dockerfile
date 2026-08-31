FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system --gid 10001 lifelenz \
    && useradd --system --uid 10001 --gid lifelenz --home-dir /nonexistent --shell /usr/sbin/nologin lifelenz

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY deploy/sqlite_maintenance.py ./deploy/sqlite_maintenance.py

RUN python -m pip install . \
    && install -d -o lifelenz -g lifelenz /var/lib/lifelenz

USER lifelenz

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2).read()" || exit 1

CMD ["python", "-m", "uvicorn", "lifelenz.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
