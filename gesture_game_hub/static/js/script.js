// =============================================
//  Gesture Game Hub - script.js
// =============================================

const GAME_NAMES = {
  "1": "Snake Game",
  "2": "Tic Tac Toe",
  "3": "Dino Runner",
  "4": "Space Shooter",
  "5": "Gesture Meteor"
};

// how many frames the same finger count must be held before triggering
const HOLD_FRAMES  = 40;

let lastFingerCount  = 0;
let holdCounter      = 0;
let countdownTimer   = null;
let launchLocked     = false;   // prevents double-launches

// ── DOM refs ──────────────────────────────────
const video          = document.getElementById("webcam");
const fingerDisplay  = document.getElementById("finger-count");
const gameNameEl     = document.getElementById("game-name");
const countdownBox   = document.getElementById("countdown-box");
const countdownNum   = document.getElementById("countdown-number");
const camStatus      = document.getElementById("cam-status");

// ── MediaPipe Hands setup ─────────────────────
const mpHands = new Hands({
  locateFile: (file) =>
    `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
});

mpHands.setOptions({
  maxNumHands: 1,
  modelComplexity: 0,          // 0 = faster, good enough
  minDetectionConfidence: 0.75,
  minTrackingConfidence: 0.6
});

mpHands.onResults(onResults);

// ── Start webcam ──────────────────────────────
const camera = new Camera(video, {
  onFrame: async () => {
    await mpHands.send({ image: video });
  },
  width: 480,
  height: 360
});

camera.start()
  .then(() => {
    camStatus.textContent = "✅ Camera active — show fingers!";
  })
  .catch((err) => {
    camStatus.textContent = "❌ Camera error: " + err.message;
  });

// ── Count extended fingers ────────────────────
function countFingers(landmarks) {
  // tip landmarks:   thumb=4, index=8, middle=12, ring=16, pinky=20
  // pip landmarks:   thumb=3, index=6, middle=10, ring=14, pinky=18

  const tips = [8, 12, 16, 20];
  const pips = [6, 10, 14, 18];

  let count = 0;

  // four fingers: tip y < pip y means extended (y is inverted in image)
  for (let i = 0; i < tips.length; i++) {
    if (landmarks[tips[i]].y < landmarks[pips[i]].y) {
      count++;
    }
  }

  // thumb: compare x axis (right hand: tip.x < pip.x means extended)
  if (landmarks[4].x < landmarks[3].x) {
    count++;
  }

  return count;
}

// ── Handle MediaPipe results ──────────────────
function onResults(results) {
  if (launchLocked) return;

  if (!results.multiHandLandmarks || results.multiHandLandmarks.length === 0) {
    // no hand — reset
    resetGestureState();
    return;
  }

  const landmarks  = results.multiHandLandmarks[0];
  const fingers    = countFingers(landmarks);

  // update display
  fingerDisplay.textContent = fingers;
  gameNameEl.textContent    = GAME_NAMES[fingers] || "Unknown gesture";

  // highlight matching card
  highlightCard(fingers);

  // hold detection: same count for HOLD_FRAMES frames = launch
  if (fingers === lastFingerCount && fingers >= 1 && fingers <= 5) {
    holdCounter++;
    if (holdCounter >= HOLD_FRAMES) {
      holdCounter = 0;
      startCountdown(String(fingers));
    }
  } else {
    lastFingerCount = fingers;
    holdCounter     = 0;
  }
}

// ── Highlight active card ─────────────────────
function highlightCard(num) {
  document.querySelectorAll(".card").forEach(c => c.classList.remove("active"));
  const card = document.getElementById("card-" + num);
  if (card) card.classList.add("active");
}

// ── Reset gesture state ───────────────────────
function resetGestureState() {
  fingerDisplay.textContent = "—";
  gameNameEl.textContent    = "Show a finger to begin";
  holdCounter               = 0;
  lastFingerCount           = 0;
  document.querySelectorAll(".card").forEach(c => c.classList.remove("active"));
}

// ── Countdown then launch ─────────────────────
function startCountdown(gameId) {
  if (launchLocked) return;
  launchLocked = true;

  countdownBox.classList.remove("hidden");
  let seconds = 3;
  countdownNum.textContent = seconds;

  countdownTimer = setInterval(() => {
    seconds--;
    countdownNum.textContent = seconds;
    if (seconds <= 0) {
      clearInterval(countdownTimer);
      launchGame(gameId);
    }
  }, 1000);
}

// ── Call Flask to launch game ─────────────────
function launchGame(gameId) {
  countdownBox.classList.add("hidden");

  fetch(`/launch/${gameId}`)
    .then(res => res.json())
    .then(data => {
      if (data.status === "ok") {
        gameNameEl.textContent = "✅ " + GAME_NAMES[gameId] + " launched!";
      } else {
        gameNameEl.textContent = "❌ Error: " + data.message;
      }
    })
    .catch(() => {
      gameNameEl.textContent = "❌ Could not reach server.";
    })
    .finally(() => {
      // allow launching again after 3 seconds
      setTimeout(() => {
        launchLocked = false;
        resetGestureState();
      }, 3000);
    });
}

// ── Cancel countdown ──────────────────────────
function cancelLaunch() {
  clearInterval(countdownTimer);
  countdownBox.classList.add("hidden");
  launchLocked = false;
  resetGestureState();
}

// ── Manual click launch (from card click) ─────
function manualLaunch(gameId) {
  if (launchLocked) return;
  fingerDisplay.textContent = gameId;
  gameNameEl.textContent    = GAME_NAMES[gameId];
  highlightCard(parseInt(gameId));
  startCountdown(gameId);
}
