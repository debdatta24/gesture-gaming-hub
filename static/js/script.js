const GAME_NAMES = {
  "1": "Snake Game",
  "2": "Tic Tac Toe",
  "3": "Dino Runner",
  "4": "Space Shooter",
  "5": "Gesture Meteor"
};

const HOLD_FRAMES = 40;

let lastFingerCount = 0;
let holdCounter     = 0;
let countdownTimer  = null;
let launchLocked    = false;
let mpCamera        = null;
let gameRunning     = false;
let cameraEnabled   = true;

const video         = document.getElementById("webcam");
const fingerDisplay = document.getElementById("finger-count");
const gameNameEl    = document.getElementById("game-name");
const countdownBox  = document.getElementById("countdown-box");
const countdownNum  = document.getElementById("countdown-number");
const camStatus     = document.getElementById("cam-status");

// block browser from stealing keys while game runs
document.addEventListener("keydown", function(e) {
  if (gameRunning) e.preventDefault();
});

// ── Camera controls ───────────────────────────
function startCamera() {
  if (!cameraEnabled) return;

  mpCamera = new Camera(video, {
    onFrame: async () => {
      await mpHands.send({ image: video });
    },
    width: 640,
    height: 480
  });

  mpCamera.start()
    .then(() => {
      camStatus.textContent = "Camera active -- show fingers or click a card!";
    })
    .catch((err) => {
      cameraEnabled = false;
      camStatus.textContent = "No camera -- click a game card to play.";
      updateCameraToggle();
    });
}

function stopCamera() {
  if (mpCamera) { mpCamera.stop(); mpCamera = null; }
  if (video.srcObject) {
    video.srcObject.getTracks().forEach(t => t.stop());
    video.srcObject = null;
  }
  camStatus.textContent = "Camera paused -- game is running";
}

function restartCamera() {
  gameRunning = false;
  if (!cameraEnabled) {
    launchLocked = false;
    resetGestureState();
    return;
  }
  camStatus.textContent = "Restarting camera...";
  setTimeout(() => {
    startCamera();
    launchLocked = false;
    resetGestureState();
  }, 2000);
}

// ── Camera toggle button ──────────────────────
function addCameraToggle() {
  const btn = document.createElement("button");
  btn.id = "cam-toggle-btn";
  btn.textContent = "Turn Camera Off";
  btn.style.cssText = `
    display:block; margin: 10px auto 0;
    background: rgba(255,62,108,0.1); border: 1px solid #ff3e6c;
    color: #ff3e6c; padding: 7px 18px; border-radius: 8px;
    cursor: pointer; font-size: 0.8rem; font-family: 'Poppins', sans-serif;
    transition: background 0.2s;
  `;
  btn.onclick = toggleCamera;
  document.querySelector(".camera-box").appendChild(btn);
}

function updateCameraToggle() {
  const btn = document.getElementById("cam-toggle-btn");
  if (!btn) return;
  if (cameraEnabled) {
    btn.textContent = "Turn Camera Off";
    btn.style.borderColor = "#ff3e6c";
    btn.style.color = "#ff3e6c";
    btn.style.background = "rgba(255,62,108,0.1)";
  } else {
    btn.textContent = "Turn Camera On";
    btn.style.borderColor = "#00e5ff";
    btn.style.color = "#00e5ff";
    btn.style.background = "rgba(0,229,255,0.1)";
  }
}

function toggleCamera() {
  if (cameraEnabled) {
    cameraEnabled = false;
    stopCamera();
    camStatus.textContent = "Camera off -- click a game card to play.";
    fingerDisplay.textContent = "--";
    gameNameEl.textContent = "Click any card below to launch";
  } else {
    cameraEnabled = true;
    startCamera();
  }
  updateCameraToggle();
}

