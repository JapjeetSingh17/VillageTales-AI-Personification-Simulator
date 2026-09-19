/* ============================================================
   Village Tales — Client-Side Application Logic
   Multi-Agent AI Personification Simulator
   The Last Light of Duskendale RPG Interface
   Handles state, API calls, voice recording, avatars, and missions
   ============================================================ */

(function () {
  "use strict";

  // ==================== NPC METADATA & ROSTER ====================
  const NPC_INFO = {
    sarini: {
      id: "sarini",
      name: "Sarini",
      title: "Potion Shop Owner — Sarini's Potion Shoppe",
      location: "Sarini's Potion Shoppe",
      quote: "“Wards don't just fail, dear. Something's eating them. That's a taste I know, and I don't like it in my mouth.”",
      avatar_url: "/static/images/sarini_ref.png",
      avatar_talk_url: "/static/avatars/sarini_talk.png",
    },
    merowin: {
      id: "merowin",
      name: "Merowin",
      title: "Peddler — Eastern Road",
      location: "Eastern Road",
      quote: "“Strange fellow paid triple for a discreet delivery to the Manor. Didn't ask what was in the crate. Should I have asked?”",
      avatar_url: "/static/images/merowin_ref.png",
      avatar_talk_url: "/static/avatars/merowin_talk.png",
    },
    voss: {
      id: "voss",
      name: "Voss Kestrian",
      title: "“Lord” of Midnight Manor — Midnight Manor",
      location: "Midnight Manor",
      quote: "“Sir Besrand sealed a door. I intend to open it politely and ask what's on the other side. Is that so villainous?”",
      avatar_url: "/static/images/voss_ref.png",
      avatar_talk_url: "/static/avatars/voss.png",
    },
    adalric: {
      id: "adalric",
      name: "Brother Adalric",
      title: "Priest — Temple of Kord",
      location: "Temple of Kord",
      quote: "“The bells ring differently now. Heavier. Forty years I've kept silent, but silence won't save us from what's waking.”",
      avatar_url: "/static/images/adalric_ref.png",
      avatar_talk_url: "/static/avatars/adalric_talk.png",
    },
    fenn: {
      id: "fenn",
      name: "Fenn Ironhand",
      title: "Master Blacksmith — Fang Rock Forge",
      location: "Fang Rock Forge",
      quote: "“Iron doesn't crack on its own. It takes heat or hammer. Something under our feet is shaking the bones of the rock.”",
      avatar_url: "/static/images/fenn_ref.png",
      avatar_talk_url: "/static/avatars/fenn_talk.png",
    },
  };

  // ==================== STATE ====================
  const state = {
    playerPos: [550, 460],
    activeNpc: NPC_INFO.sarini,
    npcRoster: {},
    conversations: {
      sarini: [
        { role: "assistant", content: "You want a truth potion or you want to actually be told the truth? Different prices." },
        { role: "user", content: "What's going on with the wards?" },
        { role: "assistant", content: "They're not just failing. Something's eating them, and it's not natural. I can taste it in the herbs." }
      ]
    },
    isRecording: false,
    isProcessing: false,
    mediaRecorder: null,
    audioChunks: [],
    recordingStartTime: null,
    timerInterval: null,
    missionPollInterval: null,
    mapZoom: 1.0,
  };

  // ==================== DOM REFS ====================
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  let els = {};

  function cacheDom() {
    els = {
      mapImg: $("#map-image"),
      btnZoomIn: $("#btn-zoom-in"),
      btnZoomOut: $("#btn-zoom-out"),
      btnCenterPlayer: $("#btn-center-player"),
      npcBanner: $("#npc-banner"),
      npcName: $("#npc-name"),
      npcTitle: $("#npc-title"),
      npcStatus: $("#npc-status"),
      npcAvatar: $("#npc-avatar"),
      statusDot: $("#status-dot"),
      agentSelector: $("#agent-selector"),
      chatContainer: $("#chat-container"),
      chatEmpty: $("#chat-empty"),
      btnSpeak: $("#btn-speak"),
      btnClear: $("#btn-clear"),
      btnRecord: $("#btn-record"),
      btnStopRecord: $("#btn-stop-record"),
      recordSection: $("#record-section"),
      recStatusTag: $("#rec-status-tag"),
      recordTimer: $("#record-timer"),
      textInput: $("#text-input"),
      btnSend: $("#btn-send"),
      audioPlayer: $("#npc-audio-player"),
      loadingOverlay: $("#loading-overlay"),
      loadingText: $("#loading-text"),
      missionTracker: $("#mission-tracker"),
    };
  }

  // ==================== INITIALIZATION ====================
  document.addEventListener("DOMContentLoaded", () => {
    cacheDom();
    loadNpcRoster();
    bindMovement();
    bindTeleport();
    bindMapControls();
    bindMapClick();
    bindSpeechControls();
    bindTextInput();
    bindAgentSelection();

    // Set initial display to Sarini
    updateNpcBanner();
    loadChatHistory();

    // Load initial map
    updateMap();

    // Poll mission progress every 30s
    state.missionPollInterval = setInterval(pollMissions, 30000);
  });

  // ==================== NPC ROSTER ====================
  async function loadNpcRoster() {
    try {
      const res = await fetch("/api/npcs");
      state.npcRoster = await res.json();
    } catch (err) {
      console.error("[Roster Error]", err);
    }
  }

  // ==================== AGENT SELECTION ====================
  function setActiveNpcById(npcId) {
    const info = NPC_INFO[npcId];
    if (info) {
      state.activeNpc = info;
    } else if (state.npcRoster && state.npcRoster[npcId]) {
      state.activeNpc = state.npcRoster[npcId];
    }
    updateNpcBanner();
    loadChatHistory();
    syncRosterUi(npcId);
  }

  function syncRosterUi(npcId) {
    if (els.agentSelector) {
      els.agentSelector.value = npcId;
    }
    $$(".npc-card-item").forEach((card) => {
      if (card.dataset.npc === npcId) {
        card.classList.add("active");
      } else {
        card.classList.remove("active");
      }
    });
  }

  function bindAgentSelection() {
    if (els.agentSelector) {
      els.agentSelector.addEventListener("change", (e) => {
        setActiveNpcById(e.target.value);
      });
    }

    // Key NPCs list in right sidebar
    $$(".npc-card-item").forEach((card) => {
      card.addEventListener("click", () => {
        const npcId = card.dataset.npc;
        if (npcId) {
          setActiveNpcById(npcId);
          // Also teleport player closer to that NPC
          const info = NPC_INFO[npcId];
          if (info && info.location) {
            teleportTo(info.location);
          }
        }
      });
    });
  }

  // ==================== MAP & MOVEMENT ====================
  async function updateMap() {
    const [px, py] = state.playerPos;
    const url = `/api/map?px=${px}&py=${py}&t=${Date.now()}`;
    els.mapImg.src = url;
  }

  function bindMapControls() {
    if (els.btnZoomIn) {
      els.btnZoomIn.addEventListener("click", () => {
        state.mapZoom = Math.min(state.mapZoom + 0.25, 2.5);
        els.mapImg.style.transform = `scale(${state.mapZoom})`;
      });
    }

    if (els.btnZoomOut) {
      els.btnZoomOut.addEventListener("click", () => {
        state.mapZoom = Math.max(state.mapZoom - 0.25, 1.0);
        els.mapImg.style.transform = `scale(${state.mapZoom})`;
      });
    }

    if (els.btnCenterPlayer) {
      els.btnCenterPlayer.addEventListener("click", () => {
        state.mapZoom = 1.0;
        els.mapImg.style.transform = "scale(1.0)";
        updateMap();
      });
    }
  }

  async function movePlayer(direction) {
    if (state.isProcessing) return;

    try {
      const res = await fetch("/api/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          direction: direction,
          player_pos: state.playerPos,
        }),
      });

      const data = await res.json();
      state.playerPos = data.player_pos;

      if (data.active_npc) {
        state.activeNpc = data.active_npc;
        syncRosterUi(data.active_npc.id);
      }

      updateMap();
      updateNpcBanner();
      loadChatHistory();
    } catch (err) {
      console.error("[Move Error]", err);
    }
  }

  async function teleportTo(location, targetNpcId = null) {
    if (state.isProcessing) return;

    try {
      const res = await fetch("/api/teleport", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ location: location }),
      });

      const data = await res.json();
      state.playerPos = data.player_pos;

      if (data.active_npc) {
        state.activeNpc = data.active_npc;
        syncRosterUi(data.active_npc.id);
      } else if (targetNpcId && NPC_INFO[targetNpcId]) {
        state.activeNpc = NPC_INFO[targetNpcId];
        syncRosterUi(targetNpcId);
      }

      updateMap();
      updateNpcBanner();
      loadChatHistory();
    } catch (err) {
      console.error("[Teleport Error]", err);
    }
  }

  async function moveToCoords(targetX, targetY) {
    if (state.isProcessing) return;

    try {
      const res = await fetch("/api/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_pos: [targetX, targetY],
          player_pos: state.playerPos,
        }),
      });

      const data = await res.json();
      state.playerPos = data.player_pos;

      if (data.active_npc) {
        state.activeNpc = data.active_npc;
        syncRosterUi(data.active_npc.id);
      }

      updateMap();
      updateNpcBanner();
      loadChatHistory();
    } catch (err) {
      console.error("[Move Error]", err);
    }
  }

  function bindMovement() {
    $$(".btn-move").forEach((btn) => {
      btn.addEventListener("click", () => movePlayer(btn.dataset.dir));
    });
  }

  function bindTeleport() {
    // Quick location access buttons
    $$(".btn-quick-loc").forEach((btn) => {
      btn.addEventListener("click", () => teleportTo(btn.dataset.location));
    });

    // Agent teleport buttons
    $$(".btn-teleport-npc").forEach((btn) => {
      btn.addEventListener("click", () => {
        const loc = btn.dataset.location;
        const npc = btn.dataset.npc;
        teleportTo(loc, npc);
      });
    });
  }

  function bindMapClick() {
    if (!els.mapImg) return;
    els.mapImg.addEventListener("click", (e) => {
      const rect = els.mapImg.getBoundingClientRect();
      const clickX = Math.round(((e.clientX - rect.left) / rect.width) * 1290);
      const clickY = Math.round(((e.clientY - rect.top) / rect.height) * 846);
      moveToCoords(clickX, clickY);
    });
  }

  // ==================== NPC BANNER ====================
  function updateNpcBanner() {
    const npc = state.activeNpc || NPC_INFO.sarini;

    if (npc) {
      els.npcName.textContent = npc.name;
      els.npcTitle.textContent = npc.title || `${npc.name} — ${npc.location}`;
      els.npcStatus.textContent = npc.quote || "“I know these lands well, traveler.”";

      // Update avatar image
      const avatarSrc = npc.avatar_url || (NPC_INFO[npc.id] ? NPC_INFO[npc.id].avatar_url : "/static/images/sarini_ref.png");
      els.npcAvatar.src = avatarSrc;
      els.npcAvatar.alt = `${npc.name} portrait`;
    }
  }

  // ==================== CHAT ====================
  function loadChatHistory() {
    const npc = state.activeNpc || NPC_INFO.sarini;
    const npcId = npc.id;
    const msgs = state.conversations[npcId] || [];

    if (msgs.length === 0) {
      els.chatContainer.innerHTML = `<div class="chat-empty" id="chat-empty">Start talking to ${npc.name}</div>`;
      return;
    }

    renderMessages(msgs);
  }

  function renderMessages(msgs) {
    els.chatContainer.innerHTML = "";
    const activeNpc = state.activeNpc || NPC_INFO.sarini;

    msgs.forEach((msg, idx) => {
      const timeStr = msg.time || (idx === 0 ? "10:24 AM" : "10:25 AM");
      const wrapper = document.createElement("div");
      wrapper.className = `chat-msg-row ${msg.role === "user" ? "user-row" : "npc-row"}`;

      if (msg.role !== "user") {
        // NPC Message
        const avatarImg = document.createElement("img");
        avatarImg.className = "chat-msg-avatar";
        avatarImg.src = activeNpc.avatar_url || (NPC_INFO[activeNpc.id] ? NPC_INFO[activeNpc.id].avatar_url : "/static/images/sarini_ref.png");
        avatarImg.alt = "";

        const bubbleCol = document.createElement("div");
        bubbleCol.className = "bubble-column";

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble npc-bubble";
        bubble.textContent = msg.content;

        const meta = document.createElement("div");
        meta.className = "chat-msg-meta";
        meta.textContent = `${activeNpc.name} • ${timeStr}`;

        bubbleCol.appendChild(bubble);
        bubbleCol.appendChild(meta);

        wrapper.appendChild(avatarImg);
        wrapper.appendChild(bubbleCol);
      } else {
        // User Message
        const bubbleCol = document.createElement("div");
        bubbleCol.className = "bubble-column user-bubble-column";

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble user-bubble";
        bubble.textContent = msg.content;

        const meta = document.createElement("div");
        meta.className = "chat-msg-meta user-meta";
        meta.textContent = timeStr;

        bubbleCol.appendChild(bubble);
        bubbleCol.appendChild(meta);

        const userIcon = document.createElement("div");
        userIcon.className = "chat-user-icon";
        userIcon.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="#93c5fd"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>`;

        wrapper.appendChild(bubbleCol);
        wrapper.appendChild(userIcon);
      }

      els.chatContainer.appendChild(wrapper);
    });

    els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
  }

  function appendMessage(role, content, audioUrl = null) {
    const npc = state.activeNpc || NPC_INFO.sarini;
    const npcId = npc.id;
    if (!state.conversations[npcId]) state.conversations[npcId] = [];

    const now = new Date();
    const hours = now.getHours();
    const mins = String(now.getMinutes()).padStart(2, "0");
    const ampm = hours >= 12 ? "PM" : "AM";
    const timeFormatted = `${((hours + 11) % 12 + 1)}:${mins} ${ampm}`;

    state.conversations[npcId].push({ role, content, audio_url: audioUrl, time: timeFormatted });

    const empty = els.chatContainer.querySelector(".chat-empty");
    if (empty) empty.remove();

    renderMessages(state.conversations[npcId]);
  }

  // ==================== NPC VOICE SYNTHESIS & PLAYBACK ====================
  function speakWithWebSpeech(npc, text) {
    if (!("speechSynthesis" in window) || !text) return;

    try {
      window.speechSynthesis.cancel();
      const clean = text.replace(/\[.*?\]/g, "").replace(/\(.*?\)/g, "").replace(/\*/g, "").trim();
      if (!clean) return;

      const utterance = new SpeechSynthesisUtterance(clean);
      const voices = window.speechSynthesis.getVoices() || [];
      const npcId = npc ? npc.id : "sarini";

      if (npcId === "sarini") {
        utterance.pitch = 1.15;
        utterance.rate = 0.95;
        const v = voices.find((v) => v.lang && v.lang.startsWith("en") && (v.name.includes("Female") || v.name.includes("Samantha") || v.name.includes("Victoria") || v.name.includes("Zira")));
        if (v) utterance.voice = v;
      } else if (npcId === "voss") {
        utterance.pitch = 0.75;
        utterance.rate = 0.9;
        const v = voices.find((v) => v.lang && v.lang.startsWith("en") && (v.name.includes("Male") || v.name.includes("Daniel") || v.name.includes("Alex") || v.name.includes("David")));
        if (v) utterance.voice = v;
      } else if (npcId === "merowin") {
        utterance.pitch = 0.95;
        utterance.rate = 1.05;
      } else if (npcId === "adalric") {
        utterance.pitch = 0.82;
        utterance.rate = 0.9;
      } else {
        utterance.pitch = 0.8;
        utterance.rate = 0.95;
      }

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("[Web Speech Exception]", e);
    }
  }

  function playNpcVoice(audioUrl, npc, fallbackText) {
    if (audioUrl) {
      if (!els.audioPlayer) return;
      els.audioPlayer.pause();
      els.audioPlayer.currentTime = 0;
      els.audioPlayer.src = audioUrl;

      els.audioPlayer.play().catch((err) => {
        console.warn("[Autoplay Notice] Falling back to Web Speech:", err);
        speakWithWebSpeech(npc, fallbackText);
      });
    } else {
      speakWithWebSpeech(npc, fallbackText);
    }
  }

  // ==================== SPEECH & RECORDING CONTROLS ====================
  function bindSpeechControls() {
    els.btnSpeak.addEventListener("click", handleSpeakToggle);
    els.btnClear.addEventListener("click", clearChat);
  }

  async function handleSpeakToggle() {
    const text = els.textInput.value.trim();
    if (text) {
      sendTextMessage();
      return;
    }

    if (state.isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }

  async function startRecording() {
    if (state.isRecording || state.isProcessing) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      let mimeType = "audio/webm";
      let fileExt = "webm";

      if (typeof MediaRecorder.isTypeSupported === "function") {
        if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
          mimeType = "audio/webm;codecs=opus";
          fileExt = "webm";
        } else if (MediaRecorder.isTypeSupported("audio/webm")) {
          mimeType = "audio/webm";
          fileExt = "webm";
        } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
          mimeType = "audio/mp4";
          fileExt = "mp4";
        }
      }

      state.recordingMimeType = mimeType;
      state.recordingExt = fileExt;
      state.mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      state.audioChunks = [];

      state.mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) state.audioChunks.push(e.data);
      };

      state.mediaRecorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(state.audioChunks, { type: state.recordingMimeType || "audio/webm" });
        sendAudioToApi(blob);
      };

      state.mediaRecorder.start();
      state.isRecording = true;
      state.recordingStartTime = Date.now();

      // Update UI to recording state
      els.recordSection.classList.add("recording");
      if (els.recStatusTag) els.recStatusTag.textContent = "Recording...";
      els.btnSpeak.querySelector("span").textContent = "Stop & Send";

      // Start timer
      state.timerInterval = setInterval(updateRecordTimer, 100);
    } catch (err) {
      console.error("[Mic Error]", err);
      alert("Microphone access denied. Please allow microphone access in your browser settings.");
    }
  }

  function stopRecording() {
    if (!state.isRecording || !state.mediaRecorder) return;

    state.mediaRecorder.stop();
    state.isRecording = false;

    // Reset UI
    els.recordSection.classList.remove("recording");
    if (els.recStatusTag) els.recStatusTag.textContent = "Ready";
    els.btnSpeak.querySelector("span").textContent = "Start Speaking";

    clearInterval(state.timerInterval);
    els.recordTimer.textContent = "00:00";
  }

  function updateRecordTimer() {
    if (!state.recordingStartTime) return;
    const elapsed = Math.floor((Date.now() - state.recordingStartTime) / 1000);
    const mins = String(Math.floor(elapsed / 60)).padStart(2, "0");
    const secs = String(elapsed % 60).padStart(2, "0");
    els.recordTimer.textContent = `${mins}:${secs}`;
  }

  async function sendAudioToApi(audioBlob) {
    const npc = state.activeNpc || NPC_INFO.sarini;
    showLoading("Transcribing voice via Groq Whisper & reasoning with Gemini...");

    const npcId = npc.id;
    const messages = state.conversations[npcId] || [];

    const formData = new FormData();
    const fileName = "recording." + (state.recordingExt || "webm");
    formData.append("audio", audioBlob, fileName);
    formData.append("npc_id", npcId);
    formData.append("messages", JSON.stringify(messages));
    formData.append("player_pos", JSON.stringify(state.playerPos));

    try {
      const res = await fetch("/api/talk", { method: "POST", body: formData });
      const data = await res.json();

      if (data.user_text) appendMessage("user", data.user_text);
      if (data.npc_text) appendMessage("assistant", data.npc_text, data.audio_url);

      playNpcVoice(data.audio_url, state.activeNpc, data.npc_text);
      pollMissions();
    } catch (err) {
      console.error("[Talk Error]", err);
      appendMessage("assistant", "(Connection error — please try again)");
    } finally {
      hideLoading();
    }
  }

  // ==================== TEXT INPUT ====================
  function bindTextInput() {
    els.btnSend.addEventListener("click", sendTextMessage);
    els.textInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendTextMessage();
      }
    });
  }

  async function sendTextMessage() {
    const text = els.textInput.value.trim();
    if (!text || state.isProcessing) return;

    const npc = state.activeNpc || NPC_INFO.sarini;
    els.textInput.value = "";
    showLoading(`Consulting ${npc.name}...`);

    const npcId = npc.id;
    const messages = state.conversations[npcId] || [];

    const formData = new FormData();
    formData.append("user_text", text);
    formData.append("npc_id", npcId);
    formData.append("messages", JSON.stringify(messages));
    formData.append("player_pos", JSON.stringify(state.playerPos));

    try {
      const res = await fetch("/api/talk", { method: "POST", body: formData });
      const data = await res.json();

      if (data.user_text) appendMessage("user", data.user_text);
      if (data.npc_text) appendMessage("assistant", data.npc_text, data.audio_url);

      playNpcVoice(data.audio_url, state.activeNpc, data.npc_text);
      pollMissions();
    } catch (err) {
      console.error("[Talk Error]", err);
      appendMessage("assistant", "(Connection error — please try again)");
    } finally {
      hideLoading();
    }
  }

  // ==================== CLEAR CHAT ====================
  function clearChat() {
    const npc = state.activeNpc || NPC_INFO.sarini;
    const npcId = npc.id;
    state.conversations[npcId] = [];
    els.chatContainer.innerHTML = `<div class="chat-empty">Start talking to ${npc.name}</div>`;
    if (els.audioPlayer) {
      els.audioPlayer.src = "";
      els.audioPlayer.pause();
    }
  }

  // ==================== MISSION POLLING ====================
  async function pollMissions() {
    try {
      const res = await fetch("/api/missions");
      const data = await res.json();
      const missions = data.missions || [];

      if (missions.length > 0 && els.missionTracker) {
        els.missionTracker.innerHTML = "";
        missions.forEach((m) => {
          const item = document.createElement("div");
          item.className = "mission-item";
          const cleanText = m.replace(/^MISSION BEAT \[.*?\]: /, "");
          item.textContent = cleanText;
          els.missionTracker.appendChild(item);
        });
      }
    } catch (err) {
      // Silently ignore mission poll errors
    }
  }

  // ==================== LOADING ====================
  function showLoading(text) {
    state.isProcessing = true;
    els.loadingText.textContent = text || "Consulting the oracles...";
    els.loadingOverlay.classList.add("active");
    els.btnSpeak.disabled = true;
    els.btnSend.disabled = true;
  }

  function hideLoading() {
    state.isProcessing = false;
    els.loadingOverlay.classList.remove("active");
    els.btnSpeak.disabled = false;
    els.btnSend.disabled = false;
  }
})();
