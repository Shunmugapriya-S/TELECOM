from gtts import gTTS
import pygame
import os

_lang_map = {
    "english": "en",
    "tamil": "ta",
    "tanglish": "ta"   # tanglish spoken -> closest is Tamil voice
}


def speak_text(text, language="english", save_path="audio_input/response.mp3", play_audio=False):
    """
    Generates speech audio from text and saves it to save_path.

    play_audio=False (default): just save the file. This is what the API
    endpoints use — the frontend plays the audio itself via a browser
    <audio> element, so playing it again here would be redundant AND
    causes a Windows-specific bug: pygame keeps a file handle open on the
    saved .mp3 after playback, so the NEXT request trying to overwrite the
    same response.mp3 fails with PermissionError: [Errno 13] Permission
    denied. Not playing server-side avoids that entirely.

    play_audio=True: also plays the audio out loud on THIS machine
    (blocking until playback finishes) — useful for standalone CLI/demo
    scripts run directly on your own computer, not for the API.
    """
    lang_code = _lang_map.get(language, "en")

    tts = gTTS(text=text, lang=lang_code)
    tts.save(save_path)
    print(f"✅ Audio saved: {save_path}")

    if not play_audio:
        return save_path

    pygame.mixer.init()
    pygame.mixer.music.load(save_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

    # Release the file handle so a future call can overwrite this same
    # path without hitting the Windows PermissionError described above.
    pygame.mixer.music.unload()

    return save_path