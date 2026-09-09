FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# FFmpeg is used for actual media identification, decoding and conversion.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg nano \
    && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

COPY pyproject.toml README.md uv.lock* ./

RUN uv sync --no-dev

COPY src ./src
COPY scripts ./scripts
COPY entrypoint.sh ./entrypoint.sh

RUN chmod +x ./entrypoint.sh

# Runtime cache directory.
RUN mkdir -p /app/.cache/models

ENV PATH="/app/.venv/bin:$PATH" \
    MODEL_CACHE_DIR="/app/.cache/models"

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]