"""
Village Tales — RAG Memory System
Provides conversation memory, mission tracking, and lore grounding
using ChromaDB + Google Generative AI Embeddings.
"""

import os
import time
import uuid
from typing import List, Dict, Optional, Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from .config import settings

# ==================== Embedding Model ====================
_embeddings = None

def get_embeddings():
    """Lazy-initialize the Google Generative AI embeddings model."""
    global _embeddings
    if _embeddings is None:
        api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        _embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=api_key
        )
    return _embeddings

# ==================== ChromaDB Collections ====================
_conversation_store: Optional[Chroma] = None
_mission_store: Optional[Chroma] = None
_lore_store: Optional[Chroma] = None
_initialized = False

STORY_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "The Last Light of Duskendale.txt")
)


def init_rag_store():
    """
    Initialize all ChromaDB collections:
    - conversations: player↔NPC dialogue history
    - missions: story beat / quest progress tracking
    - world_knowledge: chunked lore from the Duskendale story
    """
    global _conversation_store, _mission_store, _lore_store, _initialized

    if _initialized:
        return

    embeddings = get_embeddings()

    # Conversation memory collection
    _conversation_store = Chroma(
        collection_name="conversations",
        embedding_function=embeddings,
    )

    # Mission tracking collection
    _mission_store = Chroma(
        collection_name="missions",
        embedding_function=embeddings,
    )

    # World knowledge / lore collection — pre-load story
    _lore_store = Chroma(
        collection_name="world_knowledge",
        embedding_function=embeddings,
    )

    # Load and chunk the story file into the lore store
    _load_world_knowledge()

    _initialized = True
    print("[RAG] Memory system initialized with 3 collections")


def _load_world_knowledge():
    """Load 'The Last Light of Duskendale' story into the lore vector store."""
    global _lore_store

    if not os.path.exists(STORY_FILE):
        print(f"[RAG] Warning: Story file not found at {STORY_FILE}")
        return

    with open(STORY_FILE, "r", encoding="utf-8") as f:
        story_text = f.read()

    # Split into meaningful chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n________________\n", "\n\n", "\n", ". ", " "]
    )

    chunks = splitter.split_text(story_text)
    documents = []

    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk.strip(),
            metadata={
                "source": "The Last Light of Duskendale",
                "chunk_index": i,
                "type": "lore"
            }
        )
        documents.append(doc)

    if documents:
        _lore_store.add_documents(documents)
        print(f"[RAG] Loaded {len(documents)} lore chunks into world_knowledge")


# ==================== Conversation Memory ====================

def store_conversation(npc_id: str, speaker: str, text: str):
    """
    Store a conversation turn in the vector store.
    
    Args:
        npc_id: The NPC agent ID (e.g., 'sarini', 'fenn')
        speaker: 'player' or the NPC name
        text: The dialogue content
    """
    global _conversation_store

    if not _initialized:
        init_rag_store()

    doc = Document(
        page_content=text,
        metadata={
            "npc_id": npc_id,
            "speaker": speaker,
            "timestamp": time.time(),
            "turn_id": str(uuid.uuid4()),
            "type": "conversation"
        }
    )

    _conversation_store.add_documents([doc])


def retrieve_relevant_context(npc_id: str, query: str, k: int = 3) -> List[str]:
    """
    Retrieve the most relevant past conversation snippets for a specific NPC.
    
    Args:
        npc_id: Filter conversations to this NPC
        query: The current user message to match against
        k: Number of results to return
    
    Returns:
        List of relevant past conversation strings
    """
    global _conversation_store

    if not _initialized:
        init_rag_store()

    try:
        results = _conversation_store.similarity_search(
            query,
            k=k,
            filter={"npc_id": npc_id}
        )
        return [
            f"[{doc.metadata.get('speaker', 'unknown')}]: {doc.page_content}"
            for doc in results
        ]
    except Exception as e:
        print(f"[RAG] Context retrieval error: {e}")
        return []


