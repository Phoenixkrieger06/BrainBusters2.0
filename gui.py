from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog

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
)
from brainbuster.ui import render_leaderboard


class BrainBusterGui:
    def __init__(self, db_path: Path) -> None:
        initialize_database(db_path)

        self.connection = get_connection(db_path)
        self.user_repository = UserRepository(self.connection)
        self.category_repository = CategoryRepository(self.connection)
        self.question_repository = QuestionRepository(self.connection)
        self.leaderboard_repository = LeaderboardRepository(self.connection)

        self.auth_service = AuthService(self.user_repository)
        self.question_service = QuestionService(self.category_repository, self.question_repository)
        self.leaderboard_service = LeaderboardService(self.leaderboard_repository)
        self.score_service = ScoreService()
        self.game_service = QuizGameService(
            score_service=self.score_service,
            leaderboard_service=self.leaderboard_service,
            save_callback=self.leaderboard_service.save_result,
        )

        self.root = tk.Tk()
        self.root.title("BrainBuster")
        self.root.geometry("700x500")

        self.user = None
        self.categories = self.question_service.get_categories()
        self.current_questions = []
        self.current_index = 0
        self.selected_answers: list[tuple[int, float]] = []

        self.status_var = tk.StringVar(value="Nicht angemeldet")
        self.question_var = tk.StringVar(value="Willkommen bei BrainBuster")
        self.category_var = tk.StringVar()
        self.answer_var = tk.IntVar(value=-1)

        if self.categories:
            self.category_var.set(self.categories[0].name)

        self.option_buttons: list[tk.Radiobutton] = []
        self.build_ui()

    def build_ui(self) -> None:
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, textvariable=self.status_var, anchor="w").pack(fill="x")
        tk.Button(frame, text="Login / Registrierung", command=self.login).pack(fill="x", pady=(8, 8))

        category_names = [category.name for category in self.categories] or ["Keine Kategorien"]
        tk.OptionMenu(frame, self.category_var, *category_names).pack(fill="x")
        tk.Button(frame, text="Spiel starten", command=self.start_game).pack(fill="x", pady=(8, 12))

        tk.Label(frame, textvariable=self.question_var, wraplength=650, justify="left").pack(fill="x", pady=(8, 8))

        for index in range(4):
            button = tk.Radiobutton(frame, variable=self.answer_var, value=index, anchor="w", justify="left")
            button.pack(fill="x", anchor="w")
            self.option_buttons.append(button)

        tk.Button(frame, text="Antwort bestätigen", command=self.next_question).pack(fill="x", pady=(10, 6))
        tk.Button(frame, text="Rangliste anzeigen", command=self.show_leaderboard).pack(fill="x")

    def login(self) -> None:
        username = simpledialog.askstring("Login", "Benutzername:", parent=self.root)
        if not username:
            return

        password = simpledialog.askstring("Login", "Passwort:", parent=self.root, show="*")
        if password is None:
            return

        user = self.auth_service.login(username, password)
        if user is None:
            create = messagebox.askyesno("Account nicht gefunden", "Account nicht gefunden. Neu anlegen?", parent=self.root)
            if not create:
                return
            try:
                user = self.auth_service.register(username, password)
            except Exception as error:
                messagebox.showerror("Fehler", str(error), parent=self.root)
                return

        self.user = user
        self.status_var.set(f"Angemeldet als {self.user.username}")

    def start_game(self) -> None:
        if self.user is None:
            messagebox.showinfo("Hinweis", "Bitte zuerst anmelden.", parent=self.root)
            return

        category_name = self.category_var.get()
        category = next((item for item in self.categories if item.name == category_name), None)
        if category is None:
            messagebox.showerror("Fehler", "Ungültige Kategorie.", parent=self.root)
            return

        self.current_questions = self.question_service.get_questions_for_category(category.id, amount=5)
        if not self.current_questions:
            messagebox.showinfo("Hinweis", "Für diese Kategorie sind keine Fragen vorhanden.", parent=self.root)
            return

        self.current_index = 0
        self.selected_answers = []
        self.show_current_question()

    def show_current_question(self) -> None:
        question = self.current_questions[self.current_index]
        self.answer_var.set(-1)
        self.question_var.set(f"Frage {self.current_index + 1}: {question.text}")

        for index, option in enumerate(question.options):
            self.option_buttons[index].config(text=option)

    def next_question(self) -> None:
        if not self.current_questions:
            return

        if self.answer_var.get() == -1:
            messagebox.showinfo("Hinweis", "Bitte zuerst eine Antwort auswählen.", parent=self.root)
            return

        self.selected_answers.append((self.answer_var.get(), 2.0))
        self.current_index += 1

        if self.current_index >= len(self.current_questions):
            self.finish_game()
        else:
            self.show_current_question()

    def finish_game(self) -> None:
        answers_iter = iter(self.selected_answers)

        def callback(question, question_number):
            return next(answers_iter)

        result, _ = self.game_service.play_round(
            username=self.user.username,
            user_id=self.user.id,
            mode="GUI",
            questions=self.current_questions,
            answer_callback=callback,
        )

        messagebox.showinfo(
            "Spiel beendet",
            f"Punkte: {result.score}\n"
            f"Richtige Antworten: {result.correct_answers}/{result.total_questions}",
            parent=self.root,
        )
        self.show_leaderboard()
        self.current_questions = []
        self.question_var.set("Spiel beendet. Du kannst ein neues Spiel starten.")

    def show_leaderboard(self) -> None:
        entries = self.leaderboard_service.get_top_scores()
        messagebox.showinfo("Rangliste", render_leaderboard(entries), parent=self.root)

    def run(self) -> int:
        self.root.mainloop()
        self.connection.close()
        return 0


def run_gui(db_path: Path | str) -> int:
    app = BrainBusterGui(Path(db_path))
    return app.run()


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    raise SystemExit(run_gui(project_root / "data" / "brainbuster.db"))