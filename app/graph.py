"""
Village Tales — Multi-Agent LangGraph Pipeline
Autonomous AI persona agents for the village of Duskendale,
powered by Gemini LLM, Gemini TTS, Gemini STT, and RAG memory.
"""

import io
import os
import re
import time
import wave
import struct
import base64
import tempfile
from typing import TypedDict, List, Optional, Dict, Tuple, Any

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, START, END

from .config import settings
from .rag import (
    init_rag_store,
    store_conversation,
    build_rag_context,
    store_mission_beat,
    STORY_BEATS,
)

# ==================== Initialize RAG on module load ====================
try:
    init_rag_store()
except Exception as e:
    print(f"[RAG Init Warning] {e}")

# ==================== NPC Agent Roster — Duskendale ====================
NPC_ROSTER: Dict[str, Dict[str, Any]] = {
    "sarini": {
        "name": "Sarini",
        "title": "Potion Shop Owner",
        "location": "Sarini's Potion Shoppe",
        "pos": (898, 796),
        "color": "#8b5cf6",
        "avatar": "sarini.png",
        "avatar_talk": "sarini_talk.png",
        "voice": "Kore",
        "system_prompt": """You are Sarini, the potion shop owner of Sarini's Potion Shoppe in the village of Duskendale.
            You are an autonomous AI persona — a conversational agent with deep memory, personality, and world knowledge.
            PERSONALITY: Clipped, precise, and guarded. You don't trust easily. You talk in ingredients and half-warnings. You see the world through the lens of alchemy and wards.
            BACKSTORY: You've maintained the protective wards around Duskendale for years. Recently, your wards have been failing — something is draining the magic from the village. You suspect it's connected to whatever Sir Besrand the Last sealed beneath the crossroads well decades ago.
            KNOWLEDGE: You know about the sealed vault, the old magic that was drained overnight, and Sir Besrand's sacrifice. You've noticed your wards weakening and your potions losing potency. You suspect someone is tampering with forces below the village.
            SAMPLE VOICE: "Wards don't just fail, dear. Something's eating them. That's a taste I know, and I don't like it in my mouth." "You want a truth potion or you want to actually be told the truth? Different prices."
            IMPORTANT VOICE RULE: Speak in clean, complete spoken plain text (2-3 sentences max). Do NOT use stage directions, action tags, asterisks, or brackets so your spoken voice plays completely without stopping."""
    },
    "merowin": {
        "name": "Merowin",
        "title": "Traveling Peddler",
        "location": "Eastern Road",
        "pos": (1602, 732),
        "color": "#f59e0b",
        "avatar": "merowin.png",
        "avatar_talk": "merowin_talk.png",
        "voice": "Puck",
        "system_prompt": """You are Merowin, a traveling peddler whose wagon is stationed on the eastern road of Duskendale.
            You are an autonomous AI persona — a conversational agent with deep memory, personality, and world knowledge.
            PERSONALITY: Jovial, theatrical, and opportunistic. You love bartering and believe everything has a price. You're observant and know everyone's business.
            BACKSTORY: You've been coming to Duskendale every spring for seven years. This year is different — you've been hired by someone wealthy to quietly transport heavy crates of excavation gear to Midnight Manor under cover of darkness. The coin is triple your normal rate, but you're getting nervous.
            KNOWLEDGE: You know about Lord Voss's secret shipments, the rumors about Midnight Manor, and the strange metallic sounds coming from the old well at midnight. You're worried something bad is going to happen and might be willing to talk if approached right.
            SAMPLE VOICE: "Finest wares in the valley! Need a trinket? A charm? Or perhaps a little... discreet information? Everything has a price, friend." "Those crates? Heavy as lead. Delivered 'em to the Manor myself. Paid in coin older than my grandfather."
            IMPORTANT VOICE RULE: Speak in clean, complete spoken plain text (2-3 sentences max). Do NOT use stage directions, action tags, asterisks, or brackets so your spoken voice plays completely without stopping."""
    },
    "adalric": {
        "name": "Father Adalric",
        "title": "Village Priest",
        "location": "Temple of Kord",
        "pos": (670, 948),
        "color": "#10b981",
        "avatar": "adalric.png",
        "avatar_talk": "adalric.png",
        "voice": "Charon",
        "system_prompt": """You are Father Adalric, the elderly village priest at the Temple of Kord in Duskendale.
            You are an autonomous AI persona — a conversational agent with deep memory, personality, and world knowledge.
            PERSONALITY: Somber, devout, and burdened by guilt. You speak in quiet, measured tones. You feel personally responsible for the village's spiritual and physical safety.
            BACKSTORY: You were a young acolyte when Sir Besrand the Last sealed the vault beneath the crossroads well forty years ago. You swore an oath never to speak of what was buried there. But now the holy symbols in the temple are weeping dark oil, and you know the seal is weakening.
            KNOWLEDGE: You hold the original text of Sir Besrand's covenant. You know that the seal requires three conditions to remain intact, and one has already broken. You fear the vault cannot be resealed once opened.
            SAMPLE VOICE: "The bells ring differently now. Heavier. Like they're tolling for something that hasn't died yet." "Sir Besrand made us swear. Forty years I've kept silent, but silence won't save us from what's waking."
            IMPORTANT VOICE RULE: Speak in clean, complete spoken plain text (2-3 sentences max). Do NOT use stage directions, action tags, asterisks, or brackets so your spoken voice plays completely without stopping."""
    },
    "fenn": {
        "name": "Fenn Ironhand",
        "title": "Master Blacksmith",
        "location": "Fang Rock Forge",
        "pos": (852, 1084),
        "color": "#64748b",
        "avatar": "fenn.png",
        "avatar_talk": "fenn.png",
        "voice": "Aoede",
        "system_prompt": """You are Fenn Ironhand, the master blacksmith at Fang Rock Forge in Duskendale.
            You are an autonomous AI persona — a conversational agent with deep memory, personality, and world knowledge.
            PERSONALITY: Gruff, pragmatic, and fiercely proud of your craft. You speak plainly and don't care for superstition. But you're deeply troubled by something you can't explain.
            BACKSTORY: Your family has worked the forge at Fang Rock for four generations. Three days ago, every piece of iron in your workshop developed fine fractures overnight. Not rust — fractures, like the metal was screaming under pressure from deep underground.
            KNOWLEDGE: You repaired the reinforced hinges on the crossroads well cover six months ago and noticed the masonry underneath had been chipped away from the inside. You know the layout of the old mining tunnels that run beneath the village.
            SAMPLE VOICE: "Iron doesn't crack on its own. It takes heat or hammer. Neither touched these blades. Something under our feet is shaking the bones of the rock." "You want a sword? Come back when the forge stays lit. Fire won't catch today. Wrong air."
            IMPORTANT VOICE RULE: Speak in clean, complete spoken plain text (2-3 sentences max). Do NOT use stage directions, action tags, asterisks, or brackets so your spoken voice plays completely without stopping."""
    },
    "voss": {
        "name": "Voss Kestrian",
        "title": '"Lord" of Midnight Manor',
        "location": "Midnight Manor",
        "pos": (490, 442),
        "color": "#dc2626",
        "avatar": "voss.png",
        "avatar_talk": "voss.png",
        "voice": "Fenrir",
        "system_prompt": """You are Voss Kestrian, the self-styled "Lord" of Midnight Manor on the lake island of Duskendale.
            You are an autonomous AI persona — a conversational agent with deep memory, personality, and world knowledge.
            PERSONALITY: Warm, articulate, and charming — but you never quite answer the question you were asked. You're the villain of this story, but you don't see yourself that way. You believe you're a scholar seeking knowledge, not a monster.
            BACKSTORY: You arrived in Duskendale eight months ago with old coin and older manners. You bought the abandoned manor outright and have been the perfect neighbor — generous at the Frosty Dragon tavern, polite at the Temple, free with gossip. But secretly, you've been digging a tunnel from your manor's cellar, under the lake, toward the sealed well. You believe the vault holds ancient knowledge, not a monster. You're not entirely wrong — but you're not entirely right either, and you're willing to gamble the whole village to find out.
            KNOWLEDGE: You know about Sir Besrand's seal, the vault, and the old magic. You fund your dig with smuggled reagents moved through the Black Lotus, using Merowin's wagon as an unwitting courier. You genuinely don't want anyone hurt — you can be reasoned with, bribed, or exposed publicly.
            SAMPLE VOICE: "Sir Besrand sealed a door. I intend to open it politely and ask what's on the other side. Is that so villainous?" "You've mistaken caution for cowardice, friend. I've simply done the math you haven't."
            IMPORTANT VOICE RULE: Speak in clean, complete spoken plain text (2-3 sentences max). Do NOT use stage directions, action tags, asterisks, or brackets so your spoken voice plays completely without stopping."""
    },
}


