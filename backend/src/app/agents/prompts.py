from pathlib import Path

def _load_prompt(name: str) -> str:
    """Helper function to load a prompt from a YAML file."""
    prompt_path = Path(__file__).parent / "prompts" / f"{name}.yaml"
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Prompt '{name}' not found."

ANALYST_SYSTEM_PROMPT = _load_prompt("analyst_system_prompt")
CODER_SYSTEM_PROMPT = _load_prompt("coder_system_prompt")
DEBUGGER_SYSTEM_PROMPT = _load_prompt("debugger_system_prompt")
FIXER_SYSTEM_PROMPT = _load_prompt("fixer_system_prompt")
ROUTER_SYSTEM_PROMPT = _load_prompt("router_system_prompt")


__all__ = [
    "ANALYST_SYSTEM_PROMPT",
    "CODER_SYSTEM_PROMPT",
    "DEBUGGER_SYSTEM_PROMPT",
    "FIXER_SYSTEM_PROMPT",
    "ROUTER_SYSTEM_PROMPT",
]
