from game import Game

def test_points():
    g = Game("Test", [])
    g.score = 20
    assert g.score == 20

