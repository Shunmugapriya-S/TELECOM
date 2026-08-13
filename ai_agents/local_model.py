import os
import zipfile
import glob
import argparse
import logging
from typing import Optional


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def unzip_lora(zip_path: str, dest_dir: str) -> str:
    """Extracts a LoRA zip archive to `dest_dir` and returns the adapter directory path.

    If the archive contains a single top-level folder, that folder path is returned.
    Otherwise `dest_dir` is returned.
    """
    os.makedirs(dest_dir, exist_ok=True)
    logger.info("Unzipping %s -> %s", zip_path, dest_dir)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest_dir)

    # If there's a single directory extracted, return it
    entries = [p for p in glob.glob(os.path.join(dest_dir, "*"))]
    if len(entries) == 1 and os.path.isdir(entries[0]):
        return entries[0]
    return dest_dir


def find_adapter_dir(path: str) -> Optional[str]:
    """Try to locate a directory that looks like a LoRA/adapter folder under `path`.

    Heuristics: presence of `adapter_config.json`, files named like `pytorch_model.bin`,
    `adapter_model.bin`, or files with `.pt`/`.bin` that include 'adapter' in name.
    """
    candidates = []
    for root, dirs, files in os.walk(path):
        filenames = set(files)
        if "adapter_config.json" in filenames:
            return root
        for f in filenames:
            if ("adapter" in f.lower() or f.lower().endswith((".pt", ".bin"))) and (
                "pytorch_model" in f.lower() or "adapter" in f.lower() or f.lower().endswith((".pt", ".bin"))
            ):
                candidates.append(root)
    return candidates[0] if candidates else None


def load_local_model(base_model: str, adapter_dir: Optional[str] = None, device: str = "cpu", local_only: bool = True):
    """Attempt to load a fine-tuned model (PEFT) or a base model with optional adapter.

    If base_model points to a PEFT adapter folder (has adapter_config.json), load it directly.
    Otherwise, load base model and apply adapter_dir if provided.
    
    Returns (model, tokenizer). Raises informative errors if required packages are missing.
    """
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
    except Exception as e:
        raise RuntimeError("Missing transformers/torch. Install 'transformers' and 'torch' to load models.") from e

    # detect accelerate availability for device_map support
    try:
        import accelerate  # noqa: F401
        accelerate_available = True
    except Exception:
        accelerate_available = False

    # Check if base_model is actually a PEFT adapter folder
    is_peft_model = os.path.isdir(base_model) and os.path.isfile(os.path.join(base_model, "adapter_config.json"))
    
    if is_peft_model:
        logger.info("Detected PEFT model at %s, loading fine-tuned model directly", base_model)
        try:
            from peft import PeftModel, AutoPeftModelForCausalLM
        except Exception as e:
            raise RuntimeError("Missing peft. Install 'peft' to load PEFT models.") from e
        
        # Load tokenizer from the PEFT folder (with fallback to online if local_files_only fails)
        try:
            tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True, local_files_only=local_only)
        except Exception:
            try:
                tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True, local_files_only=False)
            except Exception as e:
                raise RuntimeError(f"Failed to load tokenizer from fine-tuned model '{base_model}': {e}") from e
        
        # Load the PEFT model directly
        try:
            model_kwargs = {}
            if device != "cpu" and accelerate_available:
                model_kwargs["device_map"] = "auto"
            
            try:
                model = AutoPeftModelForCausalLM.from_pretrained(base_model, **model_kwargs)
            except Exception:
                try:
                    model = AutoModelForCausalLM.from_pretrained(base_model, local_files_only=False, **model_kwargs)
                except Exception:
                    # Attempt loading using base model in adapter_config.json
                    import json
                    config_path = os.path.join(base_model, "adapter_config.json")
                    if os.path.exists(config_path):
                        with open(config_path, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                        base_model_name = cfg.get("base_model_name_or_path")
                        if base_model_name:
                            base_model_obj = AutoModelForCausalLM.from_pretrained(base_model_name, **model_kwargs)
                            model = PeftModel.from_pretrained(base_model_obj, base_model, **model_kwargs)
                        else:
                            raise
                    else:
                        raise
        except Exception as e:
            raise RuntimeError(f"Failed to load fine-tuned model from '{base_model}': {e}") from e
    else:
        # Original flow: load base model + optional adapter
        logger.info("Loading base model from %s", base_model)
        
        # Support gated HF repos via HF_TOKEN or HUGGINGFACE_HUB_TOKEN env var
        hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
        token_kwargs = {"use_auth_token": hf_token} if hf_token else {}
        if local_only:
            token_kwargs["local_files_only"] = True

        try:
            tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True, **(token_kwargs or {}))
        except Exception as e:
            msg = str(e)
            if "gated" in msg.lower() or "401" in msg or "Unauthorized" in msg:
                raise RuntimeError(
                    f"Failed to load tokenizer for base model '{base_model}': Access to this model is gated. "
                    "Ensure you have access on Hugging Face and set HF_TOKEN or run `huggingface-cli login`."
                ) from e
            raise RuntimeError(f"Failed to load tokenizer for base model '{base_model}': {e}") from e

        try:
            map_kwargs = {"device_map": "auto"} if (device != "cpu" and accelerate_available) else {}
            if device != "cpu" and torch.cuda.is_available():
                dtype_kw = {"dtype": torch.float16}
            else:
                dtype_kw = {"dtype": torch.float32}

            model = AutoModelForCausalLM.from_pretrained(
                base_model,
                low_cpu_mem_usage=True,
                local_files_only=local_only,
                **(map_kwargs or {}),
                **(token_kwargs or {}),
                **(dtype_kw or {}),
            )
        except Exception as e:
            msg = str(e)
            if "gated" in msg.lower() or "401" in msg or "Unauthorized" in msg:
                raise RuntimeError(
                    f"Failed to load base model '{base_model}': Access to this model is gated. "
                    "Ensure you have access on Hugging Face and set HF_TOKEN or run `huggingface-cli login`."
                ) from e
            raise RuntimeError(f"Failed to load base model '{base_model}': {e}") from e

        # Apply adapter if provided
        if adapter_dir:
            try:
                from peft import PeftModel

                logger.info("Applying LoRA adapter from %s", adapter_dir)
                peft_kwargs = {}
                if device != "cpu" and accelerate_available:
                    peft_kwargs["device_map"] = "auto"
                model = PeftModel.from_pretrained(model, adapter_dir, **peft_kwargs)
            except Exception as e:
                logger.warning("PEFT adapter load failed: %s. Continuing with base model.", e)

    model.eval()
    return model, tokenizer


