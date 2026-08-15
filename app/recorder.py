import sounddevice as sd
import soundfile as sf
import os

def record_audio(filename="audio_input/complaint.wav", duration=6, samplerate=16000):
    os.makedirs("audio_input", exist_ok=True)
    print("🎙️ Recording... Please speak your complaint now.")
    audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1)
    sd.wait()
    sf.write(filename, audio, samplerate)
    print(f"✅ Recording saved: {filename}")
    return filename