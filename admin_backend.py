from __future__ import annotations

from pathlib import Path

from brainbuster.database import get_connection, initialize_database
from brainbuster.repositories import CategoryRepository, QuestionRepository
from brainbuster.services import OpenTriviaService

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "brainbuster.db"


def ask_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Eingabe darf nicht leer sein.")


def ask_int(
    prompt: str,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    while True:
        raw = input(prompt).strip()
        if raw.isdigit():
            value = int(raw)
            if (min_value is None or value >= min_value) and (
                max_value is None or value <= max_value
            ):
                return value
        print("Ungültige Eingabe.")


def ask_from_allowed_ids(prompt: str, allowed_ids: list[int]) -> int:
    while True:
        raw = input(prompt).strip()
        if raw.isdigit():
            value = int(raw)
            if value in allowed_ids:
                return value
        print(f"Bitte wähle eine gültige ID aus: {allowed_ids}")


def list_categories(category_repository: CategoryRepository) -> None:
    print("\nKategorien")
    categories = category_repository.list_categories()
    if not categories:
        print("Keine Kategorien vorhanden.")
        return

    for category in categories:
        print(f"{category.id}. {category.name}")


def create_category(category_repository: CategoryRepository) -> None:
    name = ask_non_empty("Neuer Kategoriename: ")
    try:
        category = category_repository.create_category(name)
        print(f"Kategorie erstellt: {category.id} - {category.name}")
    except Exception as error:
        print(f"Kategorie konnte nicht erstellt werden: {error}")


def list_questions(question_repository: QuestionRepository) -> None:
    print("\nFragen")
    questions = question_repository.list_all_questions()
    if not questions:
        print("Keine Fragen vorhanden.")
        return

    for question in questions:
        correct_answer = question.options[question.correct_index]
        print(f"{question.id}. [{question.category_name}] {question.text}")
        print(f"   Antworten: {question.options}")
        print(f"   Richtig: {correct_answer} | Schwierigkeit: {question.difficulty}")


def create_question(
    category_repository: CategoryRepository,
    question_repository: QuestionRepository,
) -> None:
    categories = category_repository.list_categories()
    if not categories:
        print("Es existieren keine Kategorien.")
        return

    list_categories(category_repository)
    allowed_ids = [category.id for category in categories if category.id is not None]
    category_id = ask_from_allowed_ids("Kategorie-ID: ", allowed_ids)

    text = ask_non_empty("Fragetext: ")
    options = [ask_non_empty(f"Antwort {index}: ") for index in range(1, 5)]
    correct_index = ask_int("Index der richtigen Antwort (1-4): ", 1, 4) - 1
    difficulty = ask_non_empty("Schwierigkeit (easy/medium/hard): ")

    question = question_repository.create_question(
        category_id,
        text,
        options,
        correct_index,
        difficulty,
    )
    print(f"Frage erstellt: {question.id}")


def update_question(question_repository: QuestionRepository) -> None:
    questions = question_repository.list_all_questions()
    if not questions:
        print("Keine Fragen vorhanden.")
        return

    list_questions(question_repository)
    allowed_ids = [question.id for question in questions if question.id is not None]
    question_id = ask_from_allowed_ids("ID der zu bearbeitenden Frage: ", allowed_ids)

    text = ask_non_empty("Neuer Fragetext: ")
    options = [ask_non_empty(f"Neue Antwort {index}: ") for index in range(1, 5)]
    correct_index = ask_int("Index der richtigen Antwort (1-4): ", 1, 4) - 1
    difficulty = ask_non_empty("Neue Schwierigkeit: ")

    question_repository.update_question(
        question_id,
        text,
        options,
        correct_index,
        difficulty,
    )
    print("Frage aktualisiert.")


def delete_question(question_repository: QuestionRepository) -> None:
    questions = question_repository.list_all_questions()
    if not questions:
        print("Keine Fragen vorhanden.")
        return

    list_questions(question_repository)
    allowed_ids = [question.id for question in questions if question.id is not None]
    question_id = ask_from_allowed_ids("ID der zu löschenden Frage: ", allowed_ids)

    question_repository.delete_question(question_id)
    print("Frage gelöscht.")


def import_opentdb_categories(category_repository: CategoryRepository) -> None:
    api_categories = OpenTriviaService.fetch_categories()
    if not api_categories:
        print("Kategorien konnten nicht von Open Trivia DB geladen werden.")
        return

    existing_names = {category.name for category in category_repository.list_categories()}
    imported = 0
    skipped = 0

    for item in api_categories:
        name = str(item["name"])
        if name in existing_names:
            skipped += 1
            continue

        try:
            category_repository.create_category(name)
            existing_names.add(name)
            imported += 1
        except Exception:
            skipped += 1

    print(f"{imported} Kategorien importiert, {skipped} übersprungen.")


def show_opentdb_categories() -> list[dict[str, object]]:
    api_categories = OpenTriviaService.fetch_categories()
    if not api_categories:
        print("Kategorien konnten nicht von Open Trivia DB geladen werden.")
        return []

    print("\nOpen Trivia DB Kategorien")
    for item in api_categories:
        print(f"{item['id']}. {item['name']}")

    return api_categories


def import_opentdb_questions(
    category_repository: CategoryRepository,
    question_repository: QuestionRepository,
) -> None:
    api_categories = show_opentdb_categories()
    if not api_categories:
        return

    allowed_ids = [int(item["id"]) for item in api_categories]
    api_category_id = ask_from_allowed_ids("Open Trivia Kategorie-ID: ", allowed_ids)
    amount = ask_int("Wie viele Fragen importieren? (1-20): ", 1, 20)

    selected = next(item for item in api_categories if int(item["id"]) == api_category_id)
    category_name = str(selected["name"])

    questions = OpenTriviaService.fetch_questions(
        amount=amount,
        category_id=api_category_id,
    )
    if not questions:
        print("Es konnten keine Fragen geladen werden.")
        return

    local_categories = category_repository.list_categories()
    local_category = next((cat for cat in local_categories if cat.name == category_name), None)

    if local_category is None:
        local_category = category_repository.create_category(category_name)

    imported = 0
    for question in questions:
        question_repository.create_question(
            category_id=local_category.id,
            text=question.text,
            options=question.options,
            correct_index=question.correct_index,
            difficulty=question.difficulty,
        )
        imported += 1

    print(f"{imported} Fragen aus Open Trivia DB importiert.")


def run_backend() -> int:
    initialize_database(DB_PATH)

    with get_connection(DB_PATH) as connection:
        category_repository = CategoryRepository(connection)
        question_repository = QuestionRepository(connection)

        while True:
            print("\nAdmin-Backend")
            print("1. Kategorien anzeigen")
            print("2. Kategorie erstellen")
            print("3. Fragen anzeigen")
            print("4. Frage erstellen")
            print("5. Frage bearbeiten")
            print("6. Frage löschen")
            print("7. Open Trivia Kategorien importieren")
            print("8. Open Trivia Fragen importieren")
            print("9. Beenden")

            choice = input("Auswahl: ").strip()

            if choice == "1":
                list_categories(category_repository)
            elif choice == "2":
                create_category(category_repository)
            elif choice == "3":
                list_questions(question_repository)
            elif choice == "4":
                create_question(category_repository, question_repository)
            elif choice == "5":
                update_question(question_repository)
            elif choice == "6":
                delete_question(question_repository)
            elif choice == "7":
                import_opentdb_categories(category_repository)
            elif choice == "8":
                import_opentdb_questions(category_repository, question_repository)
            elif choice == "9":
                print("Backend beendet.")
                return 0
            else:
                print("Ungültige Auswahl.")


if __name__ == "__main__":
    raise SystemExit(run_backend())
