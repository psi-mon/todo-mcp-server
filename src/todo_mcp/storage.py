"""Load and save todos in ~/todos/todos.json."""

from __future__ import annotations

import json
from pathlib import Path

from mcp_types import Resource as MCPResource

from todo_mcp.models import Todo, TodoListItem

DEFAULT_PATH = Path.home() / "todos" / "todos.json"
DEFAULT_DONE_PATH = Path.home() / "todos" / "donedos.json"
TODOS_URI = "todo://todos"
TODO_TEMPLATE_URI = "todo://todo/{name}"
FLAGGED_TODOS_URI = "flaggedTodo://todos"
FLAGGED_TODO_TEMPLATE_URI = "flaggedTodo://todo/{name}"


class TodoStorageError(Exception):
    """Anticipated storage failure (bad file, duplicate name, empty name)."""


class TodoNotFoundError(TodoStorageError):
    """Anticipated failure when a specific todo name does not exist."""


class TodoStore:
    def __init__(
        self,
        path: Path | None = None,
        done_path: Path | None = None,
    ) -> None:
        self.path = path if path is not None else DEFAULT_PATH
        self.done_path = done_path if done_path is not None else DEFAULT_DONE_PATH

    def _load_file(self, file_path: Path) -> list[Todo]:
        if not file_path.exists():
            return []
        try:
            text = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise TodoStorageError(f"Could not read {file_path}: {exc}") from exc

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise TodoStorageError(
                f"{file_path} is not valid JSON ({exc}). "
                "Fix or remove the file; it will not be overwritten."
            ) from exc

        if not isinstance(data, list):
            raise TodoStorageError(
                f"{file_path} must be a JSON array of todos, not {type(data).__name__}."
            )

        todos: list[Todo] = []
        for index, item in enumerate(data):
            if not isinstance(item, dict):
                raise TodoStorageError(f"{file_path} item {index} is not a JSON object.")
            name = item.get("name")
            if not isinstance(name, str):
                raise TodoStorageError(f"{file_path} item {index} is missing a string 'name'.")
            todos.append(item)  # type: ignore[arg-type]
        return todos

    def _save_file(self, file_path: Path, todos: list[Todo]) -> None:
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(todos, indent=2, ensure_ascii=False) + "\n"
            file_path.write_text(payload, encoding="utf-8")
        except OSError as exc:
            raise TodoStorageError(f"Could not write {file_path}: {exc}") from exc

    def load(self) -> list[Todo]:
        """Load all active todos from todos.json."""
        return self._load_file(self.path)

    def load_done(self) -> list[Todo]:
        """Load all done todos from donedos.json."""
        return self._load_file(self.done_path)

    def get_done_todos(self) -> list[Todo]:
        """Return all done todos."""
        return self.load_done()

    def get(self, name: str) -> Todo:
        """Get a single todo by exact, case-sensitive name from active todos.

        Raises:
            TodoNotFoundError: If no active todo with that exact name exists.
            TodoStorageError: If the file cannot be read or parsed.
        """
        todos = self.load()
        for todo in todos:
            if todo["name"] == name:
                return todo
        raise TodoNotFoundError(f"Todo {name!r} not found.")

    def list_summary(self) -> list[TodoListItem]:
        """Return all todos with only name, status, and flag (omitting description)."""
        todos = self.load()
        return [
            {
                "name": todo["name"],
                "status": todo["status"],
                "flag": todo["flag"],
            }
            for todo in todos
        ]

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

    def mark_done(self, name: str) -> Todo:
        """Mark a todo as done.

        Removes the todo from todos.json and moves it into donedos.json
        with status set to "done".

        Raises:
            TodoNotFoundError: If no active todo with that exact name exists.
            TodoStorageError: If reading or writing either file fails.
        """
        active_todos = self.load()
        found_todo: Todo | None = None
        remaining_todos: list[Todo] = []

        for todo in active_todos:
            if todo["name"] == name:
                found_todo = todo
            else:
                remaining_todos.append(todo)

        if found_todo is None:
            raise TodoNotFoundError(f"Todo {name!r} not found in active todos.")

        done_todo: Todo = dict(found_todo)  # type: ignore[assignment]
        done_todo["status"] = "done"

        done_todos = self.load_done()
        done_todos = [t for t in done_todos if t["name"] != name]
        done_todos.append(done_todo)

        self._save_file(self.path, remaining_todos)
        self._save_file(self.done_path, done_todos)

        return done_todo

    def flag_todo(self, name: str) -> Todo:
        """Set flag to True on the specified active todo.

        Raises:
            TodoNotFoundError: If no active todo matches the given name.
            TodoStorageError: If reading or saving the file fails.
        """
        todos = self.load()
        for todo in todos:
            if todo["name"] == name:
                todo["flag"] = True
                self._save(todos)
                return todo
        raise TodoNotFoundError(f"Todo {name!r} not found in active todos.")

    def list_flagged_todos(self) -> list[Todo]:
        """Return all active todos that have flag set to True."""
        todos = self.load()
        return [todo for todo in todos if todo.get("flag") is True]

    def get_flagged_todo(self, name: str) -> Todo:
        """Get a single flagged todo by exact name.

        Raises:
            TodoNotFoundError: If no flagged todo matches the given name.
            TodoStorageError: If reading the file fails.
        """
        flagged = self.list_flagged_todos()
        for todo in flagged:
            if todo["name"] == name:
                return todo
        raise TodoNotFoundError(f"Flagged todo {name!r} not found.")

    def _save(self, todos: list[Todo]) -> None:
        self._save_file(self.path, todos)


