/* ============================================================
   Village Tales — Client-Side Application Logic
   Multi-Agent AI Personification Simulator
   Handles state, API calls, recording, avatars, and missions
   ============================================================ */

(function () {
  "use strict";

  // ==================== STATE ====================
  const state = {
    playerPos: [1065, 925],
    activeNpc: null,
    npcRoster: {},
    conversations: {},
    isRecording: false,
    isProcessing: false,
    mediaRecorder: null,
    audioChunks: [],
    recordingStartTime: null,
    timerInterval: null,
    missionPollInterval: null,
  };

  // ==================== DOM REFS ====================
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  let els = {};

  function cacheDom() {
    els = {
      mapImg: $("#map-image"),
      npcBanner: $("#npc-banner"),
      npcName: $("#npc-name"),
      npcTitle: $("#npc-title"),
      npcStatus: $("#npc-status"),
      npcAvatar: $("#npc-avatar"),
      statusDot: $("#status-dot"),
      chatContainer: $("#chat-container"),
      chatEmpty: $("#chat-empty"),
      btnSpeak: $("#btn-speak"),
      btnClear: $("#btn-clear"),
      btnRecord: $("#btn-record"),
      btnStopRecord: $("#btn-stop-record"),
      recordSection: $("#record-section"),
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
    bindMapClick();
    bindSpeechControls();
    bindTextInput();

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

  // ==================== MAP & MOVEMENT ====================
  async function updateMap() {
    const [px, py] = state.playerPos;
    const url = `/api/map?px=${px}&py=${py}&t=${Date.now()}`;
    els.mapImg.src = url;
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
      state.activeNpc = data.active_npc;

      updateMap();
      updateNpcBanner();
      loadChatHistory();
    } catch (err) {
      console.error("[Move Error]", err);
    }
  }

  async function teleportTo(location) {
    if (state.isProcessing) return;

    try {
      const res = await fetch("/api/teleport", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ location: location }),
      });

      const data = await res.json();
      state.playerPos = data.player_pos;
      state.activeNpc = data.active_npc;

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
      state.activeNpc = data.active_npc;

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
    $$(".btn-teleport").forEach((btn) => {
      btn.addEventListener("click", () => teleportTo(btn.dataset.location));
    });
  }

  function bindMapClick() {
    if (!els.mapImg) return;
    els.mapImg.addEventListener("click", (e) => {
      const rect = els.mapImg.getBoundingClientRect();
      const clickX = Math.round(((e.clientX - rect.left) / rect.width) * 2400);
      const clickY = Math.round(((e.clientY - rect.top) / rect.height) * 1750);
      moveToCoords(clickX, clickY);
    });
  }

  // ==================== NPC BANNER ====================
  function updateNpcBanner() {
    const npc = state.activeNpc;

    if (npc) {
      els.npcBanner.classList.add("active");
      els.npcBanner.classList.remove("exploring");
      els.statusDot.className = "status-dot online";
      els.npcName.textContent = npc.name;
      els.npcTitle.textContent = `${npc.title} — ${npc.location}`;
      els.npcStatus.textContent = "Agent in range — record your voice or type a message";

      // Update avatar
      if (npc.avatar_url) {
        els.npcAvatar.src = npc.avatar_url;
        els.npcAvatar.alt = `${npc.name} avatar`;
      }
    } else {
      els.npcBanner.classList.remove("active");
      els.npcBanner.classList.add("exploring");
      els.statusDot.className = "status-dot offline";
      els.npcName.textContent = "Exploring Duskendale";
      els.npcTitle.textContent = "Move closer to an agent on the map";
      els.npcStatus.textContent = "No agent in range";
      els.npcAvatar.src = "/static/avatars/sarini.png";
    }
  }

  // ==================== CHAT ====================
  function loadChatHistory() {
    if (!state.activeNpc) {
      els.chatContainer.innerHTML = '<div class="chat-empty" id="chat-empty">Walk near an agent to start a conversation</div>';
      return;
    }

    const npcId = state.activeNpc.id;
    const msgs = state.conversations[npcId] || [];

    if (msgs.length === 0) {
      els.chatContainer.innerHTML = `<div class="chat-empty" id="chat-empty">Start talking to ${state.activeNpc.name}</div>`;
      return;
    }

    renderMessages(msgs);
  }

  function renderMessages(msgs) {
    els.chatContainer.innerHTML = "";

    msgs.forEach((msg) => {
      const div = document.createElement("div");
      div.className = `chat-msg ${msg.role === "user" ? "user" : "npc"}`;

      // Add avatar thumbnail for NPC messages
      if (msg.role !== "user" && state.activeNpc && state.activeNpc.avatar_url) {
        const avatarImg = document.createElement("img");
        avatarImg.className = "chat-msg-avatar";
        avatarImg.src = state.activeNpc.avatar_url;
        avatarImg.alt = "";
        div.appendChild(avatarImg);
      }

      const contentDiv = document.createElement("div");
      contentDiv.className = "chat-msg-content";

      const label = document.createElement("div");
      label.className = "msg-label";
      label.textContent = msg.role === "user" ? "You" : (state.activeNpc ? state.activeNpc.name : "Agent");

      const text = document.createElement("div");
      text.textContent = msg.content;

      contentDiv.appendChild(label);
      contentDiv.appendChild(text);
      div.appendChild(contentDiv);
      els.chatContainer.appendChild(div);
    });

    // Scroll to bottom
    els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
  }

  function appendMessage(role, content) {
    if (!state.activeNpc) return;

    const npcId = state.activeNpc.id;
    if (!state.conversations[npcId]) state.conversations[npcId] = [];
    state.conversations[npcId].push({ role, content });

    // Remove empty state message
    const empty = els.chatContainer.querySelector(".chat-empty");
    if (empty) empty.remove();

    const div = document.createElement("div");
    div.className = `chat-msg ${role === "user" ? "user" : "npc"}`;

    // Add avatar thumbnail for NPC messages
    if (role !== "user" && state.activeNpc && state.activeNpc.avatar_url) {
      const avatarImg = document.createElement("img");
      avatarImg.className = "chat-msg-avatar";
      avatarImg.src = state.activeNpc.avatar_talk_url || state.activeNpc.avatar_url;
      avatarImg.alt = "";
      div.appendChild(avatarImg);
    }

    const contentDiv = document.createElement("div");
    contentDiv.className = "chat-msg-content";

    const label = document.createElement("div");
    label.className = "msg-label";
    label.textContent = role === "user" ? "You" : (state.activeNpc ? state.activeNpc.name : "Agent");

    const text = document.createElement("div");
    text.textContent = content;

    contentDiv.appendChild(label);
    contentDiv.appendChild(text);
    div.appendChild(contentDiv);
    els.chatContainer.appendChild(div);
    els.chatContainer.scrollTop = els.chatContainer.scrollHeight;

    // Show speaking avatar expression when NPC responds
    if (role !== "user" && state.activeNpc) {
      els.npcBanner.classList.add("speaking");
      if (state.activeNpc.avatar_talk_url) {
        els.npcAvatar.src = state.activeNpc.avatar_talk_url;
      }
      // Revert to calm after 3 seconds
      setTimeout(() => {
        els.npcBanner.classList.remove("speaking");
        if (state.activeNpc && state.activeNpc.avatar_url) {
          els.npcAvatar.src = state.activeNpc.avatar_url;
        }
      }, 3000);
    }
  }

  // ==================== SPEECH CONTROLS ====================
  function bindSpeechControls() {
    els.btnRecord.addEventListener("click", startRecording);
    els.btnStopRecord.addEventListener("click", stopRecording);
    els.btnSpeak.addEventListener("click", handleSpeak);
    els.btnClear.addEventListener("click", clearChat);
  }

  async function startRecording() {
    if (state.isRecording || state.isProcessing) return;
    if (!state.activeNpc) {
      alert("Move closer to an agent on the map first!");
      return;
    }

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

      // UI updates
      els.recordSection.classList.add("recording");
      els.btnRecord.classList.add("active");
      els.btnRecord.disabled = true;
      els.btnStopRecord.disabled = false;

      // Start timer
      state.timerInterval = setInterval(updateRecordTimer, 100);
    } catch (err) {
      console.error("[Mic Error]", err);
      alert("Microphone access denied. Please allow microphone access to record.");
    }
  }

  function stopRecording() {
    if (!state.isRecording || !state.mediaRecorder) return;

    state.mediaRecorder.stop();
    state.isRecording = false;

    // UI updates
    els.recordSection.classList.remove("recording");
    els.btnRecord.classList.remove("active");
    els.btnRecord.disabled = false;
    els.btnStopRecord.disabled = true;

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
    if (!state.activeNpc) return;
    showLoading("Transcribing voice via Gemini STT...");

    const npcId = state.activeNpc.id;
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
      if (data.npc_text) appendMessage("assistant", data.npc_text);

      // Play NPC audio
      if (data.audio_url) {
        els.audioPlayer.src = data.audio_url;
        els.audioPlayer.play().catch(() => {});
      }

      // Poll missions after interaction
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

    if (!state.activeNpc) {
      alert("Move closer to an agent on the map first!");
      return;
    }

    els.textInput.value = "";
    showLoading("Generating agent response via Gemini...");

    const npcId = state.activeNpc.id;
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
      if (data.npc_text) appendMessage("assistant", data.npc_text);

      if (data.audio_url) {
        els.audioPlayer.src = data.audio_url;
        els.audioPlayer.play().catch(() => {});
      }

      // Poll missions after interaction
      pollMissions();
    } catch (err) {
      console.error("[Talk Error]", err);
      appendMessage("assistant", "(Connection error — please try again)");
    } finally {
      hideLoading();
    }
  }

  // ==================== HANDLE SPEAK BUTTON ====================
  async function handleSpeak() {
    // If there's text in the input, send it; otherwise start recording
    const text = els.textInput.value.trim();
    if (text) {
      sendTextMessage();
    } else {
      if (state.isRecording) {
        stopRecording();
      } else {
        startRecording();
      }
    }
  }

  // ==================== CLEAR CHAT ====================
  function clearChat() {
    if (!state.activeNpc) return;
    const npcId = state.activeNpc.id;
    state.conversations[npcId] = [];
    els.chatContainer.innerHTML = `<div class="chat-empty">Start talking to ${state.activeNpc.name}</div>`;
    els.audioPlayer.src = "";
    els.audioPlayer.pause();
  }

  // ==================== MISSION POLLING ====================
  async function pollMissions() {
    try {
      const res = await fetch("/api/missions");
      const data = await res.json();
      const missions = data.missions || [];

      if (missions.length > 0) {
        els.missionTracker.innerHTML = "";
        missions.forEach((m) => {
          const item = document.createElement("div");
          item.className = "mission-item";
          // Clean up the mission text for display
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
    els.loadingText.textContent = text || "Processing...";
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
