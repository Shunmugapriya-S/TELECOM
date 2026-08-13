# RAG Engine — Local Gemma/LoRA utilities

This folder contains utilities to load a local base model (e.g., Gemma) and apply a LoRA/PEFT adapter, plus a unified test runner.

Quick steps

1. Install dependencies (use a GPU-enabled Python environment for best performance):

```bash
pip install -r requirements.txt
```

2. Login to Hugging Face if using gated models:

```bash
huggingface-cli login
# or set HF_TOKEN env var
```

3. Run unified tester (example):

```bash
python -m rag_engine.ai_agents.LLM_TESTING --adapter_dir C:\path\to\adapter --base_model google/gemma-7b --prompt "Describe how to resolve a billing issue" --device cpu
```

Notes

- If `google/gemma-7b` is gated, ensure your HF account has access and `HF_TOKEN` is set or you are logged in with `huggingface-cli`.
- You can pass a zip file containing a LoRA adapter using `--zip path/to/adapter.zip`.
- Uploading adapters to Hugging Face Hub is optional; adapters are small and easy to share privately.
