import re
from typing import List

# Prompt-only layer: builds system/user prompts and formats context
# This file contains no orchestration (no retrieval or model calls)

TAMIL_UNICODE_RANGE = re.compile(r"[\u0B80-\u0BFF]")
COMMON_ROMANIZED_TAMIL = [
    "enna", "appa", "amma", "veetu", "naaan", "nan", "vaanga", "kanna", "romba", "yaen", "oru",
    "sari", "illai", "poittu", "thaan", "unga", "unga%", "kadavule"
]


def detect_language(query: str) -> str:
    """Detects language style: 'tamil', 'tanglish', or 'english'.

    Heuristics:
    - If contains Tamil Unicode characters => 'tamil'
    - Else if contains common romanized Tamil words => 'tanglish'
    - Else => 'english'
    """
    if not query:
        return "english"
    if TAMIL_UNICODE_RANGE.search(query):
        return "tamil"
    q_lower = query.lower()
    for token in COMMON_ROMANIZED_TAMIL:
        if token in q_lower:
            return "tanglish"
    return "english"


def build_system_prompt(language: str = "english") -> str:
    """Return a short system prompt instructing assistant behavior for the given language."""
    if language == "tamil":
        return (
            "நீங்கள் ஒரு தொலைத்தொடர் உதவி உதவியாளர். உங்கள் பதில்கள் தெளிவானவையாகவும், சரியானவையாகவும் இருக்க வேண்டும். "
            "கொடுக்கப்பட்ட உண்மைகளை மட்டுமே பயன்படுத்தி பதிலளிக்கவும்; குறைந்தபட்ச தகவல் இருந்தால், அதிக விவரங்களை கேளுங்கள்."
        )
    if language == "tanglish":
        return (
            "Neenga oru telecom support assistant. Answer panna sollunga concise ah, clear ah, mathiri. "
            "Context irrundha adhai dhaan use pannu; illa na, adhai solli user kitta kelvi ketka."
        )
    # default English
    return (
        "You are an expert telecom support assistant. Analyze the customer issue using ONLY the provided context. "
        "Structure your response in exactly these three sections:\n"
        "1. ROOT CAUSE ANALYSIS: Identify the underlying cause of the issue based on the context.\n"
        "2. RECOMMENDATIONS: Provide actionable recommendations and orchestration steps.\n"
        "3. SOLUTIONS: List concrete solutions to mitigate and resolve the issue.\n\n"
        "Be specific, factual, and grounded in the context. Do not invent information not present in the context."
    )


def build_user_prompt(user_query: str, language: str = "english") -> str:
    """Wrap the user query into a consistent user prompt block based on language."""
    if language == "tamil":
        return f"வாடிக்கையாளர் கேள்வி:\n{user_query}\n\nதயவுசெய்து குறிப்பு அளிக்கவும்."
    if language == "tanglish":
        return f"User Question:\n{user_query}\n\nPlease give a short action plan in Tanglish."
    return (
        f"User Question:\n{user_query}\n\n"
        "Respond with the following sections (use these exact headings):\n"
        "ROOT CAUSE ANALYSIS:\n"
        "RECOMMENDATIONS:\n"
        "SOLUTIONS:\n"
    )


def format_context_blocks(chunks: List[dict], max_blocks: int = 5) -> str:
    """Format retrieved chunks into a single context string for injection into prompts.

    Expected chunk dict format: {"text": str, "metadata": dict, "score": float}
    """
    if not chunks:
        return ""
    blocks = []
    for i, c in enumerate(chunks[:max_blocks], start=1):
        text = c.get("text") or c.get("page_content") or ""
        meta = c.get("metadata", {})
        score = c.get("score", 0.0)
        title = meta.get("title") or meta.get("complaint_id") or meta.get("id") or f"Block-{i}"
        block = (
            f"[Context Block {i} - {title} | Score: {score:.3f}]\n{text}\n"
        )
        blocks.append(block)
    return "\n".join(blocks)


def build_full_prompt(system_prompt: str, context: str, user_prompt: str) -> str:
    """Compose the full prompt to send to the LLM (no model calls here)."""
    parts = [f"SYSTEM:\n{system_prompt}", f"RETRIEVED_CONTEXT:\n{context}", f"USER:\n{user_prompt}"]
    return "\n\n".join(parts)
