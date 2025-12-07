# TestOps Forge Backend

Backend-сервис, реализующий логику мульти-агентной системы для генерации тестов.

## Структура проекта

* `src/app/agents/` — Логика агентов (Analyst, Coder) и граф LangGraph.
* `src/app/services/tools/` — Инструменты (Linter, Pytest Runner).
* `src/app/services/parsers/` — Парсеры (OpenAPI/Swagger).
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

## Переменные окружения

| Переменная          | Описание                                |
|---------------------|-----------------------------------------|
| `CLOUD_RU_API_KEY`  | API ключ от Cloud.ru Evolution          |
| `CLOUD_RU_BASE_URL` | Base URL для LLM API                    |
| `MODEL_NAME`        | Модель (например, `Qwen/Qwen2.5-Coder`) |
| `ENVIRONMENT`       | `dev` / `prod`                          |

## Docker Build

```bash
docker build -t testops-backend .
```
