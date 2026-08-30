"""Load and save todos in ~/todos/todos.json."""

from __future__ import annotations

import json
from pathlib import Path

from todo_mcp.models import Todo

DEFAULT_PATH = Path.home() / "todos" / "todos.json"


class TodoStorageError(Exception):
    """Anticipated storage failure (bad file, duplicate name, empty name)."""


class TodoStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path is not None else DEFAULT_PATH

    def load(self) -> list[Todo]:
        if not self.path.exists():
            return []
        try:
            text = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            raise TodoStorageError(f"Could not read {self.path}: {exc}") from exc

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise TodoStorageError(
                f"{self.path} is not valid JSON ({exc}). "
                "Fix or remove the file; it will not be overwritten."
            ) from exc

        if not isinstance(data, list):
            raise TodoStorageError(
                f"{self.path} must be a JSON array of todos, not {type(data).__name__}."
            )

        todos: list[Todo] = []
        for index, item in enumerate(data):
            if not isinstance(item, dict):
                raise TodoStorageError(f"{self.path} item {index} is not a JSON object.")
            name = item.get("name")
            if not isinstance(name, str):
                raise TodoStorageError(f"{self.path} item {index} is missing a string 'name'.")
            todos.append(item)  # type: ignore[arg-type]
        return todos

    def create(self, name: str, description: str | None = None) -> Todo:
        name = name.strip()
        if not name:
            raise TodoStorageError("Todo name is required and cannot be empty.")

        todos = self.load()
        if any(todo["name"] == name for todo in todos):
            raise TodoStorageError(f"A todo named {name!r} already exists.")

        todo: Todo = {"name": name, "status": "todo", "flag": False}
        if description is not None:
            trimmed = description.strip()
            if trimmed:
                todo["description"] = trimmed

        todos.append(todo)
        self._save(todos)
        return todo

    def _save(self, todos: list[Todo]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(todos, indent=2, ensure_ascii=False) + "\n"
            self.path.write_text(payload, encoding="utf-8")
        except OSError as exc:
            raise TodoStorageError(f"Could not write {self.path}: {exc}") from exc


store = TodoStore()
