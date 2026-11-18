/**
 * Console Mobile Controller Logic.
 * Handles real-time WebSocket syncing, library navigation, persistent Home button,
 * and dynamic game controller interfaces.
 */

let socket = null;
let playerRole = localStorage.getItem("controller_role") || "player1";
let currentGames = [];
let currentIndex = 0;
let activeGame = null;

// DOM Elements
const connIndicator = document.getElementById("conn-indicator");
const connText = document.getElementById("conn-text");
const playerBadge = document.getElementById("player-badge");
const btnHome = document.getElementById("btn-home");

const screenRoleSelect = document.getElementById("screen-role-select");
const screenLibrary = document.getElementById("screen-library");
const screenQuickdraw = document.getElementById("screen-quickdraw");
const screenReflex = document.getElementById("screen-reflex");
const screenGeneric = document.getElementById("screen-generic");

// Library Elements
const libGameThumb = document.getElementById("lib-game-thumb");
const libGameBadge = document.getElementById("lib-game-badge");
const libGameTitle = document.getElementById("lib-game-title");
const libGameDesc = document.getElementById("lib-game-desc");
const libIndexIndicator = document.getElementById("lib-index-indicator");
const btnPrev = document.getElementById("btn-prev");
const btnNext = document.getElementById("btn-next");
const btnLaunch = document.getElementById("btn-launch");

// Quickdraw Elements
const duelStateBox = document.getElementById("duel-state-box");
const btnQuickdrawTrigger = document.getElementById("btn-quickdraw-trigger");

// Cyber Reflex Elements
const reflexSignalBox = document.getElementById("reflex-signal-box");
const btnReflexTrigger = document.getElementById("btn-reflex-trigger");

function vibrate(pattern = [40]) {
  if (navigator.vibrate) {
    navigator.vibrate(pattern);
  }
}

function updatePlayerBadge() {
  playerBadge.textContent = playerRole === "player1" ? "P1" : "P2";
  playerBadge.style.background = playerRole === "player1" ? "#0077ff" : "#ff4400";
}

function showScreen(screenEl) {
  [screenRoleSelect, screenLibrary, screenQuickdraw, screenReflex, screenGeneric].forEach(s => {
    if (s) s.classList.remove("active");
  });
  if (screenEl) {
    screenEl.classList.add("active");
  }
}

function connectWebSocket() {
  const host = window.location.hostname || "127.0.0.1";
  const wsUrl = `ws://${host}:8000`;
  
  connText.textContent = "Connecting...";
  connIndicator.className = "dot disconnected";

  try {
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      connIndicator.className = "dot connected";
      connText.textContent = "Connected";
      // Send role announcement
      sendJson({
        type: "set_role",
        role: playerRole,
        player: playerRole
      });
    };

    socket.onclose = () => {
      connIndicator.className = "dot disconnected";
      connText.textContent = "Disconnected";
      setTimeout(connectWebSocket, 1500);
    };

    socket.onerror = (err) => {
      console.warn("WebSocket error:", err);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
      } catch (e) {
        console.error("Failed to parse message:", event.data);
      }
    };
  } catch (err) {
    console.error("Connection failed:", err);
    setTimeout(connectWebSocket, 2000);
  }
}

function sendJson(obj) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(obj));
  }
}

function handleServerMessage(data) {
  const type = data.type;

  if (type === "sync_state") {
    currentGames = data.games || [];
    currentIndex = data.selected_index || 0;
    
    if (data.screen === "LIBRARY") {
      showScreen(screenLibrary);
      updateLibraryCard(data.game, currentIndex, currentGames.length);
    } else if (data.screen === "IN_GAME") {
      activateGameScreen(data.game);
    }
  }
  else if (type === "game_started") {
    vibrate([60, 40, 60]);
    activateGameScreen({
      id: data.game_id,
      title: data.title,
      controller_type: data.controller_type,
      controller_spec: data.controller_spec
    });
  }
  else if (type === "game_stopped") {
    vibrate([40, 30, 40]);
    showScreen(screenLibrary);
  }
  else if (type === "game_state") {
    // Quickdraw or game-specific state
    if (duelStateBox) {
      if (data.game_state === "SHOOT") {
        duelStateBox.textContent = `⚡ SHOOT! "${data.word || 'DRAW'}" ⚡`;
        duelStateBox.style.color = "#00ff88";
        duelStateBox.style.borderColor = "#00ff88";
        vibrate([80, 50, 100]);
      } else if (data.game_state === "FALSE_START") {
        duelStateBox.textContent = `FALSE START by ${data.loser || 'player'}!`;
        duelStateBox.style.color = "#ff3344";
        duelStateBox.style.borderColor = "#ff3344";
        vibrate([200]);
      } else {
        duelStateBox.textContent = data.info || data.game_state;
        duelStateBox.style.color = "#ffaa00";
        duelStateBox.style.borderColor = "#ffaa00";
      }
    }
  }
  else if (type === "signal" && data.color === "green") {
    // Cyber reflex green signal
    if (reflexSignalBox) {
      reflexSignalBox.textContent = "⚡ SLAM NOW! ⚡";
      reflexSignalBox.style.background = "#00ff88";
      reflexSignalBox.style.color = "#000";
      vibrate([100]);
    }
  }
}

