FROM python:3.12-slim-bookworm

# uv — быстрый менеджер зависимостей (берём бинарь из официального образа)
COPY --from=ghcr.io/astral-sh/uv:0.11.25 /uv /uvx /bin/

WORKDIR /app

# Docker CLI для docker exec в контейнер amnezia-awg2 на хосте
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Сначала только манифесты — слой с зависимостями кэшируется между сборками
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY VERSION .
COPY bot/ bot/

RUN mkdir -p /app/data

ENV PATH="/app/.venv/bin:$PATH" \
    DATABASE_PATH=/app/data/bot.db \
    PYTHONUNBUFFERED=1 \
    # docker.io из Debian старее демона на хосте (Docker 29+ требует API ≥ 1.40)
    DOCKER_API_VERSION=1.44

CMD ["python", "-m", "bot.main"]
