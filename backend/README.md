# TestOps Evolution Forge Backend

## Setup for Development

1. **Install Poetry:**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install Dependencies:**
   ```bash
   poetry install
   ```

3. **Run Server:**
   ```bash
   poetry run uvicorn src.app.main:app --reload
   ```

4. **Linting:**
   ```bash
   poetry run ruff check .
   ```

---

### ✅ Финальная проверка

1.  Запусти сервер: `poetry run uvicorn src.app.main:app --reload`
2.  Должна появиться надпись: `Uvicorn running on http://127.0.0.1:8000`.
3.  Нажми `Ctrl+C` для остановки.

Теперь проект инициализирован идеально. Можем переходить к конфигам (Карточка 1.2).