# ==================== Graph State ====================
class MultiNPCState(TypedDict):
    npc_id: str
    messages: List[BaseMessage]
    user_audio_path: Optional[str]
    user_text: str
    npc_text: str
    npc_audio_path: Optional[str]
    npc_audio_base64: Optional[str]
    player_pos: Tuple[int, int]
    vault_threat: str
    rag_context: str


# ==================== Text Cleaning ====================
def clean_text_for_tts(text: str) -> str:
    """Cleans text so Text-to-Speech synthesizes the entire response fully without stopping."""
    if not text:
        return ""
    text = str(text).strip()

    # Strip bracketed character prefixes like "[Voss Kestrian]:" or "[Sarini]:"
    text = re.sub(r'^\[[A-Za-z\s\']+\]:\s*', '', text)

    # Remove bracketed actions [looks around], parenthesized notes, asterisk actions *nods*, and markdown
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'\*.*?\*', '', text)
    text = re.sub(r'[*#_`~]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ==================== Node: STT & Input Processing ====================
def stt_and_input_processor(state: MultiNPCState) -> dict:
    """Processes user input. Transcribes voice input via Gemini 3.5 Transcribe if provided."""
    user_audio = state.get("user_audio_path")
    user_text = state.get("user_text", "").strip()

    if not user_text and user_audio and os.path.exists(user_audio):
        transcribed_text = ""

        # Step 1: Ultra-fast STT via Groq Cloud Whisper (whisper-large-v3-turbo)
        groq_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                from groq import Groq
                groq_client = Groq(api_key=groq_key)
                with open(user_audio, "rb") as f:
                    audio_content = f.read()
                filename = os.path.basename(user_audio)
                stt_res = groq_client.audio.transcriptions.create(
                    file=(filename, audio_content),
                    model="whisper-large-v3-turbo",
                )
                if stt_res and stt_res.text and stt_res.text.strip():
                    transcribed_text = stt_res.text.strip()
            except Exception as groq_err:
                print(f"[Groq Whisper STT Warning] {groq_err}. Falling back to Gemini STT...")

        # Step 2: Fallback to Gemini STT if Groq was empty or unavailable
        if not transcribed_text.strip():
            try:
                api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
                if api_key:
                    client = genai.Client(api_key=api_key)

                    with open(user_audio, "rb") as f:
                        audio_bytes = f.read()

                    ext = user_audio.rsplit(".", 1)[-1].lower() if "." in user_audio else "webm"
                    mime_map = {
                        "webm": "audio/webm",
                        "wav": "audio/wav",
                        "mp3": "audio/mpeg",
                        "ogg": "audio/ogg",
                        "m4a": "audio/mp4",
                        "mp4": "audio/mp4",
                    }
                    mime_type = mime_map.get(ext, "audio/webm")

                    stt_model = settings.gemini_stt_model or "gemini-3.5-transcribe"
                    try:
                        response = client.models.generate_content(
                            model=stt_model,
                            contents=[
                                types.Content(
                                    parts=[
                                        types.Part.from_bytes(
                                            data=audio_bytes,
                                            mime_type=mime_type,
                                        ),
                                    ]
                                )
                            ],
                        )
                        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                            for part in response.candidates[0].content.parts:
                                if hasattr(part, "audio_transcription") and part.audio_transcription:
                                    transcribed_text += getattr(part.audio_transcription, "text", "") or ""
                                elif hasattr(part, "text") and part.text:
                                    transcribed_text += part.text or ""
                        elif response.text:
                            transcribed_text = response.text
                    except Exception as stt_err:
                        print(f"[Gemini STT Warning] {stt_model}: {stt_err}. Falling back to multimodal Flash...")

                    if not transcribed_text.strip():
                        try:
                            fallback_model = settings.gemini_model or "gemini-3.6-flash"
                            fb_response = client.models.generate_content(
                                model=fallback_model,
                                contents=[
                                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                                    "Transcribe the exact words spoken in this audio. Output only the verbatim transcript with no commentary, quotes, or formatting."
                                ]
                            )
                            if fb_response.text and fb_response.text.strip():
                                transcribed_text = fb_response.text.strip().strip('"\'')
                        except Exception as fb_err:
                            print(f"[Fallback Gemini STT Error] {fb_err}")

            except Exception as e:
                print(f"[Gemini STT General Error] {e}")

        user_text = transcribed_text.strip()

    # Fallback only if both text and audio were completely empty
    if not user_text:
        if user_audio:
            user_text = "(inaudible speech)"
        else:
            user_text = "Hello!"

    updated_messages = list(state.get("messages", []))
    updated_messages.append(HumanMessage(content=user_text))

    # Store player conversation in RAG
    npc_id = state.get("npc_id", "sarini")
    try:
        store_conversation(npc_id, "player", user_text)
    except Exception as e:
        print(f"[RAG Store Error] {e}")

    return {
        "user_text": user_text,
        "messages": updated_messages,
    }


# ==================== Node: RAG Context Retrieval ====================
def rag_retriever_node(state: MultiNPCState) -> dict:
    """Retrieves relevant context from RAG memory to inject into the NPC's reasoning."""
    npc_id = state.get("npc_id", "sarini")
    user_text = state.get("user_text", "")

    rag_context = ""
    try:
        rag_context = build_rag_context(npc_id, user_text)
    except Exception as e:
        print(f"[RAG Retrieval Error] {e}")

    return {
        "rag_context": rag_context,
    }


# ==================== Node: NPC Reasoning (Gemini LLM) ====================
def npc_reasoning_node(state: MultiNPCState) -> dict:
    """Invokes Gemini via LangChain for autonomous NPC dialogue generation with RAG context."""
    api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
    npc_id = state.get("npc_id", "sarini")
    npc_info = NPC_ROSTER.get(npc_id, NPC_ROSTER["sarini"])

    if not api_key:
        npc_text = f"[{npc_info['name']}]: I cannot hear you. (Please set your GEMINI_API_KEY in .env!)"
    else:
        try:
            llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=api_key,
                temperature=0.7,
                max_output_tokens=300,
                max_retries=1,
            )

            # Build enhanced system prompt with RAG context
            base_prompt = npc_info["system_prompt"]
            rag_context = state.get("rag_context", "")

            if rag_context:
                enhanced_prompt = (
                    f"{base_prompt}\n\n"
                    f"--- RETRIEVED MEMORY & CONTEXT ---\n"
                    f"Use the following retrieved context naturally in your response. "
                    f"Reference past conversations if relevant. Do not repeat them verbatim.\n\n"
                    f"{rag_context}\n"
                    f"--- END CONTEXT ---"
                )
            else:
                enhanced_prompt = base_prompt

            sys_msg = SystemMessage(content=enhanced_prompt)
            prompt_messages = [sys_msg] + state.get("messages", [])

            response = llm.invoke(prompt_messages)
            raw_content = response.content

            if isinstance(raw_content, list):
                text_parts = []
                for part in raw_content:
                    if isinstance(part, dict) and "text" in part:
                        text_parts.append(str(part["text"]))
                    elif isinstance(part, str):
                        text_parts.append(part)
                    else:
                        text_parts.append(str(part))
                npc_text = " ".join(text_parts).strip()
            else:
                npc_text = str(raw_content).strip()
        except Exception as e:
            # Fallback to Groq LLM if Gemini hits quota limits or fails
            groq_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
            fallback_success = False
            if groq_key:
                try:
                    from groq import Groq
                    groq_client = Groq(api_key=groq_key)
                    chat_history = [{"role": "system", "content": enhanced_prompt}]
                    for msg in state.get("messages", []):
                        role = "user" if isinstance(msg, HumanMessage) else "assistant"
                        chat_history.append({"role": role, "content": str(msg.content)})
                    groq_res = groq_client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=chat_history,
                        max_tokens=300,
                        temperature=0.7,
                    )
                    if groq_res and groq_res.choices:
                        npc_text = groq_res.choices[0].message.content.strip()
                        fallback_success = True
                except Exception as groq_llm_err:
                    print(f"[Groq LLM Fallback Warning] {groq_llm_err}")

            if not fallback_success:
                print(f"[Dialogue Reasoning Error] {e}")
                npc_text = f"[{npc_info['name']}]: (Error communicating: {str(e)})"

    updated_messages = list(state.get("messages", []))
    updated_messages.append(AIMessage(content=npc_text))

    # Store NPC response in RAG memory
    try:
        store_conversation(npc_id, npc_info["name"], str(npc_text))
    except Exception as e:
        print(f"[RAG Store Error] {e}")

    return {
        "npc_text": npc_text,
        "messages": updated_messages,
    }


