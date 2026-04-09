from __future__ import annotations

from typing import Iterable

from brainbuster.models import Achievement, GameResult, Question

WELCOME_TEXT = """
Willkommen bei BrainBuster.
Teste dein Wissen in verschiedenen Kategorien und sammle Punkte.
""".strip()

HELP_TEXT = """
BrainBuster Steuerung
=====================
python main.py             -> Spiel starten
python main.py h           -> Hilfe anzeigen
python main.py leaderboard -> Rangliste anzeigen
python main.py gui         -> Grafische Oberfläche starten
python admin_backend.py    -> Kategorien und Fragen verwalten

Steuerung im Spiel:
- Gib die Zahl der gewünschten Antwort ein.
- Bestätige mit Enter.
- Nach jedem Spiel wird automatisch die Rangliste angezeigt.
""".strip()


def render_help() -> str:
    return HELP_TEXT


def render_categories(categories: Iterable[object]) -> str:
    lines = ["Verfügbare Kategorien:"]
    for category in categories:
        lines.append(f"{category.id}. {category.name}")
    return "\n".join(lines)


def render_question(question: Question, question_number: int) -> str:
    lines = [f"\nFrage {question_number}: [{question.category_name}] {question.text}"]
    for index, option in enumerate(question.options, start=1):
        lines.append(f"  {index}. {option}")
    return "\n".join(lines)


def render_achievements(achievements: list[Achievement]) -> str:
    if not achievements:
        return "Keine Achievements freigeschaltet."

    lines = ["Freigeschaltete Achievements:"]
    for achievement in achievements:
        lines.append(f"- {achievement.title}: {achievement.description}")
    return "\n".join(lines)


def render_result(result: GameResult) -> str:
    return (
        f"\nSpiel beendet für {result.username}\n"
        f"Modus: {result.mode}\n"
        f"Punkte: {result.score}\n"
        f"Richtige Antworten: {result.correct_answers}/{result.total_questions}\n"
        f"Durchschnittliche Antwortzeit: {result.average_response_seconds:.2f} Sekunden\n"
        f"{render_achievements(result.achievements)}"
    )


def render_leaderboard(entries: list[dict[str, object]]) -> str:
    if not entries:
        return "Noch keine Einträge in der Rangliste vorhanden."

    lines = ["\nGlobale Rangliste", "================="]
    for position, entry in enumerate(entries, start=1):
        lines.append(
            f"{position:>2}. {entry['username']:<15} "
            f"{entry['score']:>4} Punkte | "
            f"{entry['mode']:<12} | "
            f"{entry['correct_answers']}/{entry['total_questions']} richtig | "
            f"Ø {entry['average_response_seconds']:.2f}s"
        )
    return "\n".join(lines)
