import json
import os

class Ranking:
    FILE = "ranking.json"

    @staticmethod
    def save_score(name, score):
        if os.path.exists(Ranking.FILE):
            with open(Ranking.FILE, "r") as f:
                data = json.load(f)
        else:
            data = []

        data.append({"name": name, "score": score})
        data = sorted(data, key=lambda x: x["score"], reverse=True)

        with open(Ranking.FILE, "w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def show():
        if not os.path.exists(Ranking.FILE):
            print("Noch keine Einträge vorhanden.")
            return

        with open(Ranking.FILE, "r") as f:
            data = json.load(f)

        print("\n🏆 Rangliste:")
        for i, entry in enumerate(data[:10]):
            print(f"{i+1}. {entry['name']} – {entry['score']} Punkte")

