# SAIGE Local Trainer - RL-to-SFT Training Pipeline

Complete training pipeline for converting SAIGE's experiential learning data into fine-tuned language models.

## Overview

This pipeline automates the process of:
1. **Collecting experiences** via interaction with SAIGE worker
2. **Filtering high-quality responses** (low harm + high Buddhist alignment)
3. **Converting to SFT format** (TinyLlama, Mistral, or Llama3)
4. **Fine-tuning models** locally or in the cloud

---

## Quick Start

### Prerequisites

```bash
# Python 3.8+
python3 --version

# Install dependencies
pip install -r requirements.txt

# For local fine-tuning, you'll need:
# - CUDA-capable GPU (8GB+ VRAM recommended)
# - Or use Google Colab for cloud training
```

### Basic Usage

```bash
# Full pipeline: collect → convert → prepare
./train_pipeline.sh

# Or run steps individually:

# Step 1: Collect experiences (optional if you already have data)
node trainer.js 100

# Step 2: Convert to SFT format
python saige_to_sft.py --db ../saige.db --output training_data.csv

# Step 3: Fine-tune (if you have GPU)
python train_local.py --data training_data.csv
```

---

## Scripts

### 1. `saige_to_sft.py` - Experience → Training Data Converter

Queries SAIGE database for high-quality experiences and converts them to SFT format.

**Usage:**
```bash
python saige_to_sft.py \
    --db ../saige.db \
    --output saige_training_data.csv \
    --format mistral \
    --max-harm 0.25 \
    --min-buddhist 6.5 \
    --min-alignment good \
    --limit 1000
```

**Parameters:**
- `--db`: Path to SAIGE database (default: `../saige.db`)
- `--output`: Output CSV file (default: `saige_training_data.csv`)
- `--format`: Training format - `tinyllama`, `mistral`, or `llama3` (default: `mistral`)
- `--max-harm`: Maximum harm score to include, 0-1 (default: `0.3`)
- `--min-buddhist`: Minimum Buddhist weighted score, 0-10 (default: `6.0`)
- `--min-alignment`: Minimum alignment level - `moderate`, `good`, `excellent` (default: `good`)
- `--limit`: Maximum number of examples (default: unlimited)

**Output:**
CSV file with columns:
- `text`: Formatted training example
- `harm_score`: Harm score (0-1, lower is better)
- `buddhist_alignment`: Alignment level (low/moderate/good/excellent)
- `weighted_score`: Buddhist weighted score (0-10)
- `difficulty`: Scenario difficulty level (1-5)
- `scenario_id`: Original scenario ID
- `experience_id`: Experience record ID

**Example output:**
```
Found 247 high-quality experiences
✅ Wrote 247 training examples to saige_training_data.csv

📊 Training Data Statistics:
   Total Examples: 247
   Harm Score: avg=0.125, min=0.000, max=0.248
   Buddhist Score: avg=7.42, min=6.51, max=9.23
   Alignment Distribution:
     - excellent: 89 (36.0%)
     - good: 158 (64.0%)
   Difficulty Distribution:
     - Level 1: 62 (25.1%)
     - Level 2: 98 (39.7%)
     - Level 3: 87 (35.2%)
```

---

### 2. `train_local.py` - Local Fine-Tuning with LoRA/QLoRA

Fine-tunes TinyLlama, Mistral, or other models using the training data.

**Usage:**
```bash
# TinyLlama (1.1B) - good for testing, runs on smaller GPUs
python train_local.py \
    --data saige_training_data.csv \
    --model TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
    --epochs 3 \
    --batch-size 4 \
    --lora-rank 16

# Mistral (7B) with 4-bit quantization - better quality, needs 16GB+ VRAM
python train_local.py \
    --data saige_training_data.csv \
    --model mistralai/Mistral-7B-Instruct-v0.2 \
    --use-4bit \
    --epochs 3 \
    --batch-size 2 \
    --lora-rank 32
```

