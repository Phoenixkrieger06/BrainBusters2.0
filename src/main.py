import sys
from game import Game
from question_repository import QuestionRepository
from ranking import Ranking

def show_help():
    print("""
BrainBuster – Hilfe (-h)

Starten:
    python src/main.py

Funktionen:
    - Kategorien auswählen
    - Fragen beantworten
    - Punkte sammeln
    - Rangliste am Ende anzeigen
""")

def main():
    if "-h" in sys.argv:
        show_help()
        return

    print("=== BrainBuster ===")
    name = input("Dein Name: ")

    print("\nKategorien:")
    print("1. Allgemeinwissen")
    print("2. Technik")

    choice = input("Kategorie wählen (1-2): ")

    categories = {
        "1": "Allgemeinwissen",
        "2": "Technik"
    }

    if choice not in categories:
        print("Ungültige Kategorie.")
        return

    questions = QuestionRepository.load_questions(categories[choice])
    game = Game(name, questions)
    score = game.play()

    print(f"\nSpiel beendet! Du hast {score} Punkte erreicht.")
    Ranking.save_score(name, score)
    Ranking.show()

if __name__ == "__main__":
    main()

