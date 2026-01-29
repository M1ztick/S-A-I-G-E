#!/usr/bin/env python3
"""
train_local.py

Local fine-tuning script for SAIGE using TRL and LoRA/QLoRA.
Fine-tunes TinyLlama (or other models) on SAIGE's high-quality training data.

Requirements:
    pip install transformers torch datasets trl peft accelerate bitsandbytes

Usage:
    python train_local.py --data saige_training_data.csv --model TinyLlama/TinyLlama-1.1B-Chat-v1.0
    python train_local.py --data saige_training_data.csv --model mistralai/Mistral-7B-Instruct-v0.2 --use-4bit
"""

import argparse
import os
from pathlib import Path
import pandas as pd
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    BitsAndBytesConfig
)
from trl import SFTTrainer
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training


def load_training_data(csv_path: str) -> Dataset:
    """Load training data from CSV."""
    print(f"📖 Loading training data from {csv_path}")

    df = pd.read_csv(csv_path)
    print(f"   Found {len(df)} training examples")

    # Convert to HuggingFace Dataset
    dataset = Dataset.from_pandas(df[['text']])

    return dataset


def setup_model_and_tokenizer(
    model_name: str,
    use_4bit: bool = False,
    use_8bit: bool = False
):
    """Setup model and tokenizer with optional quantization."""
    print(f"🤖 Loading model: {model_name}")

    # Configure quantization if requested
    quantization_config = None
    if use_4bit:
        print("   Using 4-bit quantization (QLoRA)")
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    elif use_8bit:
        print("   Using 8-bit quantization")
        quantization_config = BitsAndBytesConfig(
            load_in_8bit=True,
        )

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=quantization_config,
        device_map="auto",
        trust_remote_code=True,
    )

    # Prepare model for k-bit training if using quantization
    if use_4bit or use_8bit:
        model = prepare_model_for_kbit_training(model)

    print(f"✅ Model loaded successfully")

    return model, tokenizer


def setup_lora_config(
    lora_rank: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05
) -> LoraConfig:
    """Setup LoRA configuration."""
    print(f"🔧 Configuring LoRA:")
    print(f"   Rank: {lora_rank}")
    print(f"   Alpha: {lora_alpha}")
    print(f"   Dropout: {lora_dropout}")

    lora_config = LoraConfig(
        r=lora_rank,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )

    return lora_config


def train_model(
    model,
    tokenizer,
    dataset: Dataset,
    lora_config: LoraConfig,
    output_dir: str,
    num_epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 2e-4,
    max_seq_length: int = 512,
):
    """Train the model using SFTTrainer."""
    print(f"\n🏋️ Starting training:")
    print(f"   Epochs: {num_epochs}")
    print(f"   Batch size: {batch_size}")
    print(f"   Learning rate: {learning_rate}")
    print(f"   Max sequence length: {max_seq_length}")
    print(f"   Output directory: {output_dir}")
    print()

    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=learning_rate,
        fp16=torch.cuda.is_available(),
        logging_steps=10,
        save_strategy="epoch",
        optim="paged_adamw_8bit" if torch.cuda.is_available() else "adamw_torch",
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        report_to=["tensorboard"],
    )

    # Initialize trainer
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        peft_config=lora_config,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        args=training_args,
    )

    # Train
    print("🚀 Training started...")
    trainer.train()
    print("✅ Training complete!")

    # Save the model
    print(f"\n💾 Saving model to {output_dir}")
    trainer.save_model()
    tokenizer.save_pretrained(output_dir)
    print("✅ Model saved successfully")

    return trainer


def main():
    parser = argparse.ArgumentParser(
        description='Fine-tune a language model on SAIGE training data'
    )

    # Data arguments
    parser.add_argument(
        '--data',
        required=True,
        help='Path to training data CSV file'
    )

    # Model arguments
    parser.add_argument(
        '--model',
        default='TinyLlama/TinyLlama-1.1B-Chat-v1.0',
        help='Model name or path (default: TinyLlama-1.1B-Chat)'
    )
    parser.add_argument(
        '--use-4bit',
        action='store_true',
        help='Use 4-bit quantization (QLoRA)'
    )
    parser.add_argument(
        '--use-8bit',
        action='store_true',
        help='Use 8-bit quantization'
    )

    # LoRA arguments
    parser.add_argument(
        '--lora-rank',
        type=int,
        default=16,
        help='LoRA rank (default: 16)'
    )
    parser.add_argument(
        '--lora-alpha',
        type=int,
        default=32,
        help='LoRA alpha (default: 32)'
    )
    parser.add_argument(
        '--lora-dropout',
        type=float,
        default=0.05,
        help='LoRA dropout (default: 0.05)'
    )

    # Training arguments
    parser.add_argument(
        '--epochs',
        type=int,
        default=3,
        help='Number of training epochs (default: 3)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=4,
        help='Batch size per device (default: 4)'
    )
    parser.add_argument(
        '--learning-rate',
        type=float,
        default=2e-4,
        help='Learning rate (default: 2e-4)'
    )
    parser.add_argument(
        '--max-seq-length',
        type=int,
        default=512,
        help='Maximum sequence length (default: 512)'
    )
    parser.add_argument(
        '--output-dir',
        default='./saige-finetuned',
        help='Output directory (default: ./saige-finetuned)'
    )

    args = parser.parse_args()

    print("🧘 SAIGE Local Fine-Tuning")
    print("=" * 60)
    print()

    # Check CUDA availability
    if torch.cuda.is_available():
        print(f"✅ GPU available: {torch.cuda.get_device_name(0)}")
        print(f"   CUDA version: {torch.version.cuda}")
        print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        print("⚠️  No GPU detected - training will be slow on CPU")
        print("   Consider using Google Colab or a GPU instance")
    print()

    # Load data
    dataset = load_training_data(args.data)

    # Setup model and tokenizer
    model, tokenizer = setup_model_and_tokenizer(
        args.model,
        use_4bit=args.use_4bit,
        use_8bit=args.use_8bit
    )

    # Setup LoRA
    lora_config = setup_lora_config(
        lora_rank=args.lora_rank,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout
    )

    # Train
    trainer = train_model(
        model=model,
        tokenizer=tokenizer,
        dataset=dataset,
        lora_config=lora_config,
        output_dir=args.output_dir,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        max_seq_length=args.max_seq_length,
    )

    print("\n" + "=" * 60)
    print("🎉 Fine-tuning complete!")
    print()
    print(f"Model saved to: {args.output_dir}")
    print()
    print("Next steps:")
    print("  1. Test the model:")
    print(f"     python test_model.py --model {args.output_dir}")
    print()
    print("  2. Deploy to SAIGE worker:")
    print("     - Copy model files to worker/models/")
    print("     - Update worker.ts to use the new model")
    print()
    print("  3. Evaluate with Buddhist principles:")
    print("     python evaluate_buddhist.py --model {args.output_dir}")
    print("=" * 60)


if __name__ == '__main__':
    main()