def generate_text(model, tokenizer, prompt: str, max_new_tokens: int = 256, temperature: float = 0.2) -> str:
    """Generate text from local model. Returns ONLY the newly generated response (prompt stripped out)."""
    try:
        import torch
    except Exception:
        raise RuntimeError("Torch is required to run generation. Install torch.")

    inputs = tokenizer(prompt, return_tensors="pt")
    input_ids = inputs["input_ids"]
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    gen = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=temperature,
        pad_token_id=tokenizer.eos_token_id,
    )

    # Strip input tokens so only the NEW generated portion is returned
    input_len = input_ids.shape[-1]
    new_tokens = gen[0][input_len:]
    generated_text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    if not generated_text:
        # Fallback: return full decode if stripping produced empty string
        generated_text = tokenizer.decode(gen[0], skip_special_tokens=True).strip()

    return generated_text


def _cli():
    ap = argparse.ArgumentParser(description="Load a local Gemma base model and apply a LoRA adapter zip to generate text.")
    ap.add_argument("--zip", help="Path to LoRA zip archive to extract (optional)")
    ap.add_argument("--adapter_dir", help="Path to adapter folder (optional)")
    ap.add_argument("--base_model", default="google/gemma-7b", help="Base model name or path")
    ap.add_argument("--prompt", default="Hello", help="Prompt to generate from")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="Device to run on")
    ap.add_argument("--max_new_tokens", type=int, default=256)
    ap.add_argument("--temperature", type=float, default=0.2)
    args = ap.parse_args()

    adapter_path = None
    if args.zip:
        extracted = unzip_lora(args.zip, os.path.join("models", os.path.splitext(os.path.basename(args.zip))[0]))
        adapter_path = find_adapter_dir(extracted)
        logger.info("Adapter located: %s", adapter_path)

    if args.adapter_dir:
        adapter_path = args.adapter_dir

    try:
        model, tokenizer = load_local_model(args.base_model, adapter_path, device=args.device)
    except Exception as e:
        logger.error("Model load error: %s", e)
        logger.info("Falling back to remote GEMMA inference (if available). See GEMMA.PY for remote usage.")
        raise

    out = generate_text(model, tokenizer, args.prompt, max_new_tokens=args.max_new_tokens, temperature=args.temperature)
    print("\n=== GENERATED ===\n")
    print(out)


if __name__ == "__main__":
    _cli()
