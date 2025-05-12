# =============================
# AI Podcast Generator Server
# =============================
# This script sets up a web API to generate podcast scripts and audio
# using OpenAI's GPT-3.5-turbo model and ElevenLabs TTS service.

import os  # Access environment variables for secure key storage
import base64  # Convert binary audio data to Base64 for JSON
import requests  # Perform HTTP requests to external APIs
from fastapi import FastAPI, HTTPException  # Web framework and HTTP errors
from pydantic import BaseModel  # Data validation and serialization
import openai  # OpenAI SDK for text generation
from openai.error import RateLimitError, OpenAIError  # Handle API-specific exceptions
from fastapi.middleware.cors import CORSMiddleware  # Allow cross-origin requests for frontend

# -----------------------------
# Configuration and Initialization
# -----------------------------
# Load API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Key for OpenAI API
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")  # Key for ElevenLabs TTS API

# Validate presence of required keys
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable!")
if not ELEVENLABS_API_KEY:
    raise RuntimeError("Missing ELEVENLABS_API_KEY environment variable!")

# Configure OpenAI client
openai.api_key = OPENAI_API_KEY  # Set the API key for OpenAI SDK

# Initialize FastAPI app
app = FastAPI()  # Create FastAPI application instance
# Setup CORS to allow any origin (for ease during development/demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# -----------------------------
# Data Models
# -----------------------------
class PodcastRequest(BaseModel):
    """
    Defines the incoming JSON payload for the podcast request.
    - topic: The subject or title of the desired podcast script.
    - voice_id: The ElevenLabs voice name or UUID for TTS.
    """
    topic: str         # Topic string provided by the user
    voice_id: str = "Aria"  # Default voice if none provided

class PodcastResponse(BaseModel):
    """
    Defines the JSON response format.
    - script: Generated podcast script text.
    - audio_base64: Base64-encoded MP3 audio of the script.
    - tts_error: Any error message encountered during TTS.
    """
    script: str       # Full text of generated podcast
    audio_base64: str  # Base64-encoded MP3 audio data
    tts_error: str = ""  # Empty string if no error

# -----------------------------
# Helper Functions: Script Generation
# -----------------------------
def generate_with_openai(topic: str) -> str:
    """
    Calls OpenAI's ChatCompletion API to generate a 500–800 word podcast script.
    - Builds a system prompt enforcing structure and tone.
    - Sends the topic as a user message.
    - Returns the generated text.
    """
    system_prompt = (
        "You are a professional podcast scriptwriter. "
        "Write a thorough 500–800 word podcast episode script on the given topic. "
        "Include an introduction, three detailed sections with examples and data, "
        "smooth transitions, and a closing summary with a call-to-action."
    )
    user_prompt = f"Topic: \"{topic}\""  # Insert the topic into the user prompt

    # Make the API call
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Chat model capable of conversation-style output
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=1500,  # Maximum tokens to generate
        temperature=0.7,  # Controls randomness/creativity
        top_p=1.0         # Nucleus sampling parameter
    )
    # Extract and return the script
    return resp.choices[0].message.content.strip()


def generate_template(topic: str) -> str:
    """
    Returns a static podcast outline as fallback when OpenAI rate limits.
    Provides a basic structure without external API calls.
    """
    return (
        f"[Intro]\nWelcome to our deep dive on “{topic}.” In today’s episode...\n\n"
        f"[Section 1: Definition]\nDefine {topic} clearly...\n\n"
        f"[Section 2: Current Challenges]\nDiscuss challenges...\n\n"
        f"[Section 3: Real-world Examples]\nShare examples...\n\n"
        f"[Closing]\nThank you for listening to {topic}!"
    )

# -----------------------------
# Helper Functions: Voice & TTS
# -----------------------------
def resolve_voice_id(voice_name_or_uuid: str) -> str:
    """
    Resolves a voice name or UUID into a valid ElevenLabs voice_id.
    - If input is already UUID, returns directly.
    - Otherwise, fetches available voices and matches by name.
    """
    # Detect if it's a UUID format
    if len(voice_name_or_uuid) == 36 and voice_name_or_uuid.count('-') == 4:
        return voice_name_or_uuid

    # Fetch voice list from ElevenLabs
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()  # Raise exception for HTTP errors

    # Search for matching name
    for v in r.json().get("voices", []):
        if v.get("name", "").lower() == voice_name_or_uuid.lower():
            return v["voice_id"]

    # If not found, raise with list of options
    available = [v["name"] for v in r.json().get("voices", [])]
    raise ValueError(f"Voice '{voice_name_or_uuid}' not found. Available: {available}")


def synthesize_tts(text: str, voice_input: str) -> (bytes, str):
    """
    Sends text to ElevenLabs TTS API to get MP3 audio.
    - Resolves voice ID.
    - Posts text with voice settings.
    - Returns raw bytes and error message if any.
    """
    try:
        voice_id = resolve_voice_id(voice_input)
    except Exception as e:
        return b"", f"Voice lookup error: {e}"  # Return on resolution failure

    # Construct TTS API request
    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
        f"?optimize_streaming_latency=0"
    )
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.content, ""  # Success: return audio bytes
    except Exception as e:
        return b"", str(e)  # Failure: return error string

# -----------------------------
# API Endpoint: Generate Podcast
# -----------------------------
@app.post("/generate_podcast/", response_model=PodcastResponse)
async def generate_podcast(req: PodcastRequest):
    """
    Main API endpoint that:
    1. Generates a podcast script via OpenAI (or template fallback).
    2. Converts script to speech via ElevenLabs TTS.
    3. Encodes audio as Base64 and returns both script and audio.
    """
    try:
        # Attempt dynamic script generation
        script = generate_with_openai(req.topic)
    except RateLimitError:
        # Fallback when rate-limited by OpenAI
        script = generate_template(req.topic)
    except OpenAIError as e:
        # Critical OpenAI error
        raise HTTPException(status_code=500, detail=f"OpenAI error: {e}")

    # Synthesize speech from script
    audio_bytes, tts_error = synthesize_tts(script, req.voice_id)
    if not audio_bytes and not tts_error:
        tts_error = "Unknown TTS failure"  # Catch-all error message

    # Encode audio for JSON transport
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8") if audio_bytes else ""

    # Return the combined response
    return PodcastResponse(
        script=script,
        audio_base64=audio_b64,
        tts_error=tts_error
    )
