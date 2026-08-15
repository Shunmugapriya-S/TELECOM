import soundfile as sf
import noisereduce as nr
import numpy as np

def clean_audio(input_path, output_path="audio_input/clean.wav"):
    """
    Reduces background noise from the recorded audio
    before sending it to Whisper for transcription.
    """
    audio, sr = sf.read(input_path)

    # If stereo, convert to mono
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)

    reduced_audio = nr.reduce_noise(y=audio, sr=sr)
    sf.write(output_path, reduced_audio, sr)
    return output_path