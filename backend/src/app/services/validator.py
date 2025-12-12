import logging
from .executor import TestExecutorService
from .tools.static_analyzer import StaticCodeAnalyzer

logger = logging.getLogger(__name__)


class ValidationService:
    def __init__(self, executor_service: TestExecutorService | None = None):
        self.static_analyzer = StaticCodeAnalyzer()
        self.executor_service = executor_service or TestExecutorService()

    async def validate(self, code: str) -> tuple[bool, str, str | None]:
        # Step 1: Perform static analysis first
        is_statically_valid, message, fixed_code = self.static_analyzer.validate(code)

        if not is_statically_valid:
            return False, message, fixed_code

        code_to_check = fixed_code or code

        # Step 2: Perform isolated dynamic check (pytest --collect-only)
        is_dynamically_valid, dynamic_message = await self.executor_service.validate_code_in_isolation(code_to_check)

        if not is_dynamically_valid:
            return False, dynamic_message, code_to_check

        # If both validations pass, return the success message from the static analysis phase
        return True, message, fixed_code
