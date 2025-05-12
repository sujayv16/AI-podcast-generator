# AI Podcast Generator

Generate professional podcast scripts and lifelike audio using OpenAI's GPT-3.5-turbo and ElevenLabs Text-to-Speech. This project provides a FastAPI backend and a simple web frontend for instant podcast creation.

## Demo

Check out a demo of this project here:

[Demo Link](https://drive.google.com/file/d/1iMd_CWQUOOhpFZza3dRS0PpO_u9zsi_I/view?usp=drivesdk) 

## Features

- Generate detailed podcast scripts (500–800 words) on any topic using OpenAI GPT-3.5-turbo.
- Convert scripts to high-quality audio with ElevenLabs TTS (multiple voices supported).
- REST API for integration and automation.
- Simple web UI for interactive use.

---

## Requirements

- Python 3.8+
- OpenAI API key
- ElevenLabs API key
- See `requirements.txt` for dependencies.

---

## Setup

1. **Clone the repository**
    ```
    git clone https://github.com/sujayv16/AI-podcast-generator.git
    cd AI-podcast-generator
    ```

2. **Install dependencies**
    ```
    pip install -r requirements.txt
    ```

3. **Set environment variables**

    Create a `.env` file or export these variables:
    ```
    OPENAI_API_KEY=your_openai_api_key
    ELEVENLABS_API_KEY=your_elevenlabs_api_key
    ```

4. **Run the FastAPI server**
    ```
    uvicorn main:app --reload
    ```

    The API will be available at `http://localhost:8000`.

---

## Usage

### Web UI

Open `index.html` in your browser. Enter a topic and select a voice to generate a podcast script and audio.