# ==================== Node: Mission Tracker ====================
def mission_tracker_node(state: MultiNPCState) -> dict:
    """
    Detects story beat triggers from the conversation and records them.
    Checks user text and NPC response for mission-relevant keywords.
    """
    user_text = (state.get("user_text", "") or "").lower()
    npc_text = (state.get("npc_text", "") or "").lower()
    npc_id = state.get("npc_id", "")
    combined = user_text + " " + npc_text

    try:
        # Beat 1: Hook — rusted tools / failing wards
        if npc_id in ("fenn", "sarini"):
            if any(w in combined for w in ["rust", "rusted", "wards fail", "failing ward", "corroded", "overnight"]):
                store_mission_beat("hook_rusted_tools", f"Discovered via {npc_id}")

        # Beat 2: Trail — Merowin's delivery
        if npc_id == "merowin":
            if any(w in combined for w in ["delivery", "crate", "manor", "discreet", "triple", "paid"]):
                store_mission_beat("trail_discreet_delivery", "Merowin revealed the deliveries")

        # Beat 3: Confrontation — Voss
        if npc_id == "voss":
            if any(w in combined for w in ["tunnel", "digging", "vault", "seal", "besrand"]):
                store_mission_beat("confrontation_voss", "Player confronted Voss about the vault")

        # Beat 4: Climax — vault door
        if any(w in combined for w in ["open the vault", "reseal", "vault door", "what's inside"]):
            store_mission_beat("climax_vault_door", "The vault decision approaches")

    except Exception as e:
        print(f"[Mission Tracker Error] {e}")

    return {}


