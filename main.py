from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.recorder import record_audio
from app.stt_engine import transcribe_speech, transcribe_to_english
from app.noise_reduction import clean_audio
from app.text_correction import understand_transcript
from app.tts_engine import speak_text
from app.sentiment_emotion.model import predict_sentiment_emotion
from app.categorization.model import predict_category
from app.priority.model import predict_priority

app = FastAPI()
# Whisper model already loaded once above (via stt_engine import) — stays in memory
# Sentiment/emotion, categorization, and priority models load once on import too

# Allow the Vite dev server (and any other local frontend) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated TTS audio files (e.g. audio_input/response.mp3) so the
# frontend can play them back directly via <audio src="...">
import os
os.makedirs("audio_input", exist_ok=True)
app.mount("/audio", StaticFiles(directory="audio_input"), name="audio")


# Messages for when Whisper couldn't hear the audio clearly enough to even
# produce a trustworthy transcript (acoustic-level problem).
STT_RETRY_MESSAGES = {
    "no_speech_detected": "I didn't catch any speech in that recording. Please try again.",
    "likely_silence_or_noise": "That sounded like silence or background noise rather than speech. Please try again in a quieter spot.",
    "low_confidence_transcription": "I couldn't hear that clearly enough to be sure what was said. Could you repeat that a bit slower or closer to the mic?",
    "uncertain_language": "I couldn't confidently tell what language was spoken. Please try again.",
}

# Message for when Whisper heard something fine, but the *meaning* couldn't
# be confidently worked out (semantic-level problem — garbled, fragmentary,
# or contradictory sentence).
UNDERSTANDING_RETRY_MESSAGE = (
    "I heard you, but I couldn't quite understand what you meant. "
    "Could you say that again in a clearer way?"
)


def _retry_response(reason, message, raw_transcript="", extra=None):
    """Speaks the retry message back (voice response) in addition to
    returning it as text, and packages a consistent 'retry' payload."""
    audio_url = None
    try:
        speak_text(message, language="english")
        audio_url = "/audio/response.mp3"
    except Exception:
        # Don't let a TTS hiccup block the retry flow itself — the frontend
        # still gets the text message even if voice playback fails.
        audio_url = None

    payload = {
        "status": "retry",
        "reason": reason,
        "message": message,
        "raw_transcript": raw_transcript,
        "audio_url": audio_url,
    }
    if extra:
        payload.update(extra)
    return payload


@app.post("/speech-to-text")
def speech_to_text(language_mode: str = Form("auto"), duration: int = Form(6)):
    raw_path = record_audio(duration=duration)
    clean_path = clean_audio(raw_path)

    # ---- Stage 1: did Whisper hear speech clearly at all? ----
    result = transcribe_speech(clean_path, language_mode=language_mode)

    if not result["is_reliable"]:
        return _retry_response(
            reason=result["reason"],
            message=STT_RETRY_MESSAGES.get(
                result["reason"], "I couldn't hear that clearly. Please try again."
            ),
            raw_transcript=result["text"],
            extra={"confidence_stats": result["confidence_stats"]},
        )

    # ---- Stage 2: given a clear transcript, can we work out what they meant? ----
    understanding = understand_transcript(
        result["text"], language_hint=result["detected_language"]
    )

    if not understanding["understood"]:
        return _retry_response(
            reason="meaning_unclear",
            message=UNDERSTANDING_RETRY_MESSAGE,
            raw_transcript=result["text"],
        )

    translated = transcribe_to_english(clean_path)

    # ---- Stage 3: sentiment/emotion + categorization (run on the English text) ----
    emotion_result = predict_sentiment_emotion(translated["english_text"])
    category_result = predict_category(translated["english_text"])

    # ---- Stage 4: priority lookup, using outputs from both models above ----
    priority_result = predict_priority(
        sentiment=emotion_result["sentiment"],
        emotion=emotion_result["emotion"],
        category=category_result["category"],
        sub_category=category_result["sub_category"],
    )

    return {
        "status": "ok",
        "detected_language": result["detected_language"],
        "raw_transcript": result["text"],
        "corrected_transcript": understanding["text"],
        "english_translation": translated["english_text"],
        "confidence": result["confidence"],
        "confidence_stats": result["confidence_stats"],
        "sentiment": emotion_result["sentiment"],
        "sentiment_confidence": emotion_result["sentiment_confidence"],
        "emotion": emotion_result["emotion"],
        "emotion_confidence": emotion_result["emotion_confidence"],
        "category": category_result["category"],
        "sub_category": category_result["sub_category"],
        "priority": priority_result["priority"],
        "priority_score": priority_result["score"],
        "priority_rank": priority_result["priority_rank"],
    }


@app.post("/text-to-speech")
def text_to_speech(text: str = Form(...), language: str = Form("english")):
    speak_text(text, language=language)
    return {"status": "spoken", "text": text, "audio_url": "/audio/response.mp3"}