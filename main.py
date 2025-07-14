from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import ssl
import json
import datetime
from pathlib import Path
from langdetect import detect
from googletrans import Translator

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set your Gemini API Key and model
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyB3HLb0TmvqHCoovYqYaSq0fJvHARn9FXk")
# GEMINI_MODEL = "gemini-1.5-pro"  # ✅ FIXED model name

TRANSCRIPT_DIR = Path("transcripts")
TRANSCRIPT_DIR.mkdir(exist_ok=True)

translator = Translator()

@app.post("/generate-feedback")
async def generate_feedback(request: Request):
    try:
        body = await request.json()
        prompt = body.get("prompt", "").strip()
        print("🟢 Prompt received:\n", prompt)

        if not prompt:
            return {"error": "Prompt is empty"}

        payload = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
        print("🌐 Sending POST request to:", url)

        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:  # ✅ Bypass SSL, increase timeout
            try:
                response = await client.post(url, json=payload)
                print("🟡 Status code:", response.status_code)
                print("🟡 Raw response text:", response.text)

                try:
                    result = response.json()
                    print("✅ Parsed Gemini result:", result)
                    return result
                except Exception as e:
                    print("❌ Failed to parse JSON:", str(e))
                    return {"error": f"Failed to parse JSON response: {str(e)}", "raw": response.text}

            except httpx.HTTPError as http_err:
                print("❌ HTTP error during POST:", str(http_err))
                return {"error": f"HTTP error: {str(http_err)}"}

    except Exception as e:
        print("🔴 Top-level Exception occurred:", str(e))
        return {"error": str(e)}


@app.post("/save-transcript")
async def save_transcript(request: Request):
    data = await request.json()
    transcript = data.get("transcript")
    if not isinstance(transcript, list):
        return {"error": "Invalid transcript"}

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = TRANSCRIPT_DIR / f"transcript_{timestamp}.json"
    with open(file_path, "w") as f:
        json.dump(transcript, f, indent=2)
    return {"status": "saved"}


@app.post("/translate-transcript")
async def translate_transcript(request: Request):
    data = await request.json()
    transcript = data.get("transcript", [])
    if not isinstance(transcript, list):
        return {"error": "Invalid transcript"}

    processed = []
    for pair in transcript:
        question = pair.get("question", "")
        answer = pair.get("answer", "")

        try:
            if question and detect(question) != "en":
                question = translator.translate(question, dest="en").text
        except Exception:
            pass

        try:
            if answer and detect(answer) != "en":
                answer = translator.translate(answer, dest="en").text
        except Exception:
            pass

        processed.append({"question": question, "answer": answer})

    return {"transcript": processed}