"""
TEST FULL MODEL CHAIN - bypasses audio/Whisper/Groq entirely.
Type a complaint, see sentiment, emotion, category, sub_category, and
priority all at once. This tests your three models directly, without
the microphone-timing issues of the voice pipeline.

Run from the backend/ folder:
    python test_full_chain.py
"""

from app.sentiment_emotion.model import predict_sentiment_emotion
from app.categorization.model import predict_category
from app.priority.model import predict_priority

print("=" * 70)
print("FULL MODEL CHAIN TEST (sentiment/emotion -> category -> priority)")
print("Type a complaint and press Enter. Type 'quit' to exit.")
print("=" * 70)

while True:
    text = input("\nComplaint: ").strip()
    if text.lower() == "quit":
        break
    if not text:
        continue

    emotion_result = predict_sentiment_emotion(text)
    category_result = predict_category(text)
    priority_result = predict_priority(
        sentiment=emotion_result["sentiment"],
        emotion=emotion_result["emotion"],
        category=category_result["category"],
        sub_category=category_result["sub_category"],
    )

    print("\n----- RESULT -----")
    print(f"  Sentiment     : {emotion_result['sentiment']} ({emotion_result['sentiment_confidence']})")
    print(f"  Emotion       : {emotion_result['emotion']} ({emotion_result['emotion_confidence']})")
    print(f"  Category      : {category_result['category']}")
    print(f"  Sub-category  : {category_result['sub_category']}")
    print(f"  Priority      : {priority_result['priority']}")
    print(f"  Priority rank : {priority_result['priority_rank']}")
    print(f"  Matched dict  : {priority_result['matched']}")
    print("-------------------")