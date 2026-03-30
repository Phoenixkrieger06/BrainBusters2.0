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
    # Modernes Farbschema
    COLOR_BG = "#0f1419"  # Dark background
    COLOR_PRIMARY = "#6366f1"  # Indigo
    COLOR_SECONDARY = "#8b5cf6"  # Purple
    COLOR_ACCENT = "#ec4899"  # Pink
    COLOR_SUCCESS = "#10b981"  # Green
    COLOR_TEXT = "#ffffff"  # White
    COLOR_TEXT_SECONDARY = "#e5e7eb"  # Light gray
    COLOR_CARD = "#1f2937"  # Dark gray

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
        self.root.title("BrainBuster - Quiz Game")
        self.root.geometry("900x700")
        self.root.configure(bg=self.COLOR_BG)

        # State variables
        self.user = None
        self.player2 = None  # For multiplayer mode
        self.game_mode = None  # "singleplayer" or "multiplayer"
        self.current_player_index = 0  # 0 for player1, 1 for player2
        self.categories = self.question_service.get_categories()
        self.current_questions = []
        self.current_index = 0
        self.selected_answers: list[tuple[int, float]] = []
        self.player1_answers: list[tuple[int, float]] = []
        self.player2_answers: list[tuple[int, float]] = []

        self.status_var = tk.StringVar(value="👤 Nicht angemeldet")
        self.question_var = tk.StringVar(value="Willkommen bei BrainBuster")
        self.category_var = tk.StringVar()
        self.answer_var = tk.IntVar(value=-1)

        if self.categories:
            self.category_var.set(self.categories[0].name)

        self.option_buttons: list[tk.Radiobutton] = []
        self.build_ui()

    def _create_button(self, parent, text, command, bg=None, width=30):
        """Erstellt einen modernen Button mit Hover-Effekt"""
        bg = bg or self.COLOR_PRIMARY
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=self.COLOR_TEXT,
            font=("Arial", 11, "bold"),
            padx=15,
            pady=12,
            border=0,
            cursor="hand2",
            activebackground=self.COLOR_SECONDARY,
            activeforeground=self.COLOR_TEXT,
        )
        # Hover-Effekt
        btn.bind("<Enter>", lambda e: btn.config(bg=self.COLOR_SECONDARY))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    def clear_main_frame(self):
        """Löscht den Inhalt des Main Frames"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def build_ui(self) -> None:
        # Header mit Titel
        header_frame = tk.Frame(self.root, bg=self.COLOR_CARD, height=80)
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)

        title_label = tk.Label(
            header_frame,
            text="🧠 BrainBuster",
            font=("Arial", 28, "bold"),
            bg=self.COLOR_CARD,
            fg=self.COLOR_PRIMARY,
        )
        title_label.pack(side="left", padx=20, pady=15)

        status_label = tk.Label(
            header_frame,
            textvariable=self.status_var,
            font=("Arial", 12),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT_SECONDARY,
        )
        status_label.pack(side="right", padx=20, pady=15)

        # Main content frame (wird manipuliert für verschiedene Screens)
        self.main_frame = tk.Frame(self.root, bg=self.COLOR_BG)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.show_home()

    def show_home(self) -> None:
        """Zeigt den Home Screen mit Login"""
        self.clear_main_frame()

        # Welcome frame
        welcome_frame = tk.Frame(self.main_frame, bg=self.COLOR_CARD, relief="flat")
        welcome_frame.pack(fill="x", padx=10, pady=15)

        welcome_label = tk.Label(
            welcome_frame,
            text="🎮 Willkommen zu BrainBuster!",
            font=("Arial", 20, "bold"),
            bg=self.COLOR_CARD,
            fg=self.COLOR_PRIMARY,
        )
        welcome_label.pack(padx=15, pady=15)

        info_label = tk.Label(
            welcome_frame,
            text="Teste dein Wissen in verschiedenen Kategorien.\nSpiele im Einzel- oder Mehrspielermodus!",
            font=("Arial", 12),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT_SECONDARY,
        )
        info_label.pack(padx=15, pady=(0, 15))

        # Login section
        login_frame = tk.Frame(self.main_frame, bg=self.COLOR_BG)
        login_frame.pack(fill="x", pady=(10, 20))

        login_btn = self._create_button(
            login_frame,
            "🔐 Anmelden / Registrieren",
            self.login,
            bg=self.COLOR_ACCENT,
        )
        login_btn.pack(fill="x", pady=(5, 0))

        leaderboard_btn = self._create_button(
            login_frame,
            "🏆 Rangliste",
            self.show_leaderboard,
            bg=self.COLOR_PRIMARY,
        )
        leaderboard_btn.pack(fill="x", pady=(10, 0))

    def show_mode_selection(self) -> None:
        """Zeigt den Mode Selection Screen"""
        self.clear_main_frame()

        # Title
        title_label = tk.Label(
            self.main_frame,
            text="🎯 Modus wählen",
            font=("Arial", 22, "bold"),
            bg=self.COLOR_BG,
            fg=self.COLOR_PRIMARY,
        )
        title_label.pack(pady=(20, 40))

        # Singleplayer option
        sp_frame = tk.Frame(self.main_frame, bg=self.COLOR_CARD, relief="flat")
        sp_frame.pack(fill="x", padx=10, pady=15)

        sp_label = tk.Label(
            sp_frame,
            text="👤 SINGLEPLAYER",
            font=("Arial", 14, "bold"),
            bg=self.COLOR_CARD,
            fg=self.COLOR_SUCCESS,
        )
        sp_label.pack(padx=15, pady=(15, 8))

        sp_info = tk.Label(
            sp_frame,
            text="Spiele Fragen alleine und versuche Punkte zu sammeln.",
            font=("Arial", 10),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT_SECONDARY,
        )
        sp_info.pack(padx=15, pady=(0, 15))

        sp_btn = self._create_button(sp_frame, "▶ Singleplayer starten", self.start_singleplayer, bg=self.COLOR_SUCCESS)
        sp_btn.pack(fill="x", padx=15, pady=(0, 15))

        # Multiplayer option
        mp_frame = tk.Frame(self.main_frame, bg=self.COLOR_CARD, relief="flat")
        mp_frame.pack(fill="x", padx=10, pady=15)

        mp_label = tk.Label(
            mp_frame,
            text="👥 MEHRSPIELERMODUS",
            font=("Arial", 14, "bold"),
            bg=self.COLOR_CARD,
            fg=self.COLOR_ACCENT,
        )
        mp_label.pack(padx=15, pady=(15, 8))

        mp_info = tk.Label(
            mp_frame,
            text="Tritt gegen einen anderen Spieler an und ermittle den Gewinner!",
            font=("Arial", 10),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT_SECONDARY,
        )
        mp_info.pack(padx=15, pady=(0, 15))

        mp_btn = self._create_button(mp_frame, "▶ Multiplayer starten", self.start_multiplayer_setup, bg=self.COLOR_ACCENT)
        mp_btn.pack(fill="x", padx=15, pady=(0, 15))

        # Back button
        back_btn = self._create_button(self.main_frame, "« Zurück", self.logout, bg=self.COLOR_PRIMARY)
        back_btn.pack(fill="x", padx=10, pady=(20, 0))

    def start_singleplayer(self) -> None:
        """Startet Singleplayer Modus"""
        self.game_mode = "singleplayer"
        self.show_game_setup()

    def start_multiplayer_setup(self) -> None:
        """Setup für Multiplayer - Login für Player 2"""
        self.clear_main_frame()

        title_label = tk.Label(
            self.main_frame,
            text="👥 Spieler 2 - Anmelden",
            font=("Arial", 20, "bold"),
            bg=self.COLOR_BG,
            fg=self.COLOR_ACCENT,
        )
        title_label.pack(pady=(20, 30))

        info_label = tk.Label(
            self.main_frame,
            text=f"Spieler 1: {self.user.username}\n\nSpieler 2 muss sich anmelden:",
            font=("Arial", 12),
            bg=self.COLOR_BG,
            fg=self.COLOR_TEXT_SECONDARY,
        )
        info_label.pack(pady=(0, 20))

        login_btn = self._create_button(
            self.main_frame,
            "🔐 Spieler 2 anmelden",
            self.login_player2,
            bg=self.COLOR_ACCENT,
        )
        login_btn.pack(fill="x", padx=10, pady=(5, 10))

        back_btn = self._create_button(self.main_frame, "« Zurück", self.show_mode_selection, bg=self.COLOR_PRIMARY)
        back_btn.pack(fill="x", padx=10, pady=(10, 0))

    def login_player2(self) -> None:
        """Login für Player 2"""
        username = simpledialog.askstring("Spieler 2 Anmelden", "Benutzername:", parent=self.root)
        if not username:
            return

        password = simpledialog.askstring("Spieler 2 Anmelden", "Passwort:", parent=self.root, show="*")
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

        self.player2 = user
        self.game_mode = "multiplayer"
        self.show_game_setup()

    def show_game_setup(self) -> None:
        """Zeigt die Kategorie Auswahl"""
        self.clear_main_frame()

        title_label = tk.Label(
            self.main_frame,
            text="📚 Kategorie wählen",
            font=("Arial", 20, "bold"),
            bg=self.COLOR_BG,
            fg=self.COLOR_PRIMARY,
        )
        title_label.pack(pady=(20, 30))

        if self.game_mode == "multiplayer":
            mode_label = tk.Label(
                self.main_frame,
                text=f"Spieler 1: {self.user.username}  VS  Spieler 2: {self.player2.username}",
                font=("Arial", 11),
                bg=self.COLOR_BG,
                fg=self.COLOR_ACCENT,
            )
            mode_label.pack(pady=(0, 20))

        category_frame = tk.Frame(self.main_frame, bg=self.COLOR_CARD, relief="flat")
        category_frame.pack(fill="x", padx=10, pady=15)

        category_label = tk.Label(
            category_frame,
            text="Wähle eine Kategorie:",
            font=("Arial", 12, "bold"),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT,
        )
        category_label.pack(anchor="w", padx=15, pady=(12, 8))

        category_names = [category.name for category in self.categories] or ["Keine Kategorien"]
        category_menu = tk.OptionMenu(
            category_frame,
            self.category_var,
            *category_names,
        )
        category_menu.config(
            bg=self.COLOR_SECONDARY,
            fg=self.COLOR_TEXT,
            font=("Arial", 10),
            activebackground=self.COLOR_PRIMARY,
            activeforeground=self.COLOR_TEXT,
            highlightthickness=0,
            relief="flat",
            bd=0,
        )
        category_menu["menu"].config(
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT,
            activebackground=self.COLOR_PRIMARY,
            activeforeground=self.COLOR_TEXT,
        )
        category_menu.pack(fill="x", padx=15, pady=(0, 12))

        button_frame = tk.Frame(self.main_frame, bg=self.COLOR_BG)
        button_frame.pack(fill="x", pady=(20, 10))

        start_btn = self._create_button(button_frame, "▶ Spiel starten", self.start_game, bg=self.COLOR_SUCCESS)
        start_btn.pack(fill="x", padx=10, pady=(0, 10))

        back_btn = self._create_button(button_frame, "« Zurück", self.show_mode_selection, bg=self.COLOR_PRIMARY)
        back_btn.pack(fill="x", padx=10, pady=(0, 0))

    def show_game(self) -> None:
        """Zeigt den Spiel Screen"""
        self.clear_main_frame()

        # Question frame
        question_frame = tk.Frame(self.main_frame, bg=self.COLOR_CARD, relief="flat")
        question_frame.pack(fill="both", expand=True, padx=0, pady=0)

        question_label = tk.Label(
            question_frame,
            textvariable=self.question_var,
            font=("Arial", 13, "bold"),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT,
            wraplength=800,
            justify="left",
        )
        question_label.pack(fill="x", padx=15, pady=(15, 20), anchor="nw")

        # Answer options
        options_frame = tk.Frame(question_frame, bg=self.COLOR_CARD)
        options_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.option_buttons = []
        for index in range(4):
            button_frame = tk.Frame(options_frame, bg=self.COLOR_CARD)
            button_frame.pack(fill="x", pady=8)

            button = tk.Radiobutton(
                button_frame,
                variable=self.answer_var,
                value=index,
                anchor="w",
                justify="left",
                font=("Arial", 11),
                bg=self.COLOR_CARD,
                fg=self.COLOR_TEXT,
                activebackground=self.COLOR_CARD,
                activeforeground=self.COLOR_ACCENT,
                selectcolor=self.COLOR_PRIMARY,
                highlightthickness=0,
            )
            button.pack(fill="x")
            self.option_buttons.append(button)

        # Action buttons frame
        button_frame = tk.Frame(self.main_frame, bg=self.COLOR_BG)
        button_frame.pack(fill="x", pady=(10, 0))

        confirm_btn = self._create_button(button_frame, "✓ Antwort bestätigen", self.next_question, bg=self.COLOR_SUCCESS)
        confirm_btn.pack(fill="x", padx=10, pady=(0, 10))

    def login(self) -> None:
        """Login Methode"""
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
        self.status_var.set(f"👤 {self.user.username}")
        self.show_mode_selection()

    def logout(self) -> None:
        """Logout und zurück zur Home"""
        self.user = None
        self.player2 = None
        self.game_mode = None
        self.status_var.set("👤 Nicht angemeldet")
        self.show_home()

    def start_game(self) -> None:
        """Startet das Spiel"""
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
        self.player1_answers = []
        self.player2_answers = []
        self.current_player_index = 0

        self.show_game()
        self.show_current_question()

    def show_current_question(self) -> None:
        """Zeigt die aktuelle Frage an"""
        question = self.current_questions[self.current_index]
        self.answer_var.set(-1)
        progress = f"Frage {self.current_index + 1}/{len(self.current_questions)}"

        if self.game_mode == "multiplayer":
            current_player = self.user if self.current_player_index == 0 else self.player2
            player_label = f"[{current_player.username}]"
            self.question_var.set(f"{progress} - {player_label}\n{question.text}")
        else:
            self.question_var.set(f"{progress}\n{question.text}")

        for index, option in enumerate(question.options):
            self.option_buttons[index].config(text=f"{chr(65 + index)}  {option}")

    def next_question(self) -> None:
        """Nächste Frage oder Spiel beenden"""
        if not self.current_questions:
            return

        if self.answer_var.get() == -1:
            messagebox.showinfo("Hinweis", "Bitte zuerst eine Antwort auswählen.", parent=self.root)
            return

        self.selected_answers.append((self.answer_var.get(), 2.0))

        self.current_index += 1

        if self.current_index >= len(self.current_questions):
            if self.game_mode == "singleplayer":
                self.finish_singleplayer_game()
            else:
                self.switch_player_multiplayer()
        else:
            self.show_current_question()

    def switch_player_multiplayer(self) -> None:
        """Wechselt zu Spieler 2 im Multiplayer"""
        if self.current_player_index == 0:
            # Spieler 1 fertig, Speichern seiner Antworten
            self.player1_answers = self.selected_answers.copy()
            # Spieler 2 starten
            self.current_player_index = 1
            self.selected_answers = []
            self.current_index = 0
            messagebox.showinfo(
                "👤 Spieler 2 ist dran",
                f"Spieler 1: {self.user.username} fertig!\n\n" + 
                f"Spieler 2: {self.player2.username} kann jetzt spielen!",
                parent=self.root,
            )
            self.show_current_question()
        else:
            # Beide Spieler fertig
            self.player2_answers = self.selected_answers.copy()
            self.finish_multiplayer_game()

    def finish_singleplayer_game(self) -> None:
        """Beendet Singleplayer Spiel"""
        answers_iter = iter(self.selected_answers)

        def callback(question, question_number):
            return next(answers_iter)

        result, _ = self.game_service.play_round(
            username=self.user.username,
            user_id=self.user.id,
            mode="Singleplayer",
            questions=self.current_questions,
            answer_callback=callback,
        )

        result_text = f"""
