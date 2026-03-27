import json

class QuestionRepository:
    @staticmethod
    def load_questions(category):
        with open("data/questions.json", "r", encoding="utf-8") as f:
            all_questions = json.load(f)

        return [q for q in all_questions if q["category"] == category]
