# TestOps Forge Frontend

Клиентское приложение (SPA) на базе React + Vite + Tailwind CSS.

## Особенности UI

*   **Code Editor**: Monaco Editor с поддержкой Python syntax highlighting.
*   **Streaming Logs**: Отображение процесса мышления агента (Terminal).
*   **Source Context**: Загрузка ZIP-архивов и клонирование Git-репозиториев для анализа кода.
*   **Session Management**: Управление сессиями (Account Tab) для сохранения истории.
*   **Evolution UI**: Темная тема в стиле Cloud.ru Console.

## Локальная разработка

1.  **Установка зависимостей:**
    ```bash
    npm install
    ```

2.  **Запуск Dev-сервера:**
    ```bash
    npm run dev
    ```

Приложение будет доступно по адресу: `http://localhost:5173`. API URL настраивается через `VITE_API_URL`.

## Сборка (Production)

```bash
npm run build
```

Результат сборки (`dist/`) раздается через Nginx в Docker-контейнере.