🎉 SPIEL BEENDET 🎉

━━━━━━━━━━━━━━━━━━━
📊 Dein Ergebnis:
🏆 Punkte: {result.score}
✓ Richtig: {result.correct_answers}/{result.total_questions}
━━━━━━━━━━━━━━━━━━━
        """

        messagebox.showinfo("Spiel beendet", result_text, parent=self.root)
        self.show_mode_selection()

    def finish_multiplayer_game(self) -> None:
        """Beendet Multiplayer Spiel"""
        # Ergebnisse für beide Spieler berechnen
        answers_iter1 = iter(self.player1_answers)

        def callback1(question, question_number):
            return next(answers_iter1)

        result1, _ = self.game_service.play_round(
            username=self.user.username,
            user_id=self.user.id,
            mode="Multiplayer",
            questions=self.current_questions,
            answer_callback=callback1,
        )

        answers_iter2 = iter(self.player2_answers)

        def callback2(question, question_number):
            return next(answers_iter2)

        result2, _ = self.game_service.play_round(
            username=self.player2.username,
            user_id=self.player2.id,
            mode="Multiplayer",
            questions=self.current_questions,
            answer_callback=callback2,
        )

        # Gewinner ermitteln
        if result1.score > result2.score:
            winner = f"🥇 {self.user.username}"
            winner_score = result1.score
        elif result2.score > result1.score:
            winner = f"🥇 {self.player2.username}"
            winner_score = result2.score
        else:
            winner = "🤝 Unentschieden!"
            winner_score = result1.score

        result_text = f"""
🎉 MULTIPLAYER VORBEI 🎉

━━━━━━━━━━━━━━━━━━━
👤 {self.user.username}
Punkte: {result1.score}
Richtig: {result1.correct_answers}/{result1.total_questions}

VS

👤 {self.player2.username}
Punkte: {result2.score}
Richtig: {result2.correct_answers}/{result2.total_questions}

━━━━━━━━━━━━━━━━━━━
🏆 SIEGER: {winner}
━━━━━━━━━━━━━━━━━━━
        """

        messagebox.showinfo("Spiel beendet", result_text, parent=self.root)
        self.show_mode_selection()

    def show_leaderboard(self) -> None:
        """Zeigt die Rangliste"""
        entries = self.leaderboard_service.get_top_scores()
        leaderboard_text = render_leaderboard(entries)
        messagebox.showinfo("🏆 Rangliste", leaderboard_text, parent=self.root)

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