// ── MediaPipe setup ───────────────────────────
const mpHands = new Hands({
  locateFile: (file) =>
    `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
});

mpHands.setOptions({
  maxNumHands: 1,
  modelComplexity: 1,
  minDetectionConfidence: 0.75,
  minTrackingConfidence: 0.6
});

mpHands.onResults(onResults);

// start camera + add toggle button on load
startCamera();
addCameraToggle();

// ── Finger counting ───────────────────────────
function countFingers(landmarks) {
  let count = 0;
  const fingerTips = [8, 12, 16, 20];
  const fingerPips = [6, 10, 14, 18];
  for (let i = 0; i < fingerTips.length; i++) {
    if (landmarks[fingerTips[i]].y < landmarks[fingerPips[i]].y - 0.02) count++;
  }
  const thumbTip  = landmarks[4];
  const indexMcp  = landmarks[5];
  const wrist     = landmarks[0];
  const thumbDist = Math.hypot(thumbTip.x - wrist.x, thumbTip.y - wrist.y);
  const indexDist = Math.hypot(indexMcp.x - wrist.x, indexMcp.y - wrist.y);
  if (thumbDist > indexDist * 0.9) count++;
  return Math.min(count, 5);
}

// ── Handle gesture results ────────────────────
function onResults(results) {
  if (launchLocked) return;
  if (!results.multiHandLandmarks || results.multiHandLandmarks.length === 0) {
    resetGestureState(); return;
  }
  const landmarks = results.multiHandLandmarks[0];
  const fingers   = countFingers(landmarks);
  fingerDisplay.textContent = fingers;
  gameNameEl.textContent    = GAME_NAMES[fingers] || "Hold steady...";
  highlightCard(fingers);
  if (fingers === lastFingerCount && fingers >= 1 && fingers <= 5) {
    holdCounter++;
    if (holdCounter >= HOLD_FRAMES) { holdCounter = 0; startCountdown(String(fingers)); }
  } else {
    lastFingerCount = fingers; holdCounter = 0;
  }
}

function highlightCard(num) {
  document.querySelectorAll(".card").forEach(c => c.classList.remove("active"));
  const card = document.getElementById("card-" + num);
  if (card) card.classList.add("active");
}

function resetGestureState() {
  if (!cameraEnabled) return;
  fingerDisplay.textContent = "--";
  gameNameEl.textContent    = "Show a finger to begin";
  holdCounter = 0; lastFingerCount = 0;
  document.querySelectorAll(".card").forEach(c => c.classList.remove("active"));
}

// ── Countdown ─────────────────────────────────
function startCountdown(gameId) {
  if (launchLocked) return;
  launchLocked = true;
  countdownBox.classList.remove("hidden");
  let seconds = 3;
  countdownNum.textContent = seconds;
  countdownTimer = setInterval(() => {
    seconds--;
    countdownNum.textContent = seconds;
    if (seconds <= 0) { clearInterval(countdownTimer); launchGame(gameId); }
  }, 1000);
}

// ── Launch game ───────────────────────────────
function launchGame(gameId) {
  countdownBox.classList.add("hidden");

  // only stop camera if it was on
  if (cameraEnabled) stopCamera();

  setTimeout(() => {
    fetch("/launch/" + gameId)
      .then(res => res.json())
      .then(data => {
        if (data.status === "ok") {
          gameRunning = true;
          fingerDisplay.textContent = gameId;
          gameNameEl.textContent = GAME_NAMES[gameId] + " is running...";
          highlightCard(parseInt(gameId));
          showReturnButton();
        } else {
          gameNameEl.textContent = "Error: " + data.message;
          restartCamera();
        }
      })
      .catch(() => {
        gameNameEl.textContent = "Could not reach server.";
        restartCamera();
      });
  }, cameraEnabled ? 800 : 100);  // shorter delay if camera was already off
}

// ── Done playing button ───────────────────────
function showReturnButton() {
  const existing = document.getElementById("done-btn");
  if (existing) existing.remove();

  const btn = document.createElement("button");
  btn.id = "done-btn";
  btn.textContent = "Done Playing -- " + (cameraEnabled ? "Restart Camera" : "Back to Hub");
  btn.style.cssText = `
    display:block; margin: 12px auto 0;
    background: rgba(0,229,255,0.1); border: 1px solid #00e5ff;
    color: #00e5ff; padding: 10px 24px; border-radius: 10px;
    cursor: pointer; font-size: 0.9rem; font-family: 'Poppins', sans-serif;
  `;
  btn.onclick = function() {
    btn.remove();
    fetch("/stop");
    gameRunning = false;
    document.querySelectorAll(".card").forEach(c => c.classList.remove("active"));
    if (cameraEnabled) {
      restartCamera();
    } else {
      launchLocked = false;
      fingerDisplay.textContent = "--";
      gameNameEl.textContent = "Click any card below to launch";
    }
  };
  document.querySelector(".gesture-display").appendChild(btn);
}

// ── Cancel countdown ──────────────────────────
function cancelLaunch() {
  clearInterval(countdownTimer);
  countdownBox.classList.add("hidden");
  launchLocked = false;
  if (!cameraEnabled) {
    gameNameEl.textContent = "Click any card below to launch";
  } else {
    resetGestureState();
  }
}

// ── Card click (cursor) — works with or without camera ────────
function manualLaunch(gameId) {
  if (launchLocked) return;

  // remove any existing done button
  const existing = document.getElementById("done-btn");
  if (existing) existing.remove();

  fingerDisplay.textContent = gameId;
  gameNameEl.textContent    = GAME_NAMES[gameId];
  highlightCard(parseInt(gameId));
  startCountdown(gameId);
}