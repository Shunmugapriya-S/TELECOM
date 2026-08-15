"""
app/sentiment_emotion/model.py

Sentiment + emotion classification (DistilBERT multi-task).
Import predict_sentiment_emotion(text) from main.py.

Requires, in this same folder:
    phase6_distilbert_multitask.pt
    label_maps.json
"""

import json
import os
import torch
from torch import nn
import torch.nn.functional as F
from transformers import DistilBertTokenizerFast, DistilBertModel

MODEL_NAME = "distilbert-base-uncased"
MAX_LEN = 128
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(_DIR, "label_maps.json")) as f:
    _maps = json.load(f)
SENTIMENT_LABELS = _maps["sentiment_labels"]
EMOTION_LABELS = _maps["emotion_labels"]


class MultiTaskDistilBert(nn.Module):
    def __init__(self, n_sent, n_emo):
        super().__init__()
        self.encoder = DistilBertModel.from_pretrained(MODEL_NAME)
        hidden = self.encoder.config.hidden_size
        self.dropout = nn.Dropout(0.2)
        self.sentiment_head = nn.Linear(hidden, n_sent)
        self.emotion_head = nn.Linear(hidden, n_emo)

    def forward(self, input_ids, attention_mask):
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0, :]
        cls = self.dropout(cls)
        return self.sentiment_head(cls), self.emotion_head(cls)


_tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_NAME)
_model = MultiTaskDistilBert(len(SENTIMENT_LABELS), len(EMOTION_LABELS)).to(DEVICE)
_model.load_state_dict(torch.load(
    os.path.join(_DIR, "phase6_distilbert_multitask.pt"), map_location=DEVICE
))
_model.eval()


def predict_sentiment_emotion(text: str) -> dict:
    """
    Input: complaint text (English).
    Output: sentiment, emotion, and confidence scores for both.
    """
    enc = _tokenizer(text, truncation=True, padding="max_length",
                      max_length=MAX_LEN, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        sent_logits, emo_logits = _model(enc["input_ids"], enc["attention_mask"])
        sent_probs = F.softmax(sent_logits, dim=1).squeeze(0)
        emo_probs = F.softmax(emo_logits, dim=1).squeeze(0)

    sent_idx = sent_probs.argmax().item()
    emo_idx = emo_probs.argmax().item()

    return {
        "sentiment": SENTIMENT_LABELS[sent_idx],
        "sentiment_confidence": round(sent_probs[sent_idx].item(), 4),
        "emotion": EMOTION_LABELS[emo_idx],
        "emotion_confidence": round(emo_probs[emo_idx].item(), 4),
    }