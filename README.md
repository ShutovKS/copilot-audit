# TestOps Evolution Forge

**TestOps Evolution Forge** — это агентная система на базе **Cloud.ru Evolution Foundation Model**, предназначенная для автоматической генерации валидных автотестов (UI & API).

## 🚀 Основные возможности

*   **Multi-Agent Architecture**: Система из трех агентов (Analyst, Coder, Reviewer) на базе LangGraph.
*   **Self-Correction Loop**: Код не отдается пользователю, пока не пройдет валидацию (linter + pytest collection).
*   **Smart Swagger Parsing**: Умный разбор OpenAPI спецификаций для экономии контекста LLM.
*   **Evolution UI**: Современный интерфейс в стилистике платформы Cloud.ru.
*   **Streaming Logs**: Отображение "мыслей" агента в реальном времени через SSE.

## 🛠 Технологический стек

### Backend
*   **Python 3.11** + **FastAPI** (Async REST API + SSE)
*   **LangGraph** + **LangChain** (Оркестрация агентов)
*   **Pytest** + **Ruff** (Валидация кода)
*   **Docker** (Multistage build < 700MB)

### Frontend
*   **React 18** + **Vite** + **TypeScript**
*   **Monaco Editor** (Редактор кода как в VS Code)
*   **Tailwind CSS v4** (Стилизация под Cloud.ru)
*   **Zustand** (State Management)

## 🏃‍♂️ Быстрый старт (Docker)

Запустить весь проект одной командой:

```bash
docker-compose up --build -d
```

После запуска:
*   🖥 **Frontend**: [http://localhost:3000](http://localhost:3000)
*   ⚙️ **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🏗 Архитектура

1.  **Analyst Agent**: Принимает запрос (текст или Swagger URL), составляет план тестирования.
2.  **Coder Agent**: Генерирует Python код (Pytest + Playwright/Requests) по паттерну AAA.
3.  **Reviewer Agent**: Запускает код в изолированной среде. Если есть ошибки — возвращает Coder'у на доработку.

## 🔐 Конфигурация

Создайте файл `backend/.env` (см. `backend/.env.example`):

```ini
CLOUD_RU_API_KEY=your_key_here
CLOUD_RU_BASE_URL=https://foundation-models.api.cloud.ru/v1
MODEL_NAME=Qwen/Qwen2.5-Coder-32B-Instruct
```

## 📸 Скриншоты

*(Место для скриншотов интерфейса)*
