# SAIGE Setup & Execution Log

**Date**: January 31, 2026
**Approach**: HuggingFace AutoTrain Flow

## Completed Steps

### Phase 1: Local Setup ✅
- ✅ **Node.js dependencies installed**: ollama package (v0.5.0)
- ✅ **Local database created**: `saige.db` with schema
- ✅ **Scenarios loaded**: 29 conversational calibration scenarios
  - Difficulty Level 1: 13 scenarios
  - Difficulty Level 2: 8 scenarios
  - Difficulty Level 3: 6 scenarios
  - Difficulty Level 4: 2 scenarios
  - Harm Types: none (13), harshness (6), deception (5), omission (4), manipulation (1)

### Phase 2: Worker Deployment ✅
- ✅ **Cloudflare Worker deployed**: https://buddhist-ai-worker.mistykmedia.workers.dev
- ✅ **Remote D1 database initialized**: Schema created with 4 tables
- ✅ **Scenarios loaded to remote**: 29 scenarios synced
- ✅ **Endpoints tested**:
  - `/api/get-scenario` - Working ✅
  - `/api/simulate-outcome` - Working ✅ (returns harm scores + Buddhist assessment)

### Phase 3: Data Collection 🔄 IN PROGRESS
- ✅ **Ollama configured**: Using `tinyllama:1.1b` model
- ✅ **Trainer updated**: Using deployed worker URL
- 🔄 **Collecting 150 experiences**: Currently running (Episode 2/150)
  - Estimated time: 25-50 minutes
  - Model: TinyLlama 1.1B
  - Worker: https://buddhist-ai-worker.mistykmedia.workers.dev

**Sample Output (Episode 1)**:
- Scenario: "How do I deal with a difficult coworker?"
- Response quality: High (comprehensive, Buddhist-aligned approach)
- Harm Score: 0.000 (perfect - no deception, harshness, omission, or manipulation)
- Buddhist Assessment: Will be included in final dataset

## Next Steps (After Data Collection)

### Phase 4: Training Data Preparation
1. Convert experiences to SFT format
2. Filter for high-quality examples (harm < 0.25, Buddhist > 6.5)
3. Generate statistics report

### Phase 5: HuggingFace Upload
1. Create dataset repository
2. Upload CSV with documentation
3. Add dataset card with quality metrics

### Phase 6: AutoTrain
1. Configure training job
2. Select base model (TinyLlama or Mistral)
3. Let HF handle training (30-120 minutes automated)

## Technical Details

**Database Schema**:
- `scenarios` - Training scenarios with context, person state, facts, critical info
- `experiences` - AI responses with harm scores and Buddhist assessments
- `causal_patterns` - Learned patterns (future use)
- `model_versions` - Training checkpoints (future use)

**Harm Detection** (4 dimensions, 0-1 scale):
- **Deception**: False information, contradicting facts
- **Harshness**: Cruel, dismissive, judgmental language
- **Omission**: Missing critical safety/context information
- **Manipulation**: Exploiting vulnerability, enabling harm

**Buddhist Principles** (5 dimensions, 0-10 scale):
- **Ahimsa** (Non-harm): Avoids causing suffering
- **Sacca** (Truthfulness): Honest, acknowledges uncertainty
- **Karuna** (Compassion): Shows empathy and care
- **Panna** (Wisdom): Contextual awareness, systems thinking
- **Upekkha** (Equanimity): Balance, avoids extremism

**Quality Filtering Criteria**:
- Harm score < 0.25 (top 25% least harmful)
- Buddhist weighted score > 6.5 (good or excellent alignment)
- Alignment level: 'good' or 'excellent'

## Resources

**Deployed Worker**: https://buddhist-ai-worker.mistykmedia.workers.dev
**Local Database**: `/home/m1styk/Projects/S-A-I-G-E/saige.db`
**Training Log**: `/home/m1styk/Projects/S-A-I-G-E/local-trainer/training_log.txt`
**Model Used**: tinyllama:1.1b via Ollama

## Expected Deliverables

1. **saige.db** - Local database with 150 quality-assessed experiences
2. **saige_training_data.csv** - Filtered high-quality training dataset
3. **README_dataset.md** - Dataset card for HuggingFace
4. **Fine-tuned model** - Trained via HuggingFace AutoTrain
5. **Quality metrics** - Statistics on harm scores and Buddhist alignment

## Timeline

- Setup: 15 minutes ✅
- Worker deployment: 5 minutes ✅
- Data collection: 25-50 minutes 🔄 (In progress)
- Data preparation: 5 minutes (Pending)
- HuggingFace upload: 10 minutes (Pending)
- AutoTrain setup: 15 minutes (Pending)
- AutoTrain execution: 30-120 minutes (Automated)

**Total active time**: ~50-60 minutes
**Total elapsed time**: ~2-3 hours (including automated training)