# ==================== Node: TTS (Groq Cloud TTS with Gemini & Web Speech Fallbacks) ====================
def tts_node(state: MultiNPCState) -> dict:
    """Converts NPC response text to speech using Groq Cloud TTS, Gemini TTS, or browser fallback."""
    npc_text = state.get("npc_text", "")
    npc_id = state.get("npc_id", "sarini")
    npc_info = NPC_ROSTER.get(npc_id, NPC_ROSTER["sarini"])
    audio_path = None
    audio_base64 = None

    if npc_text:
        speech_text = clean_text_for_tts(npc_text)
        if speech_text:
            # Step 1: Try Groq Cloud TTS (canopylabs/orpheus-v1-english)
            groq_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
            if groq_key:
                try:
                    from groq import Groq
                    groq_client = Groq(api_key=groq_key)
                    # Select voice tailored to character
                    groq_voice = "alloy"
                    if npc_id == "sarini":
                        groq_voice = "shimmer"
                    elif npc_id == "voss":
                        groq_voice = "onyx"
                    elif npc_id == "fenn":
                        groq_voice = "echo"
                    elif npc_id == "merowin":
                        groq_voice = "fable"

                    speech_res = groq_client.audio.speech.create(
                        model="canopylabs/orpheus-v1-english",
                        voice=groq_voice,
                        input=speech_text,
                    )
                    audio_content = speech_res.read()
                    if audio_content:
                        b64_str = base64.b64encode(audio_content).decode("utf-8")
                        audio_base64 = f"data:audio/wav;base64,{b64_str}"

                        tmp_dir = tempfile.gettempdir()
                        audio_name = f"npc_speech_{int(time.time() * 1000)}.wav"
                        audio_path = os.path.join(tmp_dir, audio_name)
                        with open(audio_path, "wb") as f:
                            f.write(audio_content)
                except Exception as groq_tts_err:
                    print(f"[Groq TTS Notice] {groq_tts_err}. Trying Gemini TTS fallback...")

            # Step 2: Fallback to Gemini TTS (gemini-3.1-flash-tts-preview) if Groq is pending terms or errored
            if not audio_base64:
                api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
                if api_key:
                    try:
                        client = genai.Client(api_key=api_key)
                        voice_name = npc_info.get("voice", "Kore")

                        config = types.GenerateContentConfig(
                            response_modalities=["AUDIO"],
                            speech_config=types.SpeechConfig(
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=voice_name
                                    )
                                )
                            ),
                        )

                        tts_model = settings.gemini_tts_model or "gemini-3.1-flash-tts-preview"
                        audio_data = None
                        try:
                            response = client.models.generate_content(
                                model=tts_model,
                                contents=speech_text,
                                config=config,
                            )
                            if (
                                response.candidates
                                and response.candidates[0].content
                                and response.candidates[0].content.parts
                            ):
                                part_data = response.candidates[0].content.parts[0].inline_data.data
                                if part_data:
                                    audio_data = part_data
                        except Exception as m_err:
                            print(f"[Gemini TTS Warning] Model {tts_model} failed or quota exceeded: {m_err}")

                        if audio_data:
                            sample_rate = 24000
                            num_channels = 1
                            sample_width = 2  # 16-bit

                            wav_buf = io.BytesIO()
                            with wave.open(wav_buf, "wb") as wav_file:
                                wav_file.setnchannels(num_channels)
                                wav_file.setsampwidth(sample_width)
                                wav_file.setframerate(sample_rate)
                                wav_file.writeframes(audio_data)

                            wav_bytes = wav_buf.getvalue()
                            b64_str = base64.b64encode(wav_bytes).decode("utf-8")
                            audio_base64 = f"data:audio/wav;base64,{b64_str}"

                            tmp_dir = tempfile.gettempdir()
                            audio_name = f"npc_speech_{int(time.time() * 1000)}.wav"
                            audio_path = os.path.join(tmp_dir, audio_name)
                            with open(audio_path, "wb") as f:
                                f.write(wav_bytes)

                    except Exception as e:
                        print(f"[Gemini TTS General Error] {e}")

    return {
        "npc_audio_path": audio_path,
        "npc_audio_base64": audio_base64,
    }


# ==================== Node: State Updater ====================
def state_update_node(state: MultiNPCState) -> dict:
    """Final state cleanup node."""
    return {}


# ==================== Build LangGraph Workflow ====================
workflow = StateGraph(MultiNPCState)

workflow.add_node("input_processor", stt_and_input_processor)
workflow.add_node("rag_retriever", rag_retriever_node)
workflow.add_node("npc_brain", npc_reasoning_node)
workflow.add_node("mission_tracker", mission_tracker_node)
workflow.add_node("tts_generator", tts_node)
workflow.add_node("state_updater", state_update_node)

# Pipeline: STT → RAG → LLM → Mission Tracker → TTS → Done
workflow.add_edge(START, "input_processor")
workflow.add_edge("input_processor", "rag_retriever")
workflow.add_edge("rag_retriever", "npc_brain")
workflow.add_edge("npc_brain", "mission_tracker")
workflow.add_edge("mission_tracker", "tts_generator")
workflow.add_edge("tts_generator", "state_updater")
workflow.add_edge("state_updater", END)

npc_graph = workflow.compile()
