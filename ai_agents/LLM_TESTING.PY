import sys
import torch
from pathlib import Path

# Setup rag_engine package namespace dynamically
from types import ModuleType
if "rag_engine" not in sys.modules:
    root_dir = Path(__file__).resolve().parent
    while root_dir.parent != root_dir and not (root_dir / "requirements.txt").exists():
        root_dir = root_dir.parent
    m = ModuleType("rag_engine")
    m.__path__ = [str(root_dir)]
    sys.modules["rag_engine"] = m

from rag_engine.ai_agents import local_model

BASE_MODEL = "unsloth/gemma-3-270m-it"
LORA_PATH = r"ai_agents\gemma_3_lora\content\gemma_3_lora"

print("Loading tokenizer and model (with optional LoRA adapter)...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model, tokenizer = local_model.load_local_model(BASE_MODEL, adapter_dir=LORA_PATH, device=device)
model.eval()
print("Model loaded.")


def generate_answer(question, context=""):
    prompt = f"""
You are a helpful telecom customer-support assistant.

IMPORTANT:
- Answer only using the provided context when context is available.
- Do not invent information.
- If the context does not contain enough information, clearly say that you don't have enough information.
- Understand English, Tamil and Tanglish.
- Reply in the same language/style used by the user.
- Give a concise and relevant solution.

CONTEXT:
{context}

USER QUESTION:
{question}

ANSWER:
"""

    full_prompt = prompt
    return local_model.generate_text(model, tokenizer, full_prompt, max_new_tokens=200, temperature=0.1)


if __name__ == "__main__":
    question = input("\nEnter your question: ")

    answer = generate_answer(question)

    print("\n--- LLM ANSWER ---")
    print(answer)