import sqlite3

from brainbuster.database import SCHEMA
from brainbuster.repositories import UserRepository
from brainbuster.services import AuthService, ScoreService, RoundStats, hash_password


def make_connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    connection.commit()
    return connection


def test_hash_password_is_deterministic():
    assert hash_password("secret") == hash_password("secret")
    assert hash_password("secret") != "secret"


def test_auth_service_register_and_login():
    connection = make_connection()
    repository = UserRepository(connection)
    service = AuthService(repository)

    user = service.register("hagen", "test123")

    assert user.id is not None
    assert service.login("hagen", "test123") is not None
    assert service.login("hagen", "falsch") is None


def test_calculate_question_points_fast_and_streak_bonus():
    service = ScoreService()

    points = service.calculate_question_points(
        correct=True,
        response_seconds=2.5,
        current_streak=3,
    )

    assert points == 25


def test_build_achievements_returns_expected_codes():
    service = ScoreService()
    stats = RoundStats(
        correct_answers=5,
        total_questions=5,
        score=105,
        average_response_seconds=2.4,
        response_times=[2.0, 2.5, 4.0, 1.5, 2.2],
        max_correct_streak=5,
        all_correct=True,
    )

    achievements = service.build_achievements(stats)
    codes = {achievement.code for achievement in achievements}

    assert codes == {"FAST", "STREAK3", "PERFECT", "CHAMPION"}