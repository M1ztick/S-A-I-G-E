#!/bin/bash
# load-calibration-scenarios.sh
# Load conversational calibration scenarios to teach TinyLlama contextual awareness

set -e

echo "🧘 Loading Conversational Calibration Scenarios"
echo "================================================"
echo ""

# Find the database
DB_PATH=""

if [ -f "saige.db" ]; then
    DB_PATH="saige.db"
elif [ -f ".wrangler/state/v3/d1/miniflare-D1DatabaseObject/saige.db" ]; then
    DB_PATH=".wrangler/state/v3/d1/miniflare-D1DatabaseObject/saige.db"
else
    echo "❌ Could not find SAIGE database"
    echo ""
    echo "Options:"
    echo "  1. Local SQLite database:"
    echo "     sqlite3 saige.db < sql/seed_conversational_calibration.sql"
    echo ""
    echo "  2. Cloudflare D1 (remote):"
    echo "     wrangler d1 execute saige-db --file=sql/seed_conversational_calibration.sql"
    echo ""
    exit 1
fi

echo "📍 Found database: $DB_PATH"
echo ""

# Check current scenario count
CURRENT_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM scenarios" 2>/dev/null || echo "0")
echo "📊 Current scenarios in database: $CURRENT_COUNT"
echo ""

# Load the new scenarios
echo "📥 Loading conversational calibration scenarios..."
sqlite3 "$DB_PATH" < sql/seed_conversational_calibration.sql

# Check new count
NEW_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM scenarios")
ADDED=$((NEW_COUNT - CURRENT_COUNT))

echo "✅ Successfully loaded scenarios!"
echo ""
echo "📊 Statistics:"
echo "   Previous count: $CURRENT_COUNT"
echo "   New count: $NEW_COUNT"
echo "   Added: $ADDED scenarios"
echo ""

# Show breakdown by type
echo "📋 Scenario breakdown:"
sqlite3 "$DB_PATH" "SELECT difficulty_level, COUNT(*) as count FROM scenarios GROUP BY difficulty_level ORDER BY difficulty_level" | while read line; do
    echo "   Difficulty $line"
done
echo ""

sqlite3 "$DB_PATH" "SELECT harm_type, COUNT(*) as count FROM scenarios GROUP BY harm_type ORDER BY count DESC" | while read line; do
    HARM_TYPE=$(echo "$line" | cut -d'|' -f1)
    COUNT=$(echo "$line" | cut -d'|' -f2)
    echo "   $HARM_TYPE: $COUNT"
done
echo ""

echo "================================================"
echo "🎉 Calibration scenarios loaded!"
echo ""
echo "Next steps to train TinyLlama:"
echo ""
echo "1. Collect experiences with these scenarios:"
echo "   cd local-trainer && node trainer.js 100"
echo ""
echo "2. Convert to training data:"
echo "   python saige_to_sft.py --db ../saige.db"
echo ""
echo "3. Fine-tune TinyLlama:"
echo "   python train_local.py --data saige_training_data.csv --use-4bit"
echo ""
echo "4. Test the improved model:"
echo "   ollama run saige-tinyllama"
echo "   >>> Hello"
echo "   (Should now give a brief, calm response!)"
echo ""
echo "================================================"