**Parameters:**
- `--data`: Training data CSV file (required)
- `--model`: Model name or path (default: `TinyLlama/TinyLlama-1.1B-Chat-v1.0`)
- `--use-4bit`: Use 4-bit quantization (QLoRA) for memory efficiency
- `--use-8bit`: Use 8-bit quantization
- `--lora-rank`: LoRA rank (default: 16, higher = more capacity but slower)
- `--lora-alpha`: LoRA alpha (default: 32)
- `--epochs`: Number of training epochs (default: 3)
- `--batch-size`: Batch size per device (default: 4)
- `--learning-rate`: Learning rate (default: 2e-4)
- `--output-dir`: Output directory (default: `./saige-finetuned`)

**Memory Requirements:**
- TinyLlama (1.1B): ~8GB VRAM
- TinyLlama (1.1B) + 4-bit: ~4GB VRAM
- Mistral (7B): ~28GB VRAM
- Mistral (7B) + 4-bit: ~8GB VRAM

**Output:**
Creates a directory with:
- `adapter_model.safetensors` - LoRA adapter weights
- `adapter_config.json` - LoRA configuration
- `tokenizer_config.json`, `tokenizer.json` - Tokenizer files
- `training_args.bin` - Training arguments

---

### 3. `train_pipeline.sh` - Complete Training Pipeline

Orchestrates the entire workflow: experience collection → conversion → preparation.

**Usage:**
```bash
# Default settings
./train_pipeline.sh

# Custom settings
TRAINING_EPISODES=100 \
MAX_HARM=0.2 \
MIN_BUDDHIST=7.0 \
MIN_ALIGNMENT=excellent \
./train_pipeline.sh
```

**Environment Variables:**
- `DB_PATH`: Database path (default: `../saige.db`)
- `WORKER_URL`: SAIGE worker URL (default: `http://localhost:8787`)
- `TRAINING_EPISODES`: Number of episodes to collect (default: `50`)
- `MAX_HARM`: Maximum harm threshold (default: `0.25`)
- `MIN_BUDDHIST`: Minimum Buddhist score (default: `6.5`)
- `MIN_ALIGNMENT`: Minimum alignment level (default: `good`)
- `FORMAT`: Output format (default: `mistral`)

---

## Training Formats

### TinyLlama / ChatML Format
```
<|system|>
You are a helpful AI assistant...</s>
<|user|>
Question</s>
<|assistant|>
Answer</s>
```

### Mistral Format
```
<s>[INST] Question [/INST] Answer</s>
```

### Llama 3 Format
```
<|begin_of_text|><|start_header_id|>system<|end_header_id|>
System prompt<|eot_id|>
<|start_header_id|>user<|end_header_id|>
User message<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>
Assistant response<|eot_id|>
```

---

## Training Workflows

### Workflow A: Local Training (GPU Available)

```bash
# 1. Collect and convert data
./train_pipeline.sh

# 2. Fine-tune locally
python train_local.py --data saige_training_data.csv --use-4bit

# 3. Test the model
python test_model.py --model ./saige-finetuned

# 4. Deploy to SAIGE worker
# (Copy model files and update worker configuration)
```

### Workflow B: Cloud Training (Google Colab)

```bash
# 1. Generate training data
python saige_to_sft.py --db ../saige.db

# 2. Upload saige_training_data.csv to Google Colab

# 3. In Colab, run:
```
```python
from google.colab import files
files.upload()  # Upload saige_training_data.csv

# Install dependencies
!pip install transformers trl peft accelerate

# Run training
!python train_local.py --data saige_training_data.csv --use-4bit
```
```bash
# 4. Download trained model from Colab
# 5. Deploy to SAIGE
```

### Workflow C: Cloudflare Workers AI + LoRA

```bash
# 1. Generate training data
python saige_to_sft.py --db ../saige.db --format mistral

# 2. Train LoRA adapter (use Colab or HuggingFace AutoTrain)

# 3. Deploy to Cloudflare Workers AI
cd ../worker
wrangler ai finetune create \
    @cf/mistral/mistral-7b-instruct-v0.2-lora \
    saige-ethics-lora \
    ./lora-adapters/

# 4. Update worker.ts to use the LoRA
# (See ../Buddhist Reference Archive/buddhist_worker_lora.js for example)
```

---

## Filtering Strategy

The converter filters experiences based on **both negative (harm) and positive (Buddhist principles) metrics**:

### Default Filters (Balanced)
```bash
python saige_to_sft.py \
    --max-harm 0.3 \         # Allow up to 30% harm
    --min-buddhist 6.0 \     # Require Buddhist score ≥ 6/10
    --min-alignment good     # Require "good" or "excellent" alignment
```

### Strict Filters (High Quality)
```bash
python saige_to_sft.py \
    --max-harm 0.2 \         # Max 20% harm
    --min-buddhist 7.0 \     # Require score ≥ 7/10
    --min-alignment excellent # Only "excellent" examples
```

### Permissive Filters (More Data)
```bash
python saige_to_sft.py \
    --max-harm 0.4 \         # Allow up to 40% harm
    --min-buddhist 5.0 \     # Require score ≥ 5/10
    --min-alignment moderate # Include "moderate" examples
```

**Trade-offs:**
- **Strict**: Higher quality, fewer examples (may underfit)
- **Balanced**: Good balance of quality and quantity
- **Permissive**: More examples, lower average quality (may learn sub-optimal patterns)

**Recommendation**: Start with default/balanced, then tighten filters as you collect more data.

---

## Troubleshooting

### "No experiences found matching criteria"

**Problem**: Database doesn't have enough high-quality experiences yet.

**Solutions:**
1. Collect more experiences: `node trainer.js 100`
2. Relax filters: `--max-harm 0.4 --min-buddhist 5.0`
3. Check database: `sqlite3 ../saige.db "SELECT COUNT(*) FROM experiences"`

### "CUDA out of memory"

**Problem**: Model too large for GPU.

**Solutions:**
1. Use 4-bit quantization: `--use-4bit`
2. Reduce batch size: `--batch-size 1`
3. Use smaller model: `--model TinyLlama/TinyLlama-1.1B-Chat-v1.0`
4. Use Google Colab with T4 or A100 GPU

### "Training loss not decreasing"

**Problem**: Learning rate or configuration issue.

**Solutions:**
1. Increase learning rate: `--learning-rate 5e-4`
2. Increase LoRA rank: `--lora-rank 32`
3. Train for more epochs: `--epochs 5`
4. Check data quality: Ensure examples are diverse and properly formatted

---

## Next Steps

After training:

1. **Evaluate the model** with Buddhist principle test suite (Priority 3)
2. **Deploy to SAIGE worker** to collect new experiences with the improved model
3. **Iterate**: The new model will generate better responses → more high-quality data → better next model

This creates a **continuous improvement loop**:
```
Better Model → Better Responses → Better Training Data → Better Model
```

---

## Files

- `saige_to_sft.py` - Experience to SFT converter (370 lines)
- `train_local.py` - Local fine-tuning script (280 lines)
- `train_pipeline.sh` - Complete pipeline orchestrator
- `requirements.txt` - Python dependencies
- `trainer.js` - Experience collection (existing)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 SAIGE Training Pipeline                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Experience Collection (trainer.js)                     │
│     └─> Worker API → Database (experiences table)          │
│                                                             │
│  2. Data Filtering (saige_to_sft.py)                       │
│     ├─ Query: harm < 0.3 AND buddhist > 6.0               │
│     ├─ Filter: alignment = 'good' or 'excellent'          │
│     └─> CSV file (text, harm_score, buddhist_scores)      │
│                                                             │
│  3. Format Conversion                                       │
│     ├─ TinyLlama: <|system|>...<|user|>...<|assistant|>   │
│     ├─ Mistral: <s>[INST]...[/INST]...</s>               │
│     └─ Llama3: <|begin_of_text|>...<|eot_id|>            │
│                                                             │
│  4. Fine-Tuning (train_local.py)                           │
│     ├─ LoRA/QLoRA parameter-efficient training            │
│     ├─ Optimized for Buddhist principles + harm reduction │
│     └─> Adapter weights (adapter_model.safetensors)       │
│                                                             │
│  5. Deployment                                              │
│     ├─ Local: Load adapter with base model                │
│     ├─ Cloudflare: Deploy LoRA to Workers AI              │
│     └─> Improved SAIGE model                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

**Generated**: 2026-01-29
**Priority**: 2 of 5
**Status**: Complete ✅
