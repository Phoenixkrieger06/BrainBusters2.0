from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from brainbuster.database import get_connection, initialize_database
from brainbuster.repositories import (
    CategoryRepository,
    LeaderboardRepository,
    QuestionRepository,
    UserRepository,
)
from brainbuster.services import (
    AuthService,
    LeaderboardService,
    QuestionService,
    QuizGameService,
    ScoreService,
    Timer,
)
from brainbuster.ui import (
    WELCOME_TEXT,
    render_categories,
    render_help,
    render_leaderboard,
    render_question,
    render_result,
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "brainbuster.db"


def ask_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Bitte gib einen Wert ein.")


def ask_int(prompt: str, min_value: int, max_value: int) -> int:
    while True:
        raw = input(prompt).strip()
        if raw.isdigit():
            value = int(raw)
            if min_value <= value <= max_value:
                return value
        print(f"Bitte gib eine Zahl zwischen {min_value} und {max_value} ein.")


def ask_from_allowed_ids(prompt: str, allowed_ids: list[int]) -> int:
    while True:
        raw = input(prompt).strip()
        if raw.isdigit():
            value = int(raw)
            if value in allowed_ids:
                return value
        print(f"Bitte wähle eine gültige ID aus: {allowed_ids}")


def authenticate(auth_service: AuthService):
    print("\n1. Login")
    print("2. Registrieren")
    while True:
        choice = input("Auswahl: ").strip()
        if choice == "1":
            username = ask_non_empty("Benutzername: ")
            password = ask_non_empty("Passwort: ")
            user = auth_service.login(username, password)
            if user is None:
                print("Login fehlgeschlagen.")
                continue
            print(f"Willkommen zurück, {user.username}.")
            return user

        if choice == "2":
            username = ask_non_empty("Neuer Benutzername: ")
            password = ask_non_empty("Neues Passwort: ")
            try:
                user = auth_service.register(username, password)
            except Exception as error:
                print(f"Registrierung fehlgeschlagen: {error}")
                continue
            print(f"Account {user.username} wurde angelegt.")
            return user

        print("Ungültige Auswahl.")


def choose_category(question_service: QuestionService):
    categories = question_service.get_categories()
    if not categories:
        print("Es sind keine Kategorien vorhanden.")
        return None

    print(render_categories(categories))
    allowed_ids = [category.id for category in categories if category.id is not None]
    category_id = ask_from_allowed_ids("Kategorie-ID wählen: ", allowed_ids)
    selected = next(category for category in categories if category.id == category_id)
    return selected


def build_answer_callback(timer: Timer) -> Callable:
    def callback(question, question_number):
        print(render_question(question, question_number))
        start = timer.now()
        answer = ask_int("Antwort: ", min_value=1, max_value=len(question.options))
        response_seconds = timer.now() - start
        return answer - 1, response_seconds

    return callback


def run_singleplayer(user, question_service, game_service, timer):
    category = choose_category(question_service)
    if category is None:
        return

    questions = question_service.get_questions_for_category(category.id, amount=5)
    if not questions:
        print("Für diese Kategorie sind keine Fragen vorhanden.")
        return

    result, _ = game_service.play_round(
        username=user.username,
        user_id=user.id,
        mode="Singleplayer",
        questions=questions,
        answer_callback=build_answer_callback(timer),
    )
    print(render_result(result))
    print(render_leaderboard(game_service.leaderboard_service.get_top_scores()))


def run_multiplayer(auth_service, question_service, game_service, timer):
    print("\nMehrspieler-Modus")
    print("Spieler 1 meldet sich an:")
    player1 = authenticate(auth_service)

    print("\nSpieler 2 meldet sich an:")
    player2 = authenticate(auth_service)

    category = choose_category(question_service)
    if category is None:
        return

    questions = question_service.get_questions_for_category(category.id, amount=5)
    if not questions:
        print("Für diese Kategorie sind keine Fragen vorhanden.")
        return

    print(f"\n{player1.username} ist an der Reihe.")
    result1, _ = game_service.play_round(
        username=player1.username,
        user_id=player1.id,
        mode="Mehrspieler",
        questions=questions,
        answer_callback=build_answer_callback(timer),
    )
    print(render_result(result1))

    print(f"\n{player2.username} ist an der Reihe.")
    result2, _ = game_service.play_round(
        username=player2.username,
        user_id=player2.id,
        mode="Mehrspieler",
        questions=questions,
        answer_callback=build_answer_callback(timer),
    )
    print(render_result(result2))

    if result1.score > result2.score:
        print(f"\nSieger: {player1.username}")
    elif result2.score > result1.score:
        print(f"\nSieger: {player2.username}")
    else:
        print("\nUnentschieden")

    print(render_leaderboard(game_service.leaderboard_service.get_top_scores()))


def run_cli() -> int:
    if len(sys.argv) > 1 and sys.argv[1].lower() == "h":
        print(render_help())
        return 0

    initialize_database(DB_PATH)

    with get_connection(DB_PATH) as connection:
        user_repository = UserRepository(connection)
        category_repository = CategoryRepository(connection)
        question_repository = QuestionRepository(connection)
        leaderboard_repository = LeaderboardRepository(connection)

        auth_service = AuthService(user_repository)
        question_service = QuestionService(category_repository, question_repository)
        leaderboard_service = LeaderboardService(leaderboard_repository)
        score_service = ScoreService()
        game_service = QuizGameService(
            score_service=score_service,
            leaderboard_service=leaderboard_service,
            save_callback=leaderboard_service.save_result,
        )
        timer = Timer()

        if len(sys.argv) > 1 and sys.argv[1].lower() == "leaderboard":
            print(render_leaderboard(leaderboard_service.get_top_scores()))
            return 0

        if len(sys.argv) > 1 and sys.argv[1].lower() == "gui":
            from gui import run_gui
            return run_gui(DB_PATH)

        print(WELCOME_TEXT)
        user = authenticate(auth_service)

        while True:
            print("\nHauptmenü")
            print("1. Singleplayer")
            print("2. Mehrspieler")
            print("3. Rangliste anzeigen")
            print("4. Hilfe")
            print("5. Beenden")

            choice = input("Auswahl: ").strip().lower()

            if choice == "1":
                run_singleplayer(user, question_service, game_service, timer)
            elif choice == "2":
                run_multiplayer(auth_service, question_service, game_service, timer)
            elif choice == "3":
                print(render_leaderboard(leaderboard_service.get_top_scores()))
            elif choice == "4" or choice == "h":
                print(render_help())
            elif choice == "5":
                print("Programm beendet.")
                return 0
            else:
                print("Ungültige Auswahl.")


if __name__ == "__main__":
    raise SystemExit(run_cli())