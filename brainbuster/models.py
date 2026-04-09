from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Category:
    id: int | None
    name: str


@dataclass(slots=True)
class Question:
    id: int | None
    category_id: int
    category_name: str
    text: str
    options: list[str]
    correct_index: int
    difficulty: str = "medium"


@dataclass(slots=True)
class User:
    id: int | None
    username: str
    password_hash: str


@dataclass(slots=True)
class Achievement:
    code: str
    title: str
    description: str


@dataclass(slots=True)
class GameResult:
    username: str
    mode: str
    score: int
    correct_answers: int
    total_questions: int
    average_response_seconds: float
    achievements: list[Achievement] = field(default_factory=list)
