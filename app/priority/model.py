"""
app/priority/model.py

Priority lookup based on sentiment + emotion + category + sub_category,
using a pre-built JSON dictionary (priority_dictionary.json).
Import predict_priority(...) from main.py.

Requires, in this same folder:
    priority_dictionary.json
"""

import json
import os

_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(_DIR, "priority_dictionary.json"), "r", encoding="utf-8") as f:
    _priority_map = json.load(f)


def predict_priority(sentiment: str, emotion: str, category: str, sub_category: str) -> dict:
    """
    Input: sentiment, emotion, category, sub_category (from the other two models).
    Output: urgency label, score, and priority_rank - or a safe fallback
    if this exact combination isn't in the dictionary.
    """
    key = f"{sentiment.strip()}|{emotion.strip()}|{category.strip()}|{sub_category.strip()}"

    if key in _priority_map:
        result = _priority_map[key]
        return {
            "priority": result["urgency"],
            "score": result["score"],
            "priority_rank": result["priority_rank"],
            "matched": True,
        }

    # Fallback for combinations not seen in the priority dictionary -
    # don't let a missing key break the pipeline.
    return {
        "priority": "Unknown",
        "score": None,
        "priority_rank": None,
        "matched": False,
    }