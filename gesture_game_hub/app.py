from flask import Flask, render_template, jsonify
import subprocess
import sys
import os

app = Flask(__name__)

GAMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "games")

GAME_MAP = {
    "1": "snake_game.py",
    "2": "tictactoe_air.py",
    "3": "dino_game.py",
    "4": "space_shooter.py",
    "5": "gesture_meteor.py",
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/launch/<game_id>")
def launch(game_id):
    filename = GAME_MAP.get(game_id)
    if not filename:
        return jsonify({"status": "error", "message": "Game not found"}), 400
    game_path = os.path.join(GAMES_DIR, filename)
    if not os.path.exists(game_path):
        return jsonify({"status": "error", "message": f"{filename} does not exist"}), 404
    subprocess.Popen([sys.executable, game_path])
    return jsonify({"status": "ok", "launched": filename})

if __name__ == "__main__":
    app.run(debug=True)