def retrieve_cross_agent_context(query: str, exclude_npc: str = "", k: int = 2) -> List[str]:
    """
    Retrieve conversations from OTHER NPCs for cross-agent awareness.
    Allows NPCs to reference what the player discussed with other characters.
    
    Args:
        query: The current conversation topic
        exclude_npc: NPC to exclude (the current one)
        k: Number of results to return
    
    Returns:
        List of cross-agent conversation snippets
    """
    global _conversation_store

    if not _initialized:
        init_rag_store()

    try:
        # Retrieve all relevant conversations
        results = _conversation_store.similarity_search(query, k=k + 2)

        # Filter out the current NPC's conversations
        cross_agent = []
        for doc in results:
            if doc.metadata.get("npc_id") != exclude_npc:
                npc_name = doc.metadata.get("npc_id", "unknown")
                speaker = doc.metadata.get("speaker", "unknown")
                cross_agent.append(
                    f"[Overheard from {npc_name} — {speaker}]: {doc.page_content}"
                )
            if len(cross_agent) >= k:
                break

        return cross_agent
    except Exception as e:
        print(f"[RAG] Cross-agent retrieval error: {e}")
        return []


# ==================== Mission Tracking ====================

# Story beats from "The Last Light of Duskendale"
STORY_BEATS = {
    "hook_rusted_tools": "Fenn's rusted tools + Sarini's failing wards discovered",
    "trail_discreet_delivery": "Merowin mentions the 'discreet delivery' to the Manor",
    "confrontation_voss": "Player confronts Voss Kestrian about the tunnel",
    "climax_vault_door": "The tunnel, the vault door, and the choice to reseal or open",
}


def store_mission_beat(beat_id: str, description: str = ""):
    """
    Record that a story beat has been triggered.
    
    Args:
        beat_id: One of the STORY_BEATS keys
        description: Additional context about how it was triggered
    """
    global _mission_store

    if not _initialized:
        init_rag_store()

    beat_text = STORY_BEATS.get(beat_id, description or beat_id)
    full_text = f"MISSION BEAT [{beat_id}]: {beat_text}"
    if description:
        full_text += f" — {description}"

    doc = Document(
        page_content=full_text,
        metadata={
            "beat_id": beat_id,
            "triggered_at": time.time(),
            "type": "mission"
        }
    )

    _mission_store.add_documents([doc])
    print(f"[RAG] Mission beat triggered: {beat_id}")


def get_active_missions() -> List[str]:
    """
    Return all triggered mission beats.
    
    Returns:
        List of mission beat descriptions
    """
    global _mission_store

    if not _initialized:
        init_rag_store()

    try:
        # Retrieve all mission documents by searching broadly
        results = _mission_store.similarity_search("mission story quest beat", k=10)
        return [doc.page_content for doc in results]
    except Exception as e:
        print(f"[RAG] Mission retrieval error: {e}")
        return []


# ==================== Lore Retrieval ====================

def retrieve_lore(query: str, k: int = 2) -> List[str]:
    """
    Retrieve relevant story/lore chunks to ground NPC responses.
    
    Args:
        query: The topic to search for in the story
        k: Number of lore chunks to return
    
    Returns:
        List of relevant lore text snippets
    """
    global _lore_store

    if not _initialized:
        init_rag_store()

    try:
        results = _lore_store.similarity_search(query, k=k)
        return [doc.page_content for doc in results]
    except Exception as e:
        print(f"[RAG] Lore retrieval error: {e}")
        return []


# ==================== Composite Context Builder ====================

def build_rag_context(npc_id: str, user_message: str) -> str:
    """
    Build a comprehensive RAG context string for the NPC reasoning node.
    Combines: relevant past conversations + cross-agent intel + lore + missions.
    
    Args:
        npc_id: The current NPC being spoken to
        user_message: The player's current message
    
    Returns:
        Formatted context string to inject into the system prompt
    """
    sections = []

    # 1. Past conversations with this NPC
    past_convos = retrieve_relevant_context(npc_id, user_message, k=3)
    if past_convos:
        sections.append("=== PAST CONVERSATIONS (your memory) ===")
        sections.extend(past_convos)

    # 2. Cross-agent awareness
    cross_agent = retrieve_cross_agent_context(user_message, exclude_npc=npc_id, k=2)
    if cross_agent:
        sections.append("\n=== VILLAGE RUMORS (what you've heard from others) ===")
        sections.extend(cross_agent)

    # 3. Relevant lore
    lore = retrieve_lore(user_message, k=2)
    if lore:
        sections.append("\n=== WORLD KNOWLEDGE (things you know about Duskendale) ===")
        sections.extend(lore)

    # 4. Active missions
    missions = get_active_missions()
    if missions:
        sections.append("\n=== CURRENT EVENTS IN DUSKENDALE ===")
        sections.extend(missions)

    if not sections:
        return ""

    return "\n".join(sections)
