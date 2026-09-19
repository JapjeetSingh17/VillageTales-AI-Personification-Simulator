# Village Tales: AI Personification Simulator

## Overview
- Built a lightweight multi-agent personification simulator using LangGraph, Google Gemini, and ChromaDB to power autonomous village characters with persistent memory and multimodal voice interactions.

## Architecture and Pipeline
- Engineered a stateful dialogue graph utilizing LangChain and LangGraph to maintain character persona consistency, memory grounding, and voice synthesis across conversation turns.
- Integrated Google Gemini 3.6 Flash with Gemini STT and Gemini 3.1 Flash TTS Preview to deliver low-latency speech-to-speech dialogue tailored to individual character voice profiles.

## Retrieval-Augmented Memory (RAG)
- Implemented a vector memory system using ChromaDB and Gemini embeddings to ground character responses in canonical Duskendale lore and recall past player dialogue.
- Automated story progression tracking by evaluating conversation turns against narrative milestones to dynamically update village quests.

## Spatial Interface and Navigation
- Developed a dynamic 2D map renderer using Pillow and FastAPI to visualize character locations with custom avatar portrait tokens and proximity-detection zones.
- Added coordinate-based click-to-move navigation and directional controls to enable fluid spatial movement and proximity-triggered dialogue.

## Setup and Running
1. Clone the repository:
   ```bash
   git clone https://github.com/JapjeetSingh17/VillageTales-AI-Personification-Simulator.git
   cd VillageTales-AI-Personification-Simulator
   ```
2. Set up virtual environment and dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Configure environment variables in `.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-3.6-flash
   GEMINI_TTS_MODEL=gemini-3.1-flash-tts-preview
   GEMINI_STT_MODEL=gemini-3.5-transcribe
   ```
4. Start the application:
   ```bash
   python -m app.main
   ```
   Open http://127.0.0.1:7860 in your browser.
