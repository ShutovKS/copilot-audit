import json
import uuid
from pathlib import Path
from typing import Any

from src.app.core.config import get_settings


class StorageService:
    """
    Handles saving and loading of large data artifacts to avoid state bloat.
    """

    def __init__(self, base_path: Path = get_settings().STORAGE_PATH):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _generate_path(self, run_id: int | str, extension: str) -> Path:
        run_path = self.base_path / str(run_id)
        run_path.mkdir(exist_ok=True)
        return run_path / f"{uuid.uuid4()}.{extension}"

    def save(self, data: str | bytes, run_id: int | str, extension: str = "txt") -> str:
        """Saves text or binary data and returns the relative path."""
        path = self._generate_path(run_id, extension)
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data, encoding="utf-8")
        return str(path)

    def save_json(self, data: Any, run_id: int | str) -> str:
        """Saves a JSON-serializable object and returns the relative path."""
        path = self._generate_path(run_id, "json")
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return str(path)

    def load(self, path: str) -> str:
        """Loads text data from the given relative path."""
        full_path = self.base_path / path
        return full_path.read_text(encoding="utf-8")

    def load_bytes(self, path: str) -> bytes:
        """Loads binary data from the given relative path."""
        full_path = self.base_path / path
        return full_path.read_bytes()

    def load_json(self, path: str) -> Any:
        """Loads a JSON object from the given relative path."""
        full_path = self.base_path / path
        with full_path.open("r", encoding="utf-8") as f:
            return json.load(f)


storage_service = StorageService()
