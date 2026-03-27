import time

class Game:
    def __init__(self, player_name, questions):
        self.player_name = player_name
        self.questions = questions
        self.score = 0

    def play(self):
        print(f"\nWillkommen {self.player_name}! Viel Erfolg!\n")

        for q in self.questions:
            print(f"Frage: {q['question']}")
            for i, ans in enumerate(q["answers"]):
                print(f"{i+1}. {ans}")

            start = time.time()
            answer = input("Deine Antwort (1-4): ")
            end = time.time()

            if not answer.isdigit() or int(answer) not in range(1, 5):
                print("Ungültige Eingabe. Frage wird übersprungen.\n")
                continue

            if int(answer) - 1 == q["correct"]:
                points = 10
                if end - start < 5:
                    points += 5
                self.score += points
                print(f"Richtig! +{points} Punkte\n")
            else:
                print("Falsch!\n")

        return self.score

