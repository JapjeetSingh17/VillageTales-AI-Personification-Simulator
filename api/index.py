"""
Village Tales — AI Personification Simulator
FastAPI Backend serving the multi-agent dialogue pipeline and static frontend.
"""

import os
import io
import json
import math
import time
import tempfile

os.environ["GRADIO_TEMP_DIR"] = "/tmp"

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from app.graph import npc_graph, NPC_ROSTER, MultiNPCState
from app.ui_map import render_game_map, get_closest_npc, PROXIMITY_THRESHOLD, DEFAULT_PLAYER_POS
from app.rag import get_active_missions

# ==================== App Setup ====================
app = FastAPI(title="Village Tales — AI Personification Simulator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static directory for CSS, JS, map, and assets
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# ==================== Static Files ====================
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"), media_type="text/html")


@app.get("/static/{filepath:path}")
async def serve_static(filepath: str):
    full_path = os.path.join(STATIC_DIR, filepath)
    if os.path.exists(full_path) and not os.path.isdir(full_path):
        # Determine media type
        ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
        media_types = {
            "css": "text/css",
            "js": "application/javascript",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "svg": "image/svg+xml",
            "ico": "image/x-icon",
            "json": "application/json",
        }
        media_type = media_types.get(ext, "application/octet-stream")
        return FileResponse(full_path, media_type=media_type)
    return JSONResponse(status_code=404, content={"error": "Not found"})


# ==================== API: NPC Roster ====================
@app.get("/api/npcs")
async def api_npcs():
    """Return the full NPC roster with avatar URLs for the frontend."""
    roster = {}
    for npc_id, npc in NPC_ROSTER.items():
        roster[npc_id] = {
            "id": npc_id,
            "name": npc["name"],
            "title": npc["title"],
            "location": npc["location"],
            "color": npc["color"],
            "avatar_url": f"/static/avatars/{npc['avatar']}",
            "avatar_talk_url": f"/static/avatars/{npc['avatar_talk']}",
        }
    return roster


# ==================== API: Missions ====================
@app.get("/api/missions")
async def api_missions():
    """Return currently triggered story beats / missions."""
    try:
        missions = get_active_missions()
        return {"missions": missions}
    except Exception as e:
        return {"missions": [], "error": str(e)}


# ==================== API: Map Rendering ====================
@app.get("/api/map")
async def api_map(px: int = 1065, py: int = 925):
    """Render the game map with the player and NPC avatar tokens and return as fast JPEG."""
    img = render_game_map((px, py))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=88)
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/jpeg")


# ==================== API: Movement ====================
@app.post("/api/move")
async def api_move(data: dict):
    """Move the player in a direction or directly to clicked coordinates."""
    direction = data.get("direction")
    target_pos = data.get("target_pos")
    px, py = data.get("player_pos", [1065, 925])
    step = 90

    if target_pos and isinstance(target_pos, (list, tuple)) and len(target_pos) == 2:
        px = max(60, min(2340, int(target_pos[0])))
        py = max(60, min(1690, int(target_pos[1])))
    elif direction == "up":
        py = max(60, py - step)
    elif direction == "down":
        py = min(1690, py + step)
    elif direction == "left":
        px = max(60, px - step)
    elif direction == "right":
        px = min(2340, px + step)
    elif direction == "reset":
        px, py = 1065, 925

    npc_id, npc_info, dist = get_closest_npc((px, py))

    active_npc = None
    if npc_id:
        active_npc = {
            "id": npc_id,
            "name": npc_info["name"],
            "title": npc_info["title"],
            "location": npc_info["location"],
            "avatar_url": f"/static/avatars/{npc_info['avatar']}",
            "avatar_talk_url": f"/static/avatars/{npc_info['avatar_talk']}",
        }

    return {
        "player_pos": [px, py],
        "active_npc": active_npc,
    }


# ==================== API: Teleport ====================
@app.post("/api/teleport")
async def api_teleport(data: dict):
    """Teleport the player right to an NPC location."""
    location = data.get("location", "Sarini's Potion Shoppe")
    target_pos = [1065, 925]

    for npc in NPC_ROSTER.values():
        if npc["location"].lower() == location.lower() or npc["name"].lower() in location.lower():
            # Position player within proximity threshold of the NPC
            nx, ny = npc["pos"]
            target_pos = [nx, ny + 40]
            break

    npc_id, npc_info, dist = get_closest_npc(tuple(target_pos))

    active_npc = None
    if npc_id:
        active_npc = {
            "id": npc_id,
            "name": npc_info["name"],
            "title": npc_info["title"],
            "location": npc_info["location"],
            "avatar_url": f"/static/avatars/{npc_info['avatar']}",
            "avatar_talk_url": f"/static/avatars/{npc_info['avatar_talk']}",
        }

    return {
        "player_pos": target_pos,
        "active_npc": active_npc,
    }


# ==================== API: Talk (Voice + Text) ====================
@app.post("/api/talk")
async def api_talk(
    npc_id: str = Form(...),
    messages: str = Form("[]"),
    player_pos: str = Form("[1065, 925]"),
    user_text: str = Form(""),
    audio: UploadFile = File(None),
):
    """
    Process user input (voice or text) through the LangGraph pipeline.
    Returns NPC response text and audio URL.
    """
    from langchain_core.messages import HumanMessage, AIMessage

    # Parse conversation history from client
    msg_list = json.loads(messages)
    langchain_msgs = []
    for m in msg_list:
        if m["role"] == "user":
            langchain_msgs.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            langchain_msgs.append(AIMessage(content=m["content"]))

    pos = json.loads(player_pos)

    # Save uploaded audio to temp file if provided
    audio_path = None
    if audio and audio.filename:
        tmp_dir = tempfile.gettempdir()
        audio_ext = audio.filename.rsplit(".", 1)[-1] if "." in audio.filename else "webm"
        audio_path = os.path.join(tmp_dir, f"user_audio_{int(time.time() * 1000)}.{audio_ext}")
        content = await audio.read()
        with open(audio_path, "wb") as f:
            f.write(content)

    # Invoke LangGraph pipeline
    graph_input: MultiNPCState = {
        "npc_id": npc_id,
        "messages": langchain_msgs,
        "user_audio_path": audio_path,
        "user_text": user_text or "",
        "npc_text": "",
        "npc_audio_path": None,
        "npc_audio_base64": None,
        "player_pos": tuple(pos),
        "vault_threat": "ACTIVE",
        "rag_context": "",
    }

    final_state = npc_graph.invoke(graph_input)

    # Build audio URL - prefer base64 data URI so Vercel serverless never gets 404
    audio_url = final_state.get("npc_audio_base64")
    if not audio_url:
        npc_audio = final_state.get("npc_audio_path")
        if npc_audio and os.path.exists(npc_audio):
            audio_filename = os.path.basename(npc_audio)
            audio_url = f"/audio/{audio_filename}"

    # Extract what the user said (from STT or direct text)
    user_said = final_state.get("user_text", user_text)

    return {
        "npc_text": final_state.get("npc_text", ""),
        "user_text": user_said,
        "audio_url": audio_url,
    }


# ==================== API: Serve Audio Files ====================
@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated TTS audio files from /tmp."""
    filepath = os.path.join(tempfile.gettempdir(), filename)
    if os.path.exists(filepath) and filename.startswith("npc_speech_"):
        # Determine media type based on extension
        ext = filename.rsplit(".", 1)[-1].lower()
        media_type = "audio/wav" if ext == "wav" else "audio/mpeg"
        return FileResponse(
            filepath,
            media_type=media_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache",
            },
        )
    return JSONResponse({"error": "Audio file not found"}, status_code=404)
