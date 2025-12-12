import { SlideData, SlideType } from './types';

export const SLIDES: SlideData[] = [
  {
    id: 1,
    type: SlideType.TITLE,
    title: "TestOps\nEvolution\nForge",
    subtitle: ["Данилов Михаил", "Корнилов Кирилл", "Шутов Кирилл"],
    image: ["./danilov_photo.jpg", "./kornilov_photo.jpg", "./shutov_photo.jpg"]
  },
  {
    id: 2,
    type: SlideType.GRID_CARDS,
    title: "Что такое TestOps Forge?",
    content: [
      { title: "Agentic QA System", description: "Система, которая не просто пишет код, а видит интерфейс, понимает архитектуру и чинит тесты.", icon: "ghost" },
      { title: "White-Box Analysis", description: "Анализирует исходный код (AST) репозитория для создания точных интеграционных тестов.", icon: "file-json" },
      { title: "Self-Healing", description: "Автоматически исправляет упавшие тесты, анализируя трейсы Playwright и скриншоты.", icon: "shield-alert" },
      { title: "Parallel Batching", description: "Распараллеливает генерацию сотен сценариев с помощью асинхронной архитектуры.", icon: "cpu" }
    ]
  },
  {
    id: 3,
    type: SlideType.GRID_CARDS,
    title: "Технологический стек (v1.4.0)",
    content: [
      { title: "Frontend", description: "React 19, Vite 7, Tailwind 4, Monaco Editor. Dark Console Theme.", icon: "react" },
      { title: "Backend", description: "Python 3.11, FastAPI, LangGraph, SQLAlchemy (Async).", icon: "server" },
      { title: "AI Core", description: "Cloud.ru Evolution (Qwen 3 Coder & Qwen 2.5). RAG via ChromaDB.", icon: "database" },
      { title: "Execution", description: "Docker Containers, Playwright, Allure Report, GitLab API.", icon: "layers" }
    ]
  },
  {
    id: 4,
    type: SlideType.FLOWCHART,
    title: "Архитектура Агентов (LangGraph)",
    content: [
      { role: "Router", label: "Router", icon: "git-branch", description: "Классифицирует запрос: UI Test, API Test, Repo Analysis или Debug." },
      { role: "Analyst", label: "Analyst", icon: "search", description: "RAG + WebInspector. Формирует план тестирования." },
      { role: "Batch Node", label: "Batch", icon: "cpu", description: "Параллельная генерация кода для независимых сценариев." },
      { role: "Coder", label: "Coder", icon: "code", description: "Пишет код на Pytest + Playwright." },
      { role: "Reviewer", label: "Reviewer", icon: "check-circle", description: "Строгий AST-валидатор и Security Linter." },
      { role: "Debugger", label: "Debugger", icon: "bug", description: "Анализирует Trace.zip и правит код." }
    ]
  },
  {
    id: 5,
    type: SlideType.CODE_SPLIT,
    title: "Active Vision: Агент видит DOM",
    content: "Мы не скармливаем модели «сырой» HTML. Инструмент **WebInspector** использует Playwright для рендеринга страницы и извлечения **семантического контекста**.\n\nЭто позволяет извлекать реальные `data-testid` и `id`, исключая галлюцинации селекторов.",
    code: `class WebInspector:
    async def inspect_page(self, url: str) -> str:
        async with async_playwright() as p:
            # Запускаем реальный браузер
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Ждем гидратации JS
            await page.goto(url, wait_until="domcontentloaded")
            
            # Парсим "Accessibility Tree"
            return self._parse_html_to_context(await page.content())`
  },
  {
    id: 6,
    type: SlideType.CODE_SPLIT,
    title: "White-Box: Анализ кода (AST)",
    content: "Агент не ограничивается черным ящиком. Модуль **CodeAnalysisService** скачивает репозиторий и строит карту эндпоинтов, используя AST (Abstract Syntax Tree).\n\nПоддержка: **FastAPI (Python)**, **Spring (Java)**, **NestJS (TS)**.",
    code: `class FastAPIParser:
    def parse_file(self, content: str) -> list[ParsedEndpoint]:
        tree = ast.parse(content)
        endpoints = []
        
        # Обход AST дерева Python
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                 # Извлечение декораторов @app.get(...)
                 if self._is_route(node):
                     endpoints.append(self._extract_metadata(node))
                     
        return endpoints`
  },
  {
    id: 7,
    type: SlideType.CODE_SPLIT,
    title: "Параллельный Batch Processing",
    content: "Аналитик разбивает сложные задачи на список сценариев. **Batch Node** использует `asyncio.gather` для одновременной генерации кода, ускоряя процесс в 5-10 раз.",
    code: `async def batch_node(state: AgentState) -> dict:
    scenarios = state["scenarios"]
    
    # Параллельный запуск генерации
    tasks = [
        process_single_scenario(scenario, i) 
        for i, scenario in enumerate(scenarios)
    ]
    
    # Сбор результатов
    results = await asyncio.gather(*tasks)
    
    return {
        "generated_code": combine_results(results),
        "status": ProcessingStatus.COMPLETED
    }`
  },
  {
    id: 8,
    type: SlideType.CODE_SPLIT,
    title: "Smart Quality Gate",
    content: "**CodeValidator** — это не просто линтер. Это строгий страж качества:\n\n1. **Security:** Блокирует `import os`, `subprocess`.\n2. **Allure Strict:** Требует наличия `@allure.step`.\n3. **POM Validator:** Проверяет, что методы, вызванные в тесте, реально существуют в Page Object классе.",
    code: `class CodeValidator:
    BANNED = {'os', 'subprocess', 'shutil'}

    @staticmethod
    def validate(code: str) -> tuple[bool, str]:
        tree = ast.parse(code)
        
        # 1. Security Check
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and node.names[0].name in BANNED:
                return False, "Security Violation!"

        # 2. POM Consistency Check
        if not CodeValidator._check_pom_methods(tree):
             return False, "Method not defined in PageObject"
             
        return True, "Valid"`
  },
  {
    id: 9,
    type: SlideType.CODE_SPLIT,
    title: "Self-Healing: Trace Inspector",
    content: "Если тест падает, мы не просто отдаем лог. **TraceInspector** распаковывает `trace.zip` от Playwright и извлекает:\n\n*   📸 **DOM Snapshot** в момент ошибки.\n*   🌐 **Network Logs** (500/403 ошибки).\n*   🐞 **Console Errors**.",
    code: `class TraceInspector:
    def get_failure_context(self, run_id: int) -> dict:
        trace_file = self._find_trace_file(run_id)
        data = self._extract_trace_data(trace_file)
        
        failed_action = self._find_failed_action(data)
        
        return {
            "summary": failed_action['error'],
            "dom_snapshot": self._get_dom(failed_action),
            "network_errors": self._filter_network(data),
            "console_logs": self._get_console(data)
        }`
  },
  {
    id: 10,
    type: SlideType.TERMINAL,
    title: "Live Demo: Auto-Fix Workflow",
    code: `> System: Starting Test Run #42...\n> Executor: Docker container started.\n> Pytest: FAILED test_login.py::test_auth_error\n> System: ❌ Execution Failed. Triggering Auto-Fix...\n# ...\n> Debugger: Analyzing Trace Context...\n> Debugger: Hypothesis: Selector 'button.login' is obscured by cookie banner.\n> Debugger: Generating Fix...\n# ...\n> Coder: Adding step: page.get_by_text("Accept Cookies").click()\n> System: Rerunning Test #42...\n> Pytest: PASSED\n> System: ✅ Test Automatically Repaired.`
  },
  {
    id: 11,
    type: SlideType.UI_SCREENSHOT,
    title: "Консоль TestOps Forge",
    image: "./ide_example.png",
    content: [
      { label: "Чат с историей", position: "left" },
      { label: "Monaco Editor + Diff", position: "center" },
      { label: "Streaming Terminal", position: "right" }
    ]
  },
  {
    id: 12,
    type: SlideType.OUTRO,
    title: "Итоги",
    content: [
      "Автономия: Система сама генерирует, проверяет и чинит тесты.",
      "Глубина: White-Box анализ кода и Active Vision для UI.",
      "Скорость: Параллельная генерация и умный кеш."
    ],
    subtitle: "github.com/ShutovKS/copilot-audit"
  }
];
