from flask import Flask, render_template, jsonify
import subprocess
import sys
import os
import time
import threading

app = Flask(__name__)

GAMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "games")

GAME_MAP = {
    "1": "snake_game.py",
    "2": "tictactoe_air.py",
    "3": "dino_game.py",
    "4": "space_shooter.py",
    "5": "gesture_meteor.py",
}

current_process = None

def focus_game_window(title_keywords):
    """Wait for game window to appear then bring it to front (Windows only)."""
    if sys.platform != "win32":
        return
    time.sleep(2)   # wait for pygame window to appear
    try:
        import ctypes
        # EnumWindows to find the pygame window and focus it
        user32 = ctypes.windll.user32

        found_hwnd = [None]

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        def enum_callback(hwnd, lparam):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.lower()
                if any(k.lower() in title for k in title_keywords):
                    found_hwnd[0] = hwnd
                    return False   # stop enumeration
            return True

        user32.EnumWindows(enum_callback, 0)

        if found_hwnd[0]:
            # bring window to foreground
            user32.ShowWindow(found_hwnd[0], 9)         # SW_RESTORE
            user32.SetForegroundWindow(found_hwnd[0])
            user32.BringWindowToTop(found_hwnd[0])
    except Exception as e:
        print(f"[Focus Error] {e}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/launch/<game_id>")
def launch(game_id):
    global current_process

    filename = GAME_MAP.get(game_id)
    if not filename:
        return jsonify({"status": "error", "message": "Game not found"}), 400

    game_path = os.path.join(GAMES_DIR, filename)
    if not os.path.exists(game_path):
        return jsonify({"status": "error", "message": f"{filename} does not exist"}), 404

    # kill previous game
    if current_process is not None:
        try:
            current_process.terminate()
            current_process.wait(timeout=3)
        except Exception:
            try:
                current_process.kill()
            except Exception:
                pass
        current_process = None

    time.sleep(0.3)

    # launch game
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE

    current_process = subprocess.Popen([sys.executable, game_path], **kwargs)

    # focus the window in background thread using game name as title keyword
    game_name = os.path.splitext(filename)[0].replace("_", " ")
    threading.Thread(
        target=focus_game_window,
        args=([game_name, "pygame", "gesture"],),
        daemon=True
    ).start()

    return jsonify({"status": "ok", "launched": filename})


@app.route("/stop")
def stop():
    global current_process
    if current_process is not None:
        try:
            current_process.terminate()
            current_process.wait(timeout=3)
        except Exception:
            pass
        current_process = None
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True)