# Village Tales: AI Personification Simulator

## Overview
- What: A lightweight multi-agent conversational system where AI characters represent villagers of Duskendale.
- Why: To create interactive persona-driven characters with distinct dialogue, local lore awareness, and voice capabilities instead of generic chatbots.
- How: Built with LangGraph for agent orchestration, Google Gemini for LLM dialogue, Gemini STT/TTS for voice interaction, and ChromaDB for retrieval-augmented memory.

## Architecture
- What: A stateful agent pipeline managing character personas, memory retrieval, and speech processing.
- Why: To ensure each character responds consistently according to their unique backstory and remembers prior interactions.
- How: User input passes through Gemini STT (if audio), retrieves relevant story chunks via ChromaDB embeddings, generates in-character responses using Gemini 3.6 Flash, records mission beats, and synthesizes character voices using Gemini 3.1 Flash TTS.

## Characters and Roles
- What: Five distinct AI characters situated across the Duskendale map (Sarini, Merowin, Brother Adalric, Fenn, and Voss Kestrian).
- Why: To give users different perspectives on the village lore and unfolding storyline.
- How: Defined with dedicated system prompts, distinct spatial coordinates on the village map, theme colors, and separate voice profiles.

## RAG and Memory
- What: A vector-based memory store containing the story text from The Last Light of Duskendale and ongoing conversation history.
- Why: To ground agent knowledge in canonical world events and allow characters to remember past dialogues.
- How: Implemented using ChromaDB and Google Generative AI embeddings (gemini-embedding-001), segmenting the lore text into searchable chunks and querying relevant context on each interaction.

## Interactive Map Navigation
- What: A 2D spatial interface displaying character avatars and the player position.
- Why: To provide spatial context for agent encounters and trigger dialogues based on proximity.
- How: Rendered dynamically via Pillow with character avatar portraits and proximity detection zones, supporting directional movement controls and click-to-move navigation.

## Setup and Running
- What: Local environment requirements and startup instructions.
- Why: To run and test the simulation locally.
- How:
  1. Clone the repository:
     ```bash
     git clone https://github.com/JapjeetSingh17/VillageTales-AI-Personification-Simulator.git
     cd VillageTales-AI-Personification-Simulator
     ```
  2. Create and activate a virtual environment:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
  3. Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```
  4. Create a .env file with your Gemini API key:
     ```env
     GEMINI_API_KEY=your_gemini_api_key_here
     GEMINI_MODEL=gemini-3.6-flash
     GEMINI_TTS_MODEL=gemini-3.1-flash-tts-preview
     GEMINI_STT_MODEL=gemini-3.5-transcribe
     ```
  5. Run the application:
     ```bash
     python -m app.main
     ```
  6. Open http://127.0.0.1:7860 in your browser.
