FROM python:3.12-slim-bookworm

WORKDIR /app

# Docker CLI для docker exec в контейнер amnezia-awg2 на хосте
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY VERSION .
COPY bot/ bot/

RUN mkdir -p /app/data

ENV DATABASE_PATH=/app/data/bot.db
ENV PYTHONUNBUFFERED=1
# docker.io из Debian старее демона на хосте (Docker 29+ требует API ≥ 1.40)
ENV DOCKER_API_VERSION=1.44

CMD ["python", "-m", "bot.main"]
