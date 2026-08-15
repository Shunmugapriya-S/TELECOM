from faster_whisper import WhisperModel

# Model ONE TIME load aagும் (module-level) — script edhுவும் repeat pannினாலும் re-download aagாthu
model = WhisperModel("base", device="cpu", compute_type="int8")


def _run_transcribe(filepath, task="transcribe", language=None):
    """
    Core transcribe function with fixes for the 'empty transcript' bug:
    - vad_filter=True  -> removes silence/noise gaps that were causing blank output
    - condition_on_previous_text=False -> avoids Whisper repeating/hallucinating text

    Also materializes the segment generator (instead of just concatenating
    text) so we can inspect each segment's confidence signals:
    - avg_logprob:    how confident Whisper was about the words it chose
                       (close to 0 = confident, very negative e.g. < -1 = guessing)
    - no_speech_prob: how likely this segment was actually silence/noise
                       rather than speech (close to 1 = probably not speech)
    """
    segments_gen, info = model.transcribe(
        filepath,
        beam_size=5,
        task=task,
        language=language,           # None = auto-detect
        vad_filter=True,             # <-- fixes missing transcript issue
        vad_parameters=dict(min_silence_duration_ms=500),
        condition_on_previous_text=False,
    )

    segments = list(segments_gen)  # generator only yields once — consume it here
    full_text = "".join(segment.text for segment in segments).strip()

    if segments:
        avg_logprob = sum(s.avg_logprob for s in segments) / len(segments)
        no_speech_prob = sum(s.no_speech_prob for s in segments) / len(segments)
    else:
        # No segments at all usually means VAD found no speech in the clip
        avg_logprob = -999.0
        no_speech_prob = 1.0

    confidence_stats = {
        "avg_logprob": round(avg_logprob, 3),
        "no_speech_prob": round(no_speech_prob, 3),
        "segment_count": len(segments),
    }

    return full_text, info, confidence_stats


# Tunable thresholds — loosen/tighten these based on real testing, not theory.
# Whisper's own CLI uses avg_logprob < -1.0 and no_speech_prob > 0.6 as its
# default "this segment is probably junk" heuristic; we start from the same.
LOW_CONFIDENCE_AVG_LOGPROB = -1.0
HIGH_NO_SPEECH_PROB = 0.6
LOW_LANGUAGE_PROBABILITY = 0.3


def assess_confidence(text, confidence_stats, language_probability):
    """
    Decides whether a transcript is trustworthy enough to send further down
    the pipeline (grammar correction, translation) or whether we should ask
    the user to re-record instead of silently returning garbage.

    Returns (is_reliable: bool, reason: str | None)
    """
    if not text.strip() or confidence_stats["segment_count"] == 0:
        return False, "no_speech_detected"

    if confidence_stats["no_speech_prob"] > HIGH_NO_SPEECH_PROB:
        return False, "likely_silence_or_noise"

    if confidence_stats["avg_logprob"] < LOW_CONFIDENCE_AVG_LOGPROB:
        return False, "low_confidence_transcription"

    if language_probability < LOW_LANGUAGE_PROBABILITY:
        return False, "uncertain_language"

    return True, None


def transcribe_speech(filepath, language_mode="auto"):
    """
    language_mode: 'auto' | 'ta' | 'en' | 'tanglish'

    Returns transcript in the SAME language spoken (no translation), plus
    an is_reliable flag so the caller can stop the pipeline early instead
    of running correction/translation on a garbage transcript.
    """
    lang = None if language_mode in ("auto", "tanglish") else language_mode
    text, info, confidence_stats = _run_transcribe(
        filepath, task="transcribe", language=lang
    )
    is_reliable, reason = assess_confidence(
        text, confidence_stats, info.language_probability
    )

    return {
        "text": text,
        "detected_language": info.language,
        "confidence": round(info.language_probability, 2),
        "is_reliable": is_reliable,
        "reason": reason,
        "confidence_stats": confidence_stats,
    }


def transcribe_to_english(filepath):
    """
    Whatever language spoken (Tamil/Tanglish/English) -> English output
    """
    text, info, _ = _run_transcribe(filepath, task="translate")
    return {
        "original_language": info.language,
        "english_text": text
    }