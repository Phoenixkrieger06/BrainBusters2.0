from __future__ import annotations

import hashlib
import html
import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Iterable

from brainbuster.models import Achievement, GameResult, Question, User
from brainbuster.repositories import (
    CategoryRepository,
    LeaderboardRepository,
    QuestionRepository,
    UserRepository,
)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    def register(self, username: str, password: str) -> User:
        return self.user_repository.create_user(username, hash_password(password))

    def login(self, username: str, password: str) -> User | None:
        user = self.user_repository.get_by_username(username)
        if user is None:
            return None
        if user.password_hash != hash_password(password):
            return None
        return user


@dataclass(slots=True)
class RoundStats:
    correct_answers: int
    total_questions: int
    score: int
    average_response_seconds: float
    response_times: list[float]
    max_correct_streak: int
    all_correct: bool


class ScoreService:
    CORRECT_BASE_POINTS = 10
    FAST_BONUS_THRESHOLD = 3.0
    FAST_BONUS_POINTS = 5
    STREAK_BONUS_EVERY = 3
    STREAK_BONUS_POINTS = 10

    def calculate_question_points(
        self,
        correct: bool,
        response_seconds: float,
        current_streak: int,
    ) -> int:
        if not correct:
            return 0

        points = self.CORRECT_BASE_POINTS

        if response_seconds <= self.FAST_BONUS_THRESHOLD:
            points += self.FAST_BONUS_POINTS

        if current_streak > 0 and current_streak % self.STREAK_BONUS_EVERY == 0:
            points += self.STREAK_BONUS_POINTS

        return points

    def build_achievements(self, stats: RoundStats) -> list[Achievement]:
        achievements: list[Achievement] = []

        if any(seconds <= self.FAST_BONUS_THRESHOLD for seconds in stats.response_times):
            achievements.append(
                Achievement(
                    code="FAST",
                    title="Blitzantwort",
                    description="Eine Frage in unter 3 Sekunden richtig beantwortet.",
                )
            )

        if stats.max_correct_streak >= 3:
            achievements.append(
                Achievement(
                    code="STREAK3",
                    title="Serie",
                    description="Drei Fragen in Folge richtig beantwortet.",
                )
            )

        if stats.all_correct and stats.total_questions > 0:
            achievements.append(
                Achievement(
                    code="PERFECT",
                    title="Perfektes Spiel",
                    description="Alle Fragen eines Spiels korrekt beantwortet.",
                )
            )

        if stats.score >= 100:
            achievements.append(
                Achievement(
                    code="CHAMPION",
                    title="BrainBuster-Champion",
                    description="Mindestens 100 Punkte in einem Spiel erreicht.",
                )
            )

        return achievements


class QuestionService:
    def __init__(
        self,
        category_repository: CategoryRepository,
        question_repository: QuestionRepository,
    ) -> None:
        self.category_repository = category_repository
        self.question_repository = question_repository

    def get_categories(self):
        return self.category_repository.list_categories()

    def get_questions_for_category(self, category_id: int, amount: int = 5) -> list[Question]:
        questions = self.question_repository.list_questions_by_category(category_id)
        return questions[:amount]


class LeaderboardService:
    def __init__(self, leaderboard_repository: LeaderboardRepository) -> None:
        self.leaderboard_repository = leaderboard_repository

    def save_result(self, user_id: int, result: GameResult) -> int:
        return self.leaderboard_repository.save_result(user_id, result)

    def get_top_scores(self, limit: int = 10) -> list[dict[str, object]]:
        return self.leaderboard_repository.get_top_scores(limit)


class QuizGameService:
    def __init__(
        self,
        score_service: ScoreService,
        leaderboard_service: LeaderboardService,
        save_callback: Callable[[int, GameResult], int],
    ) -> None:
        self.score_service = score_service
        self.leaderboard_service = leaderboard_service
        self.save_callback = save_callback

    def play_round(
        self,
        username: str,
        user_id: int,
        mode: str,
        questions: Iterable[Question],
        answer_callback: Callable[[Question, int], tuple[int | None, float]],
    ) -> tuple[GameResult, int]:
        total_questions = 0
        correct_answers = 0
        score = 0
        correct_streak = 0
        max_correct_streak = 0
        response_times: list[float] = []

        for index, question in enumerate(questions, start=1):
            total_questions += 1
            answer_index, response_seconds = answer_callback(question, index)
            response_times.append(response_seconds)

            is_correct = answer_index == question.correct_index

            if is_correct:
                correct_answers += 1
                correct_streak += 1
                max_correct_streak = max(max_correct_streak, correct_streak)
            else:
                correct_streak = 0

            score += self.score_service.calculate_question_points(
                correct=is_correct,
                response_seconds=response_seconds,
                current_streak=correct_streak,
            )

        average_response_seconds = (
            sum(response_times) / len(response_times) if response_times else 0.0
        )

        stats = RoundStats(
            correct_answers=correct_answers,
            total_questions=total_questions,
            score=score,
            average_response_seconds=average_response_seconds,
            response_times=response_times,
            max_correct_streak=max_correct_streak,
            all_correct=(correct_answers == total_questions and total_questions > 0),
        )

        achievements = self.score_service.build_achievements(stats)

        result = GameResult(
            username=username,
            mode=mode,
            score=score,
            correct_answers=correct_answers,
            total_questions=total_questions,
            average_response_seconds=average_response_seconds,
            achievements=achievements,
        )

        score_id = self.save_callback(user_id, result)
        return result, score_id


class Timer:
    def now(self) -> float:
        return time.perf_counter()


class OpenTriviaService:
    BASE_URL = "https://opentdb.com"

    @classmethod
    def fetch_categories(cls) -> list[dict[str, object]]:
        url = f"{cls.BASE_URL}/api_category.php"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "BrainBuster/1.0"},
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return []

        categories = payload.get("trivia_categories", [])
        if not isinstance(categories, list):
            return []

        return categories

    @classmethod
    def fetch_questions(
        cls,
        amount: int = 5,
        category_id: int | None = None,
        difficulty: str | None = None,
        question_type: str = "multiple",
    ) -> list[Question]:
        params: dict[str, str] = {
            "amount": str(amount),
            "type": question_type,
        }

        if category_id is not None:
            params["category"] = str(category_id)

        if difficulty:
            params["difficulty"] = difficulty

        query = urllib.parse.urlencode(params)
        url = f"{cls.BASE_URL}/api.php?{query}"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "BrainBuster/1.0"},
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return []

        if payload.get("response_code") != 0:
            return []

        results = payload.get("results", [])
        if not isinstance(results, list):
            return []

        questions: list[Question] = []

        for item in results:
            correct_answer = html.unescape(item["correct_answer"])
            incorrect_answers = [
                html.unescape(answer) for answer in item["incorrect_answers"]
            ]

            options = incorrect_answers + [correct_answer]
            random.shuffle(options)

            question = Question(
                id=None,
                category_id=0,
                category_name=html.unescape(item["category"]),
                text=html.unescape(item["question"]),
                options=options,
                correct_index=options.index(correct_answer),
                difficulty=item.get("difficulty", "medium"),
            )
            questions.append(question)

        return questions
