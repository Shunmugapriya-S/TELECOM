import os
import soundfile as sf
import noisereduce as nr
import numpy as np

def clean_audio(input_path, output_path=None):
    """
    Reduces background noise from recorded audio.
    Safely falls back to the original audio file if audio reading or
    noise reduction encounters an issue with M4A/OGG/Opus voice notes.
    """
    if not os.path.exists(input_path):
        return input_path

    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_clean.wav"

    # Ensure parent directory of output_path exists
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    try:
        try:
            import librosa
            audio, sr = librosa.load(input_path, sr=16000)
        except Exception:
            audio, sr = sf.read(input_path)

        # If stereo, convert to mono
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)

        reduced_audio = nr.reduce_noise(y=audio, sr=sr)
        sf.write(output_path, reduced_audio, sr)
        return output_path
    except Exception as e:
        print(f"[INFO] Skipping noise reduction for voice audio ({e}). Using raw audio file.")
        return input_path