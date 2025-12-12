# TestOps Evolution Forge - AI Coding Agent Instructions

## Project Overview
TestOps Evolution Forge is an autonomous AI agent system for test generation and asynchronous execution using Cloud.ru Evolution LLMs, **Celery** for task queuing, and **Redis** for message brokering and real-time log streaming. The system uses **LangGraph** for agent orchestration, Playwright for browser automation, and FastAPI + React for the interface.

## Architecture

### LangGraph Agent Flow
The core is a state machine in [backend/src/app/agents/graph.py](../backend/src/app/agents/graph.py):
- **router** → classifies requests (ui_test_gen, debug_request, api_test_gen)
- **analyst** → creates test plans, uses WebInspector for DOM extraction
- **batch** → handles multi-scenario generation
- **coder** → generates Playwright test code
- **reviewer** → runs [CodeValidator](../backend/src/app/services/tools/linter.py) for security/quality
- **final_output** → saves to database and **queues test execution in Celery**

Routing logic: Debug requests bypass analyst and go directly to coder with `status=FIXING`.

### State Management
- **Backend**: `AgentState` (domain/state.py) tracks: messages, status, attempts, validation_error, logs, test_plan, scenarios
- **Frontend**: Zustand store (entities/store.ts) manages: sessionId, generatedCode, chatMessages, editorSettings
- Session persistence uses LangGraph checkpointer with PostgreSQL

### Key Services
- **TestExecutorService** (services/executor.py): Runs within a Celery worker, spins up Docker containers (`testops-runner:latest`) to execute tests in isolation.
- **WebInspector** (services/tools/browser.py): Playwright-based DOM scraping for Active Vision feature
- **CodeValidator** (services/tools/linter.py): AST-based validation enforcing banned imports (`os`, `subprocess`), Allure compliance, POM patterns
- **DeduplicationService** (services/deduplication.py): ChromaDB RAG for caching similar test code
- **SchedulerService** (services/scheduler.py): APScheduler for batch processing
- **Celery Application** (core/celery_app.py): Configures the Celery worker and tasks.
- **Redis Client** (core/redis.py): Provides asynchronous Redis client for Pub/Sub operations.
- **Celery Tasks** (tasks.py): Defines background tasks for test execution and other long-running operations.

## Development Workflows

### Running Locally
```bash
docker-compose up --build -d  # Full stack: backend (8000), frontend (3000), db (5432), chromadb (8001), worker, redis
```

### Testing
```bash
cd backend
pytest tests/  # Uses pytest-asyncio, mocks LLM calls via pytest-mock
```

Test structure:
- `tests/unit/`: Isolated logic tests (agents, parsers, validators)
- `tests/integration/`: LLM integration tests (use real API keys from .env)

### Adding New Agent Nodes
1. Create node function in [agents/nodes.py](../backend/src/app/agents/nodes.py) accepting `AgentState`
2. Register in `create_workflow()` with `workflow.add_node("name", node_func)`
3. Add routing logic in conditional edges (see `route_after_analyst`)

### Frontend Development
- Components: Functional React with TypeScript in `frontend/src/widgets/`
- Monaco Editor for code display (Editor.tsx)
- SSE streaming from `/api/v1/chat` and `/api/v1/execution/{id}/logs` endpoints yields JSON events: `{type: 'log'|'plan'|'code', content: ...}`

## Project-Specific Conventions

### Code Generation Patterns
Generated tests MUST follow this structure (enforced by CodeValidator):
```python
import allure
from playwright.sync_api import Page, expect

@allure.epic("Module Name")
@allure.feature("Feature")
class TestClassName:
    @allure.story("Story")
    @allure.title("Test Title")
    @allure.severity(allure.severity_level.NORMAL)
    def test_name(self, page: Page):
        # Test body
```

### Validation Rules (see linter.py)
- **Banned imports**: `os`, `subprocess`, `shutil`, `sys`, `builtins`
- **Banned functions**: `eval`, `exec`, `compile`
- **Allure requirements**: Every test class needs @epic, test methods need @story + @title
- **POM enforcement**: If Page Object classes exist, test methods must not use raw `page.locator()` calls

### Configuration
- **Environment**: `backend/.env` requires `CLOUD_RU_API_KEY`, `CLOUD_RU_BASE_URL`, `MODEL_NAME`
- **Models**: Available models in [frontend/src/entities/store.ts](../frontend/src/entities/store.ts) `AVAILABLE_MODELS` array (Qwen3-Coder-480B default)
- **Database**: SQLAlchemy async with PostgreSQL (models in domain/models.py)

### API Endpoints
- `POST /api/v1/generate`: One-shot test generation
- `POST /api/v1/chat`: SSE streaming for conversational interface (persists thread_id)
- `POST /api/v1/execution/{id}/run`: Triggers a Celery task for asynchronous test execution.
- `GET /api/v1/execution/{id}/logs`: SSE streaming for real-time test execution logs.
- `GET /api/v1/history`: Lists TestRun records by session_id

### Error Handling
- Auto-fix flow: Frontend sends `[AUTO-FIX]` prefix → router sets `task_type=debug_request` → debugger node uses DEBUGGER_SYSTEM_PROMPT
- Validation failures: Store `validation_error` in state, increment `attempts` (max 3)
- LLM crashes: Nodes have fallback retry logic without vision context (see analyst_node DOM error handling)

## Integration Points

### External Dependencies
- **Cloud.ru Evolution API**: LLM provider via langchain-openai with custom base_url
- **Playwright**: `playwright install chromium` required in runner image
- **ChromaDB**: Vector store for RAG (CHROMA_HOST/PORT in config)
- **Docker**: Must be running for test execution
- **Celery**: Task queue system
- **Redis**: Message broker for Celery and Pub/Sub for logs

### Key Tools Used by Agents
- **WebInspector**: Scrapes DOM for UI tests (returns element attributes: id, class, data-testid)
- **CodebaseNavigator**: Clones git repos, generates file trees for context
- **OpenAPIParser**: Parses Swagger/OpenAPI specs for API test generation
- **TraceInspector**: Parses Playwright trace files for debugging

## Common Gotchas
- Docker containers persist between runs → `cleanup_all()` in executor startup
- SSE responses must be formatted as `f"data: {json.dumps(obj)}\n\n"` for chat and execution logs.
- LangGraph state updates are partial → always return dict with changed keys only
- Session IDs are UUID strings passed via `X-Session-ID` header (see api/client.ts interceptor)
- Test files written to TEMP_DIR are mounted into Docker with absolute paths

## File Navigation
- Agent prompts: [backend/src/app/agents/prompts.py](../backend/src/app/agents/prompts.py)
- Domain models: [backend/src/app/domain/models.py](../backend/src/app/domain/models.py)
- Frontend store: [frontend/src/entities/store.ts](../frontend/src/entities/store.ts)
- Docker runner: [backend/Dockerfile.runner](../backend/Dockerfile.runner)
- Celery app config: [backend/src/app/core/celery_app.py](../backend/src/app/core/celery_app.py)
- Celery tasks: [backend/src/app/tasks.py](../backend/src/app/tasks/py)
