# OTUS-GPT ДЗ: Fine-tuning GPT-like модели

## Что сделано
1. Выбрана открытая GPT-like модель на HuggingFace (по умолчанию: `Qwen/Qwen2.5-1.5B-Instruct`).
2. Реализован **instruction fine-tuning** с **QLoRA** (4-bit) через `transformers + peft + bitsandbytes`.
3. Реализован CLI-бот/агент с цепочкой:
   - `Router` определяет тип запроса (FAQ/свободный).
   - `Answer` генерирует ответ (base или base+LoRA).
4. Добавлены примерные данные (JSONL) и скрипт индексации документов.



## Быстрый старт
```bash
pip install -r requirements.txt
python scripts/train_qlora.py --model_name Qwen/Qwen2.5-1.5B-Instruct --train_path data/sample_train.jsonl --val_path data/sample_val.jsonl --output_dir artifacts/lora_qwen_1p5b
python scripts/build_index.py --docs_dir docs --index_dir artifacts/rag_index
python scripts/rag_agent.py --model_name Qwen/Qwen2.5-1.5B-Instruct --lora_path artifacts/lora_qwen_1p5b --index_dir artifacts/rag_index
```

## Структура
См. код в `scripts/`.
