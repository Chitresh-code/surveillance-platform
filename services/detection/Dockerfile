FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY services/common /app/services/common
COPY services/detection /app/services/detection
WORKDIR /app/services/detection

RUN uv sync --no-dev --frozen

CMD ["uv", "run", "python", "-m", "detection.main"]
