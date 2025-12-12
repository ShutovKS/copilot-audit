import { SlideData, SlideType } from './types';

export const SLIDES: SlideData[] = [
  {
    id: 1,
    type: SlideType.TITLE,
    title: "Smart ValidOps",
    subtitle: "Кирилл Корнилов\nКапитан команды",
    image: "./my_photo.jpg" // Ensure this file is in the public folder
  },
  {
    id: 2,
    type: SlideType.GRID_CARDS,
    title: "Почему LLM не умеют тестировать?",
    content: [
      { title: "Галлюцинации", description: "Придумывает селекторы, которых нет в DOM.", icon: "ghost" },
      { title: "Слепота", description: "Модель не «видит» реальный интерфейс сайта.", icon: "eye-off" },
      { title: "Хрупкость", description: "Тесты падают при малейшем изменении верстки.", icon: "zap-off" },
      { title: "Безопасность", description: "Генерирует опасный код.", icon: "shield-alert" }
    ]
  },
  {
    id: 3,
    type: SlideType.FLOWCHART,
    title: "Агентный подход",
    content: [
      { role: "Запрос пользователя", label: "User", icon: "user", description: "Ввод задачи на естественном языке, ссылка на Swagger/URL или загрузка репозитория." },
      { role: "Router", label: "Router", icon: "git-branch", description: "Классификация запроса (UI/API/Debug). Выбор модели." },
      { role: "Analyst", label: "Analyst", icon: "search", description: "Сканирование DOM-дерева, поиск паттернов (RAG)." },
      { role: "Coder", label: "Coder", icon: "code", description: "Генерация кода (Python + Playwright)." },
      { role: "Reviewer", label: "Reviewer", icon: "check-circle", description: "Проверка AST, линтеры, валидация." },
      { role: "Executor", label: "Executor", icon: "play", description: "Запуск тестов в изолированном Docker-контейнере." }
    ]
  },
  {
    id: 4,
    type: SlideType.CODE_SPLIT,
    title: "Оркестрация через LangGraph",
    content: "Решение создает не линейную цепочку, а граф. Это позволяет всем агентам работать с единым контекстом.\n\nКлючевой элемент — условные переходы. Функция should_continue выступает как Quality Gate: если Reviewer находит ошибки, процесс возвращается к Coder.",
    code: `def create_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("analyst", analyst_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("reviewer", reviewer_node)

    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {"coder": "coder", "end": END}
    )
    return workflow`
  },
  {
    id: 5,
    type: SlideType.CODE_SPLIT,
    title: "Агент видит реальный DOM",
    content: "Агент запускает реальный браузер в фоне. Он не просто скачивает HTML, а ждет JS-гидратации страницы.\n\nМы не скармливаем модели весь HTML. Метод _parse_html_to_context извлекает только семантически важные элементы, экономя токены.",
    code: `async def inspect_page(self, url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        raw_html = await page.content()
        return self._parse_html_to_context(raw_html)`
  },
  {
    id: 6,
    type: SlideType.CODE_SPLIT,
    title: "Понимание контекста",
    content: "Система принимает на вход ZIP-архивы или ссылки на Git. Используем Abstract Syntax Tree (AST) вместо регулярных выражений.\n\nНа выходе LLM получает сжатую карту API: список эндпоинтов, параметры и типы данных.",
    code: `class FastAPIParser(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                method = decorator.func.attr
                if method in ['get', 'post', 'put']:
                    self._extract_endpoint(node, decorator)`
  },
  {
    id: 7,
    type: SlideType.CODE_SPLIT,
    title: "Гарантия валидности кода",
    content: "Static Analyzer блокирует любые попытки импорта опасных библиотек (os, subprocess).\n\nВалидатор проверяет наличие декораторов @allure. Код также прогоняется через Ruff для соблюдения PEP-8.",
    code: `class CodeValidator:
    BANNED_IMPORTS = {'os', 'subprocess', 'shutil', 'sys'}

    @staticmethod
    def validate(code: str) -> tuple[bool, str]:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                 if node.names[0].name in BANNED_IMPORTS:
                     return False, "Security Violation"
        
        if not CodeValidator._check_allure(tree):
             return False, "Missing @allure.step"
             
        return True, "Passed"`
  },
  {
    id: 8,
    type: SlideType.CODE_SPLIT,
    title: "Самоисправление ошибок",
    content: "Если тест падает, Executor извлекает Trace.zip (DOM-снапшот, логи, скриншот). Специализированный агент находит причину и исправляет код.\n\nЦикл повторяется, пока тест не станет «зеленым».",
    code: `DEBUGGER_SYSTEM_PROMPT = """
You are an Expert SDET acting as an Automated Debugger.

=== FAILURE CONTEXT (from Trace.zip) ===
1. Original Error: {original_error}
2. Failed Action: {summary}
3. DOM Snapshot at failure time: {dom_snapshot}

=== REASONING TASK ===
1. Analyze the DOM. Is element obscured?
2. Compare locator vs actual DOM.
3. Form Hypothesis.
4. GENERATE FIXED CODE.
"""`
  },
  {
    id: 9,
    type: SlideType.UI_SCREENSHOT,
    title: "Интерфейс Smart ValidOps",
    content: [
      { label: "Чат с контекстом", position: "left" },
      { label: "Monaco Editor", position: "center" },
      { label: "Streaming Logs", position: "right" }
    ]
  },
  {
    id: 10,
    type: SlideType.OUTRO,
    title: "Итоги",
    content: [
      "Full Cycle: От сканирования DOM до Merge Request.",
      "Powered by Cloud.ru: Qwen 2.5 Coder на мощностях Evolution.",
      "Production Ready: Docker-контейнеризация и Self-Healing."
    ],
    subtitle: "https://github.com/ShutovKS/copilot-audit"
  }
];