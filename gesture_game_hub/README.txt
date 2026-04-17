============================
 GESTURE GAME HUB - README
============================

FOLDER STRUCTURE:
-----------------
gesture_game_hub/
  app.py                      ← Flask backend
  templates/
    index.html                ← main webpage
  static/
    css/style.css             ← styling
    js/script.js              ← gesture detection + launch logic
    images/                   ← game preview images
  games/
    snake_game.py
    tictactoe_air.py
    dino_game.py
    space_shooter.py
    gesture_meteor.py

SETUP:
------
1. Install dependencies:
   pip install flask opencv-python mediapipe pygame

2. Copy your game files into the games/ folder

3. Run the Flask server:
   python app.py

4. Open browser at:
   http://127.0.0.1:5000

HOW TO USE:
-----------
- Allow camera access when browser asks
- Show fingers in front of camera:
    1 finger  → Snake Game
    2 fingers → Tic Tac Toe
    3 fingers → Dino Runner
    4 fingers → Space Shooter
    5 fingers → Gesture Meteor
- Hold the gesture steady for ~2 seconds
- A 3-second countdown appears, then the game launches
- You can also click any game card directly to launch it

NOTES:
------
- Games launch as separate Python processes (non-blocking)
- Gesture detection runs in the browser using MediaPipe JS
- No extra Python gesture detection needed for the hub