function updateLibraryCard(game, index, total) {
  if (!game) return;
  libGameTitle.textContent = game.title.toUpperCase();
  libGameDesc.textContent = game.description;
  libGameBadge.textContent = `${game.min_players}-${game.max_players} PLAYERS`;
  libGameThumb.src = game.thumbnail;

  // Dots
  libIndexIndicator.innerHTML = "";
  for (let i = 0; i < total; i++) {
    const dot = document.createElement("span");
    dot.className = "dot" + (i === index ? " active" : "");
    libIndexIndicator.appendChild(dot);
  }
}

function activateGameScreen(game) {
  if (!game) return;
  activeGame = game;

  if (game.id === "quickdraw" || game.controller_type === "quickdraw") {
    showScreen(screenQuickdraw);
    if (duelStateBox) {
      duelStateBox.textContent = "READY - LISTEN TO OUTLAW";
      duelStateBox.style.color = "#ffaa00";
      duelStateBox.style.borderColor = "#ffaa00";
    }
  } else if (game.id === "reflex_duel" || game.controller_type === "reflex") {
    showScreen(screenReflex);
    if (reflexSignalBox) {
      reflexSignalBox.textContent = "WAIT FOR GREEN...";
      reflexSignalBox.style.background = "#191b24";
      reflexSignalBox.style.color = "#00d2ff";
    }
  } else {
    // Generic fallback controller
    showScreen(screenGeneric);
    const gTitle = document.getElementById("generic-title");
    const gDesc = document.getElementById("generic-instructions");
    if (gTitle) gTitle.textContent = game.title.toUpperCase();
    if (gDesc) gDesc.textContent = (game.controller_spec && game.controller_spec.instructions) || "Use controller";
  }
}

// Persistent Home Button Trigger (Every screen!)
btnHome.addEventListener("click", () => {
  vibrate([50]);
  sendJson({
    type: "home",
    action: "home"
  });
});

// Library Navigation
btnPrev.addEventListener("click", () => {
  vibrate([30]);
  sendJson({
    type: "navigate",
    direction: "prev"
  });
});

btnNext.addEventListener("click", () => {
  vibrate([30]);
  sendJson({
    type: "navigate",
    direction: "next"
  });
});

btnLaunch.addEventListener("click", () => {
  vibrate([80]);
  sendJson({
    type: "select_game",
    action: "select_game"
  });
});

// Touch / Swipe Navigation on Library Card
let touchStartX = 0;
screenLibrary.addEventListener("touchstart", (e) => {
  touchStartX = e.touches[0].clientX;
}, { passive: true });

screenLibrary.addEventListener("touchend", (e) => {
  const touchEndX = e.changedTouches[0].clientX;
  const diff = touchEndX - touchStartX;
  if (Math.abs(diff) > 50) {
    if (diff > 0) {
      btnPrev.click();
    } else {
      btnNext.click();
    }
  }
}, { passive: true });

// Quickdraw Trigger Action
function triggerShot() {
  vibrate([70, 30, 80]);
  const timestamp = Date.now();
  // Send both formats for seamless server compatibility
  sendJson({
    type: "input",
    action: "shoot",
    player: playerRole,
    time: timestamp
  });
}

btnQuickdrawTrigger.addEventListener("pointerdown", (e) => {
  e.preventDefault();
  triggerShot();
});

// Cyber Reflex Trigger Action
btnReflexTrigger.addEventListener("pointerdown", (e) => {
  e.preventDefault();
  vibrate([90]);
  sendJson({
    type: "input",
    action: "slam",
    player: playerRole,
    time: Date.now()
  });
});

// Role Selection Buttons
document.getElementById("btn-select-p1").addEventListener("click", () => {
  playerRole = "player1";
  localStorage.setItem("controller_role", "player1");
  updatePlayerBadge();
  sendJson({ type: "set_role", role: "player1", player: "player1" });
  showScreen(screenLibrary);
});

document.getElementById("btn-select-p2").addEventListener("click", () => {
  playerRole = "player2";
  localStorage.setItem("controller_role", "player2");
  updatePlayerBadge();
  sendJson({ type: "set_role", role: "player2", player: "player2" });
  showScreen(screenLibrary);
});

// Player Badge click toggles role
playerBadge.addEventListener("click", () => {
  playerRole = playerRole === "player1" ? "player2" : "player1";
  localStorage.setItem("controller_role", playerRole);
  updatePlayerBadge();
  vibrate([40]);
  sendJson({ type: "set_role", role: playerRole, player: playerRole });
});

// Initialization
updatePlayerBadge();
connectWebSocket();
