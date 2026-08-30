"""Todo record shape stored in ~/todos/todos.json."""

from typing import Literal, NotRequired, TypedDict

TodoStatus = Literal["todo", "done"]


class Todo(TypedDict):
    name: str
    status: TodoStatus
    flag: bool
    description: NotRequired[str]
