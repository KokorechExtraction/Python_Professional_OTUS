import argparse

import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    Trainer,
    TrainingArguments,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
)


def format_example(tokenizer, ex: dict) -> str:

    instruction = (ex.get("instruction") or "").strip()
    inp = (ex.get("input") or "").strip()
    out = (ex.get("output") or "").strip()


    user = instruction + ("\n\n" + inp if inp else "")


    messages = [
        {"role": "user", "content": user},
        {"role": "assistant", "content": out},
    ]


    if hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
        except Exception:
            pass

    return (
        f"### Instruction:\n{instruction}\n\n"
        f"### Input:\n{inp}\n\n"
        f"### Response:\n{out}"
    )


def tokenize_batch(tokenizer, batch: dict, max_len: int) -> dict:

    texts = [
        format_example(tokenizer, {"instruction": i, "input": x, "output": o})
        for i, x, o in zip(batch["instruction"], batch["input"], batch["output"])
    ]

    return tokenizer(
        texts,
        max_length=max_len,
        truncation=True,
        padding=False,
    )


def main() -> None:


    ap = argparse.ArgumentParser(description="QLoRA fine-tuning for OTUS-GPT homework")


    ap.add_argument("--model_name", required=True, help="HF model id, e.g. Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--train_path", required=True, help="Path to train JSONL")
    ap.add_argument("--val_path", required=True, help="Path to validation JSONL")
    ap.add_argument("--output_dir", required=True, help="Where to save LoRA adapters and tokenizer")


    ap.add_argument("--max_seq_len", type=int, default=1024, help="Max tokens per sample after tokenization")
    ap.add_argument("--learning_rate", type=float, default=2e-4, help="Learning rate for LoRA training")
    ap.add_argument("--num_train_epochs", type=int, default=3, help="Number of epochs")
    ap.add_argument("--per_device_train_batch_size", type=int, default=1, help="Train batch size per device")
    ap.add_argument("--per_device_eval_batch_size", type=int, default=1, help="Eval batch size per device")
    ap.add_argument("--gradient_accumulation_steps", type=int, default=8, help="Accumulate gradients to simulate bigger batch")
    ap.add_argument("--warmup_ratio", type=float, default=0.03, help="Warmup ratio for LR scheduling")
    ap.add_argument("--logging_steps", type=int, default=10, help="How often to log metrics")
    ap.add_argument("--save_steps", type=int, default=200, help="How often to save checkpoints (steps)")
    ap.add_argument("--eval_steps", type=int, default=200, help="How often to run eval (steps)")


    ap.add_argument("--lora_r", type=int, default=16, help="LoRA rank (capacity of adapter)")
    ap.add_argument("--lora_alpha", type=int, default=32, help="LoRA alpha (scaling)")
    ap.add_argument("--lora_dropout", type=float, default=0.05, help="LoRA dropout (regularization)")

    args = ap.parse_args()


    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=(
            torch.bfloat16 if torch.cuda.is_available() else torch.float16
        ),
    )


    tok = AutoTokenizer.from_pretrained(args.model_name, use_fast=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token


    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        device_map="auto",
        quantization_config=bnb,
        torch_dtype=(torch.bfloat16 if torch.cuda.is_available() else torch.float16),
    )


    model = prepare_model_for_kbit_training(model)


    lora = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",

        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )


    model = get_peft_model(model, lora)


    model.print_trainable_parameters()


    ds_train = load_dataset("json", data_files=args.train_path, split="train")
    ds_val = load_dataset("json", data_files=args.val_path, split="train")


    ds_train = ds_train.map(
        lambda b: tokenize_batch(tok, b, args.max_seq_len),
        batched=True,
        remove_columns=ds_train.column_names,
    )
    ds_val = ds_val.map(
        lambda b: tokenize_batch(tok, b, args.max_seq_len),
        batched=True,
        remove_columns=ds_val.column_names,
    )


    collator = DataCollatorForLanguageModeling(
        tokenizer=tok,
        mlm=False,
    )


    targs = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_train_epochs,
        warmup_ratio=args.warmup_ratio,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps,
        evaluation_strategy="steps",
        save_strategy="steps",
        report_to="none",
        optim="paged_adamw_8bit",
    )


    trainer = Trainer(
        model=model,
        args=targs,
        train_dataset=ds_train,
        eval_dataset=ds_val,
        data_collator=collator,
    )

    trainer.train()


    model.save_pretrained(args.output_dir)
    tok.save_pretrained(args.output_dir)
    print(f"Saved LoRA adapter to: {args.output_dir}")


if __name__ == "__main__":

    main()
