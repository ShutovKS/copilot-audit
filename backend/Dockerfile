# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
ENV PIP_DEFAULT_TIMEOUT=300
ENV POETRY_HTTP_TIMEOUT=300
ENV POETRY_NO_INTERACTION=1
RUN curl -sSL https://install.python-poetry.org | python3 -

RUN python -m pip install --upgrade pip setuptools wheel

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies to a local folder
RUN poetry config virtualenvs.create false \
    && for i in 1 2 3; do \
        poetry install --no-root --without dev --no-interaction --no-ansi && break || { \
            echo "poetry install failed (attempt $i), retrying..."; \
            sleep $((i * 5)); \
        }; \
    done

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Set env variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy Application Code
COPY src ./src
COPY pyproject.toml .

# Create non-root user for security
RUN useradd -m appuser
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]