FROM python:3.11-slim-bookworm as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_HOME="/opt/poetry" \
    PATH="$POETRY_HOME/bin:$PATH" \
    POETRY_NO_INTERACTION=1 \
    POETRY_REQUESTS_TIMEOUT=3000

RUN python -m pip install --upgrade pip \
    && python -m pip install poetry

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --without dev --no-interaction --no-ansi

RUN rm -rf /root/.cache

FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    unzip \
    openjdk-17-jre-headless \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q https://github.com/allure-framework/allure2/releases/download/2.27.0/allure-2.27.0.zip \
    && unzip -q allure-2.27.0.zip -d /opt/ \
    && ln -s /opt/allure-2.27.0/bin/allure /usr/bin/allure \
    && rm allure-2.27.0.zip

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

RUN playwright install chromium

COPY src ./src
COPY pyproject.toml .

RUN mkdir -p /app/static/reports /app/temp_execution \
    && useradd -m appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]