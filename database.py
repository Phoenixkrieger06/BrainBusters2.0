from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from brainbuster.models import Question

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "brainbuster.db"


DEFAULT_QUESTIONS: dict[str, list[dict[str, object]]] = {
    "Allgemeinwissen": [
        {
            "text": "Wie viele Kontinente gibt es auf der Erde?",
            "options": ["5", "6", "7", "8"],
            "correct_index": 2,
            "difficulty": "easy",
        },
        {
            "text": "In welchem Jahr fiel die Berliner Mauer?",
            "options": ["1987", "1988", "1989", "1991"],
            "correct_index": 2,
            "difficulty": "medium",
        },
        {
            "text": "Welche Farbe entsteht aus Blau und Gelb?",
            "options": ["Lila", "Orange", "Grün", "Rot"],
            "correct_index": 2,
            "difficulty": "easy",
        },
    ],
    "Informatik": [
        {
            "text": "Wofür steht die Abkürzung CPU?",
            "options": [
                "Central Processing Unit",
                "Computer Power Utility",
                "Central Program Upload",
                "Control Processing User",
            ],
            "correct_index": 0,
            "difficulty": "easy",
        },
        {
            "text": "Welches Protokoll wird für verschlüsselte Webseiten genutzt?",
            "options": ["HTTP", "FTP", "HTTPS", "SMTP"],
            "correct_index": 2,
            "difficulty": "easy",
        },
        {
            "text": "Welche Datenbank ist dateibasiert und ohne separaten Server nutzbar?",
            "options": ["Oracle", "SQLite", "PostgreSQL", "MongoDB"],
            "correct_index": 1,
            "difficulty": "medium",
        },
    ],
    "Filme & Serien": [
        {
            "text": "Wie heißt die Schule für Hexerei in Harry Potter?",
            "options": ["Durmstrang", "Beauxbatons", "Hogwarts", "Narnia"],
            "correct_index": 2,
            "difficulty": "easy",
        },
        {
            "text": "Wie heißt die Stadt von Batman?",
            "options": ["Metropolis", "Central City", "Gotham City", "Star City"],
            "correct_index": 2,
            "difficulty": "easy",
        },
        {
            "text": "Welche Figur trägt meist ein rotes Lichtschwert?",
            "options": ["Jedi", "Sith", "Hobbit", "Avenger"],
            "correct_index": 1,
            "difficulty": "medium",
        },
    ],
}


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    options_json TEXT NOT NULL,
    correct_index INTEGER NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'medium',
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    mode TEXT NOT NULL,
    score INTEGER NOT NULL,
    correct_answers INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    average_response_seconds REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS score_achievements (
    score_id INTEGER NOT NULL,
    achievement_id INTEGER NOT NULL,
    PRIMARY KEY (score_id, achievement_id),
    FOREIGN KEY (score_id) REFERENCES scores(id) ON DELETE CASCADE,
    FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE
);
"""


DEFAULT_ACHIEVEMENTS = [
    ("FAST", "Blitzantwort", "Eine Frage in unter 3 Sekunden richtig beantwortet."),
    ("STREAK3", "Serie", "Drei Fragen in Folge richtig beantwortet."),
    ("PERFECT", "Perfektes Spiel", "Alle Fragen eines Spiels korrekt beantwortet."),
    ("CHAMPION", "BrainBuster-Champion", "Mindestens 100 Punkte in einem Spiel erreicht."),
]


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path: Path | None = None) -> Path:
    path = db_path or DB_PATH
    with get_connection(path) as connection:
        connection.executescript(SCHEMA)
        seed_achievements(connection)
        seed_questions_if_empty(connection)
        connection.commit()
    return path


def seed_achievements(connection: sqlite3.Connection) -> None:
    connection.executemany(
        """
        INSERT OR IGNORE INTO achievements (code, title, description)
        VALUES (?, ?, ?)
        """,
        DEFAULT_ACHIEVEMENTS,
    )


def seed_questions_if_empty(connection: sqlite3.Connection) -> None:
    row = connection.execute("SELECT COUNT(*) AS count FROM questions").fetchone()
    if row["count"] > 0:
        return

    for category_name, questions in DEFAULT_QUESTIONS.items():
        connection.execute(
            "INSERT OR IGNORE INTO categories (name) VALUES (?)",
            (category_name,),
        )
        category_row = connection.execute(
            "SELECT id FROM categories WHERE name = ?",
            (category_name,),
        ).fetchone()
        category_id = category_row["id"]

        for question in questions:
            connection.execute(
                """
                INSERT INTO questions (category_id, text, options_json, correct_index, difficulty)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    category_id,
                    question["text"],
                    json.dumps(question["options"], ensure_ascii=False),
                    question["correct_index"],
                    question["difficulty"],
                ),
            )


def import_questions(connection: sqlite3.Connection, category_name: str, questions: Iterable[Question]) -> int:
    connection.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category_name,))
    category_row = connection.execute(
        "SELECT id FROM categories WHERE name = ?",
        (category_name,),
    ).fetchone()
    category_id = category_row["id"]

    inserted = 0
    for question in questions:
        connection.execute(
            """
            INSERT INTO questions (category_id, text, options_json, correct_index, difficulty)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                category_id,
                question.text,
                json.dumps(question.options, ensure_ascii=False),
                question.correct_index,
                question.difficulty,
            ),
        )
        inserted += 1

    connection.commit()
    return inserted