store = TodoStore()


def todo_to_resource_uri(name: str) -> str:
    """Return the resource URI for a specific todo name."""
    return f"todo://todo/{name}"


def format_todo_resource(todo: Todo) -> MCPResource:
    """Create an MCPResource for a single todo object."""
    return MCPResource(
        uri=todo_to_resource_uri(todo["name"]),
        name=todo["name"],
        description=todo.get("description"),
        mime_type="application/json",
    )


def get_all_mcp_resources(store_instance: TodoStore | None = None) -> list[MCPResource]:
    """Return all MCP resources: collection resource ('todo://todos') + individual todo resources."""
    target_store = store_instance if store_instance is not None else store
    resources: list[MCPResource] = [
        MCPResource(
            uri=TODOS_URI,
            name="All Todos",
            description="Complete JSON array of all todos in ~/todos/todos.json",
            mime_type="application/json",
        )
    ]
    for todo in target_store.load():
        resources.append(format_todo_resource(todo))
    return resources


def flagged_todo_to_resource_uri(name: str) -> str:
    """Return the resource URI for a specific flagged todo."""
    return f"flaggedTodo://todo/{name}"


def format_flagged_todo_resource(todo: Todo) -> MCPResource:
    """Create an MCPResource for a single flagged todo object."""
    return MCPResource(
        uri=flagged_todo_to_resource_uri(todo["name"]),
        name=f"Flagged: {todo['name']}",
        description=todo.get("description"),
        mime_type="application/json",
    )


def get_all_flagged_mcp_resources(store_instance: TodoStore | None = None) -> list[MCPResource]:
    """Return all flagged MCP resources (collection resource + individual flagged resources)."""
    target_store = store_instance if store_instance is not None else store
    resources: list[MCPResource] = [
        MCPResource(
            uri=FLAGGED_TODOS_URI,
            name="All Flagged Todos",
            description="Complete JSON array of all flagged todos in ~/todos/todos.json",
            mime_type="application/json",
        )
    ]
    for todo in target_store.list_flagged_todos():
        resources.append(format_flagged_todo_resource(todo))
    return resources


def get_all_combined_mcp_resources(store_instance: TodoStore | None = None) -> list[MCPResource]:
    """Return all regular and flagged MCP resources for Cursor @ discovery."""
    target_store = store_instance if store_instance is not None else store
    return get_all_mcp_resources(target_store) + get_all_flagged_mcp_resources(target_store)

