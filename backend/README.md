# TestOps Forge Backend

Backend-сервис, реализующий логику мульти-агентной системы для генерации тестов.

## Возможности API

* **SSE Streaming**: `/api/v1/generate` отдает логи и код в реальном времени.
* **Code Analysis**:
  * `/api/v1/analyze-source` (ZIP Upload)
  * `/api/v1/analyze-git` (Git Clone)
  * Поддержка: Python (FastAPI), Java (Spring), Node.js (NestJS, Express).
* **RBAC**: Все запросы требуют заголовок `X-Session-ID`.

## Структура проекта

* `src/app/agents/` — Логика агентов (Analyst, Coder, Reviewer).
* `src/app/services/code_analysis/` — Парсеры исходного кода (AST/Regex).
* `src/app/services/tools/` — Инструменты валидации (Strict Allure Linter).
* `src/app/api/` — FastAPI эндпоинты.

## Локальная разработка

1. **Установка зависимостей (Poetry):**

   ```bash
   poetry install
   ```

2. **Запуск сервера:**

   ```bash
   poetry run uvicorn src.app.main:app --reload
   ```

3. **Запуск тестов:**

   ```bash
   poetry run pytest
   ```

## Миграции БД

При старте приложения (`main.py`) выполняется автоматическая проверка схемы и создание таблицы `test_runs` с поддержкой `session_id`.

## Переменные окружения

| Переменная          | Описание                                |
|---------------------|-----------------------------------------|
| `CLOUD_RU_API_KEY`  | API ключ от Cloud.ru Evolution          |
| `CLOUD_RU_BASE_URL` | Base URL для LLM API                    |
| `MODEL_NAME`        | Модель (например, `Qwen/Qwen2.5-Coder`) |
| `DATABASE_URL`      | PostgreSQL Connection String            |
