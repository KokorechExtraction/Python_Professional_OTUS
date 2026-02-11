import argparse
import torch

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)

from peft import PeftModel



SYSTEM = (
    "Ты полезный ассистент. Отвечай кратко и по делу. "
    "Если не уверен — скажи об этом."
)


def build_prompt(tok, user_text: str) -> str:
    """Build a chat prompt in the model's preferred format if possible."""


    msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_text},
    ]


    if hasattr(tok, "apply_chat_template"):
        try:
            return tok.apply_chat_template(
                msgs,
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:

            pass


    return f"System: {SYSTEM}\nUser: {user_text}\nAssistant:"


@torch.inference_mode()
def main() -> None:
    ap = argparse.ArgumentParser(description="Compare base vs base+LoRA")

    ap.add_argument("--model_name", required=True, help="HF model id")
    ap.add_argument("--lora_path", default=None, help="Path to LoRA adapter directory (optional)")
    ap.add_argument("--max_new_tokens", type=int, default=256, help="Max tokens to generate")

    args = ap.parse_args()


    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=(torch.bfloat16 if torch.cuda.is_available() else torch.float16),
    )


    tok = AutoTokenizer.from_pretrained(args.model_name, use_fast=True)


    if tok.pad_token is None:
        tok.pad_token = tok.eos_token


    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        device_map="auto",
        quantization_config=bnb,
    )


    if args.lora_path:
        model = PeftModel.from_pretrained(model, args.lora_path)

    model.eval()

    print("Введите вопрос (пустая строка — выход):")

    while True:
        q = input("> ").strip()
        if not q:
            break

        prompt = build_prompt(tok, q)


        inputs = tok(prompt, return_tensors="pt").to(model.device)


        outputs = model.generate(
            **inputs,
            max_new_tokens=args.max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tok.eos_token_id,
        )


        print(tok.decode(outputs[0], skip_special_tokens=True))
        print()


if __name__ == "__main__":
    main()
