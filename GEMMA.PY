import os
from huggingface_hub import InferenceClient

# Prefer the HF token from environment; keep file-based token off by default.
# To test locally you may set HF_TOKEN env var or uncomment the fallback below.
HF_TOKEN = os.environ.get("HF_TOKEN")
# HF_TOKEN = os.environ.get("HF_TOKEN")  # set via environment variable

def generate(prompt: str, model: str = "google/gemma-7b"):
    """Generate text using the Gemma model.

    Raises EnvironmentError if `HF_TOKEN` is not set.
    """
    if not HF_TOKEN:
        raise EnvironmentError("HF_TOKEN environment variable not set")

    client = InferenceClient(provider="featherless-ai", api_key=HF_TOKEN)
    return client.text_generation(prompt, model=model)


if __name__ == "__main__":
    prompt = "Can you please let us know more details about your "
    try:
        result = generate(prompt)
        print(result)
    except Exception as e:
        print("Error running generation:", e)