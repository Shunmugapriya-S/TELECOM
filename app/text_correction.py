import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

UNCLEAR_TOKEN = "UNCLEAR_INPUT"


def understand_transcript(text, language_hint="english"):
    """
    Takes a raw speech-to-text transcript — which may contain filler words
    ("um", "uh"), false starts, repeated words, informal grammar, or minor
    speech-recognition mistakes — and reconstructs what the user most
    likely intended to say, the way a human listener would fill in the
    gaps rather than transcribing every stumble literally.

    Returns:
        {
          "text": str,          # cleaned-up, intent-preserving text
          "understood": bool,   # False if the model couldn't confidently
                                 # work out the intended meaning
        }
    """
    if not text.strip():
        return {"text": text, "understood": False}

    prompt = f"""You are listening to a real person speak out loud, and what you have
below is a raw speech-to-text transcript of what they said, in {language_hint}.
Speech is messy: people pause, restart sentences, repeat words, use filler
words like "um" or "like", drop words, or get individual words
mis-transcribed by the speech recognizer. Your job is to figure out what
the person actually meant to communicate — the way an attentive human
listener would — and rewrite it as ONE clean, natural sentence (or short
set of sentences) in {language_hint}, preserving their original meaning,
tone, and intent. Do not add facts, requests, or details that were not
implied by what they said. Do not answer or respond to them — only
reconstruct what they meant to say.

If the transcript is so unclear, contradictory, or fragmentary that you
cannot confidently work out ANY reasonable intended meaning, respond with
exactly this token and nothing else: {UNCLEAR_TOKEN}

Transcript: "{text}" """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=300,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    result = response.choices[0].message.content.strip()
    print(f"[DEBUG] Groq raw output: {result!r}")

    if result == UNCLEAR_TOKEN or UNCLEAR_TOKEN in result:
        return {"text": text, "understood": False}

    return {"text": result, "understood": True}


correct_transcript = understand_transcript