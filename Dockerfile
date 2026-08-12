# syntax=docker/dockerfile:1
FROM python:3.14-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
COPY schema ./schema

RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.14-slim

RUN useradd --create-home --uid 1000 ledger
COPY --from=builder /install /usr/local

WORKDIR /app
COPY schema ./schema

ENV LEDGER_DATA_DIR=/data \
    LEDGER_HOST=0.0.0.0 \
    LEDGER_PORT=8420 \
    PYTHONUNBUFFERED=1

RUN mkdir -p /data && chown ledger:ledger /data
VOLUME ["/data"]
USER ledger

EXPOSE 8420

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8420/healthz', timeout=3)" || exit 1

ENTRYPOINT ["ledger"]
CMD ["serve"]
