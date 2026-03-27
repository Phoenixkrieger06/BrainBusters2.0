from __future__ import annotations

import json
import sqlite3

from brainbuster.models import Achievement, Category, GameResult, Question, User


class UserRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create_user(self, username: str, password_hash: str) -> User:
        cursor = self.connection.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        self.connection.commit()
        return User(id=cursor.lastrowid, username=username, password_hash=password_hash)

    def get_by_username(self, username: str) -> User | None:
        row = self.connection.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None:
            return None
        return User(id=row["id"], username=row["username"], password_hash=row["password_hash"])


class CategoryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_categories(self) -> list[Category]:
        rows = self.connection.execute(
          "SELECT id, name FROM categories ORDER BY id"  
        ).fetchall()
        return [Category(id=row["id"], name=row["name"]) for row in rows]

    def create_category(self, name: str) -> Category:
        cursor = self.connection.execute(
            "INSERT INTO categories (name) VALUES (?)",
            (name,),
        )
        self.connection.commit()
        return Category(id=cursor.lastrowid, name=name)

    def delete_category(self, category_id: int) -> None:
        self.connection.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        self.connection.commit()


class QuestionRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_questions_by_category(self, category_id: int) -> list[Question]:
        rows = self.connection.execute(
            """
            SELECT q.id, q.category_id, c.name AS category_name, q.text, q.options_json,
                   q.correct_index, q.difficulty
            FROM questions q
            JOIN categories c ON c.id = q.category_id
            WHERE q.category_id = ?
            ORDER BY q.id
            """,
            (category_id,),
        ).fetchall()
        return [self._row_to_question(row) for row in rows]

    def list_all_questions(self) -> list[Question]:
        rows = self.connection.execute(
            """
            SELECT q.id, q.category_id, c.name AS category_name, q.text, q.options_json,
                   q.correct_index, q.difficulty
            FROM questions q
            JOIN categories c ON c.id = q.category_id
            ORDER BY c.name, q.id
            """
        ).fetchall()
        return [self._row_to_question(row) for row in rows]

    def create_question(
        self,
        category_id: int,
        text: str,
        options: list[str],
        correct_index: int,
        difficulty: str = "medium",
    ) -> Question:
        cursor = self.connection.execute(
            """
            INSERT INTO questions (category_id, text, options_json, correct_index, difficulty)
            VALUES (?, ?, ?, ?, ?)
            """,
            (category_id, text, json.dumps(options, ensure_ascii=False), correct_index, difficulty),
        )
        self.connection.commit()

        row = self.connection.execute(
            """
            SELECT q.id, q.category_id, c.name AS category_name, q.text, q.options_json,
                   q.correct_index, q.difficulty
            FROM questions q
            JOIN categories c ON c.id = q.category_id
            WHERE q.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
        return self._row_to_question(row)

    def update_question(
        self,
        question_id: int,
        text: str,
        options: list[str],
        correct_index: int,
        difficulty: str,
    ) -> None:
        self.connection.execute(
            """
            UPDATE questions
            SET text = ?, options_json = ?, correct_index = ?, difficulty = ?
            WHERE id = ?
            """,
            (text, json.dumps(options, ensure_ascii=False), correct_index, difficulty, question_id),
        )
        self.connection.commit()

    def delete_question(self, question_id: int) -> None:
        self.connection.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        self.connection.commit()

    @staticmethod
    def _row_to_question(row: sqlite3.Row) -> Question:
        return Question(
            id=row["id"],
            category_id=row["category_id"],
            category_name=row["category_name"],
            text=row["text"],
            options=json.loads(row["options_json"]),
            correct_index=row["correct_index"],
            difficulty=row["difficulty"],
        )


class LeaderboardRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save_result(self, user_id: int, result: GameResult) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO scores (user_id, mode, score, correct_answers, total_questions, average_response_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                result.mode,
                result.score,
                result.correct_answers,
                result.total_questions,
                result.average_response_seconds,
            ),
        )

        score_id = cursor.lastrowid

        for achievement in result.achievements:
            achievement_row = self.connection.execute(
                "SELECT id FROM achievements WHERE code = ?",
                (achievement.code,),
            ).fetchone()
            if achievement_row:
                self.connection.execute(
                    "INSERT OR IGNORE INTO score_achievements (score_id, achievement_id) VALUES (?, ?)",
                    (score_id, achievement_row["id"]),
                )

        self.connection.commit()
        return score_id

    def get_top_scores(self, limit: int = 10) -> list[dict[str, object]]:
        rows = self.connection.execute(
            """
            SELECT u.username, s.mode, s.score, s.correct_answers, s.total_questions,
                   s.average_response_seconds, s.created_at
            FROM scores s
            JOIN users u ON u.id = s.user_id
            ORDER BY s.score DESC, s.average_response_seconds ASC, s.created_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_score_achievements(self, score_id: int) -> list[Achievement]:
        rows = self.connection.execute(
            """
            SELECT a.code, a.title, a.description
            FROM achievements a
            JOIN score_achievements sa ON sa.achievement_id = a.id
            WHERE sa.score_id = ?
            ORDER BY a.title
            """,
            (score_id,),
        ).fetchall()

        return [
            Achievement(code=row["code"], title=row["title"], description=row["description"])
            for row in rows
        ]