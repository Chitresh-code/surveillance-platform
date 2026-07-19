FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY services/common /app/services/common
COPY services/retention /app/services/retention
WORKDIR /app/services/retention

RUN uv sync --no-dev --frozen

CMD ["uv", "run", "python", "-m", "retention.main"]
