# TestOps Evolution Forge

**TestOps Evolution Forge** — это интеллектуальная агентная система на базе **Cloud.ru Evolution Foundation Model** для автоматической генерации валидных E2E и API тестов.

## 🚀 Ключевые возможности

*   **Multi-Agent Workflow**: Оркестрация агентов (Analyst, Coder, Reviewer) через LangGraph.
*   **Self-Correction Loop**: Гарантия валидности кода. Агент не отдает результат, пока он не пройдет статический анализ и проверку `pytest`.
*   **Smart Context**: Умный парсинг OpenAPI (Swagger) с фильтрацией эндпоинтов под запрос пользователя.
*   **RAG & Deduplication**: Поиск похожих тестов в векторной базе (ChromaDB) для предотвращения дублей.
*   **Defect Awareness**: Учет исторических дефектов при генерации тест-плана.

## 🛠 Технологии

*   **Backend**: Python 3.11, FastAPI, LangGraph, Pydantic V2.
*   **LLM**: Cloud.ru Evolution (OpenAI-compatible API).
*   **Validation**: Ruff, Pytest, AST.
*   **Frontend**: React 18, Monaco Editor, Tailwind CSS.
*   **Infrastructure**: Docker Compose.

## 🏃‍♂️ Быстрый старт

1.  **Настройка окружения**
    Создайте файл `backend/.env`:
    ```ini
    CLOUD_RU_API_KEY=your_key
    CLOUD_RU_BASE_URL=https://foundation-models.api.cloud.ru/v1
    MODEL_NAME=Qwen/Qwen2.5-Coder-32B-Instruct
    ```

2.  **Запуск в Docker**
    ```bash
    docker-compose up --build -d
    ```
    *   Frontend: [http://localhost:3000](http://localhost:3000)
    *   Backend Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

3.  **Локальная разработка (Backend)**
    ```bash
    cd backend
    poetry install
    poetry run pytest  # Запуск тестов
    poetry run uvicorn src.app.main:app --reload
    ```

## 🧪 Тестирование (Quality Gate)

Проект покрыт unit-тестами на **83%**.
Для запуска проверки покрытия:
```bash
cd backend
poetry run pytest --cov=src
```

## 🏗 Архитектура

Система построена на принципах **Clean Architecture**:
*   `src/app/core`: Конфигурация и настройки.
*   `src/app/domain`: Pydantic модели и стейт агентов.
*   `src/app/services`: Бизнес-логика (LLM, Parsers, Linter, Deduplication, Defects).
*   `src/app/agents`: Граф LangGraph и промпты.
*   `src/app/api`: REST API контроллеры.
