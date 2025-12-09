# TestOps Evolution Forge

**TestOps Evolution Forge** — это интеллектуальная агентная система на базе **Cloud.ru Evolution Foundation Model** для автоматической генерации валидных E2E и API тестов.

## 🚀 Ключевые возможности

*   **🤖 Multi-Agent Workflow**: Оркестрация агентов (Analyst, Coder, Reviewer) через LangGraph. Агенты сами проверяют и исправляют свой код.
*   **🛡️ Strict Quality Gate**: Гарантия валидности. Код не отдается пользователю, пока не пройдет AST-валидацию и `pytest --collect-only`. Строгое соблюдение Allure-декораторов.
*   **🔍 Code Analysis (White-Box)**: Парсинг исходного кода (Python FastAPI, Java Spring, JS/TS NestJS/Express) из **ZIP-архивов** или **Git-репозиториев** для генерации точных тестов.
*   **🔐 Private Git Support**: Безопасная работа с приватными репозиториями через Access Tokens.
*   **👥 Session Isolation**: Многопользовательский режим с разделением истории через уникальные Session Keys.
*   **🧠 RAG & Deduplication**: Поиск похожих тестов в векторной базе (ChromaDB) для предотвращения дублей.

## 🛠 Технологии

*   **Backend**: Python 3.11, FastAPI, LangGraph, Pydantic V2, AST, SQLAlchemy (Async).
*   **LLM**: Cloud.ru Evolution (OpenAI-compatible API).
*   **Frontend**: React 18, Vite, Tailwind CSS, Monaco Editor.
*   **Infrastructure**: Docker Compose, PostgreSQL, ChromaDB.

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

3.  **Использование**
    *   Зайдите на Frontend.
    *   Введите описание теста или загрузите код (ZIP/Git).
    *   Получите готовый Pytest код с Allure-отчетами.

## 🧪 Тестирование (Quality Gate)

Проект покрыт unit-тестами (Backend):
```bash
cd backend
poetry run pytest
```

## 🏗 Архитектура

Система построена на принципах **Clean Architecture**:
*   `src/app/core`: Конфигурация и миграции.
*   `src/app/domain`: Pydantic модели и стейт агентов.
*   `src/app/services`: Бизнес-логика (LLM, Code Parsers, Git Service, Linter).
*   `src/app/agents`: Граф LangGraph и промпты.
*   `src/app/api`: REST API контроллеры.
