#!/usr/bin/env python3
"""
saige_to_sft.py

Converts SAIGE experiential learning data to Supervised Fine-Tuning (SFT) format.
Filters experiences by:
- Low harm scores (good responses)
- High Buddhist principle alignment
- Creates training data for TinyLlama/Mistral fine-tuning

Usage:
    python saige_to_sft.py --db saige.db --output training_data.csv
    python saige_to_sft.py --db saige.db --min-buddhist 7.0 --max-harm 0.25
"""

import sqlite3
import json
import csv
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class SAIGEToSFTConverter:
    """Converts SAIGE experiences to SFT training format."""

    def __init__(self, db_path: str):
        """Initialize converter with database path."""
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Connect to SAIGE database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        print(f"✅ Connected to database: {self.db_path}")

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print("✅ Database connection closed")

    def get_high_quality_experiences(
        self,
        max_harm: float = 0.3,
        min_buddhist_weighted: float = 6.0,
        min_buddhist_alignment: str = 'good',
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Query database for high-quality experiences suitable for training.

        Args:
            max_harm: Maximum harm score (0-1, lower is better)
            min_buddhist_weighted: Minimum Buddhist weighted score (0-10, higher is better)
            min_buddhist_alignment: Minimum alignment level ('moderate', 'good', 'excellent')
            limit: Maximum number of examples to return

        Returns:
            List of experience dictionaries
        """
        if not self.conn:
            raise RuntimeError("Not connected to database. Call connect() first.")

        # Map alignment levels to ordering
        alignment_order = {
            'excellent': 4,
            'good': 3,
            'moderate': 2,
            'low': 1
        }
        min_alignment_value = alignment_order.get(min_buddhist_alignment, 3)

        # Build query
        query = """
            SELECT
                e.id,
                e.scenario_id,
                e.ai_response,
                e.actual_harm,
                e.harm_breakdown,
                e.buddhist_scores,
                e.buddhist_alignment,
                e.timestamp,
                s.context,
                s.person_state,
                s.facts,
                s.critical_info,
                s.difficulty_level,
                s.harm_type
            FROM experiences e
            JOIN scenarios s ON e.scenario_id = s.id
            WHERE e.actual_harm <= ?
              AND e.buddhist_alignment IS NOT NULL
        """

        params = [max_harm]

        # Add alignment filter
        alignment_conditions = []
        if min_alignment_value >= 4:
            alignment_conditions = ['excellent']
        elif min_alignment_value >= 3:
            alignment_conditions = ['excellent', 'good']
        elif min_alignment_value >= 2:
            alignment_conditions = ['excellent', 'good', 'moderate']

        if alignment_conditions:
            placeholders = ','.join(['?' for _ in alignment_conditions])
            query += f" AND e.buddhist_alignment IN ({placeholders})"
            params.extend(alignment_conditions)

        query += " ORDER BY e.actual_harm ASC, e.timestamp DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()

        experiences = []
        for row in rows:
            # Parse JSON fields
            buddhist_scores = json.loads(row['buddhist_scores']) if row['buddhist_scores'] else {}

            # Calculate weighted score if available
            if buddhist_scores:
                weights = {
                    'ahimsa': 0.25,
                    'sacca': 0.20,
                    'karuna': 0.25,
                    'panna': 0.20,
                    'upekkha': 0.10
                }
                weighted_score = sum(
                    buddhist_scores.get(principle, 0) * weight
                    for principle, weight in weights.items()
                )
            else:
                weighted_score = 0

            # Skip if below minimum Buddhist score
            if weighted_score < min_buddhist_weighted:
                continue

            experiences.append({
                'id': row['id'],
                'scenario_id': row['scenario_id'],
                'context': row['context'],
                'person_state': json.loads(row['person_state']) if row['person_state'] else {},
                'facts': json.loads(row['facts']) if row['facts'] else [],
                'critical_info': json.loads(row['critical_info']) if row['critical_info'] else [],
                'difficulty_level': row['difficulty_level'],
                'harm_type': row['harm_type'],
                'ai_response': row['ai_response'],
                'actual_harm': row['actual_harm'],
                'harm_breakdown': json.loads(row['harm_breakdown']) if row['harm_breakdown'] else {},
                'buddhist_scores': buddhist_scores,
                'buddhist_alignment': row['buddhist_alignment'],
                'weighted_score': weighted_score,
                'timestamp': row['timestamp']
            })

        return experiences

    def format_for_tinyllama(self, context: str, person_state: Dict, response: str) -> str:
        """
        Format in TinyLlama/ChatML format.

        <|system|>
        You are a helpful AI assistant...</s>
        <|user|>
        Question</s>
        <|assistant|>
        Answer</s>
        """
        # Build system prompt
        system = "You are an AI assistant practicing ethical communication. You respond with wisdom, compassion, and truthfulness while minimizing harm."

        # Build user prompt with context
        user_prompt = f"{context}"

        # Add person state context if relevant
        if person_state:
            mood = person_state.get('mood', 'neutral')
            vulnerability = person_state.get('vulnerability', 'low')
            if mood != 'neutral' or vulnerability != 'low':
                user_prompt += f"\n\n[Context: Person is feeling {mood}, vulnerability level: {vulnerability}]"

        formatted = f"<|system|>\n{system}</s>\n<|user|>\n{user_prompt}</s>\n<|assistant|>\n{response}</s>"
        return formatted

    def format_for_mistral(self, context: str, person_state: Dict, response: str) -> str:
        """
        Format in Mistral instruction template.
        <s>[INST] prompt [/INST] response</s>
        """
        # Build prompt with context
        prompt = f"{context}"

        # Add person state context if relevant
        if person_state:
            mood = person_state.get('mood', 'neutral')
            vulnerability = person_state.get('vulnerability', 'low')
            if mood != 'neutral' or vulnerability != 'low':
                prompt += f"\n\nContext: Person is {mood}, vulnerability: {vulnerability}"

        formatted = f"<s>[INST] {prompt} [/INST] {response}</s>"
        return formatted

    def format_for_llama3(self, context: str, person_state: Dict, response: str) -> str:
        """
        Format in Llama 3 instruction template.
        <|begin_of_text|><|start_header_id|>system<|end_header_id|>
        System prompt<|eot_id|>
        <|start_header_id|>user<|end_header_id|>
        User message<|eot_id|>
        <|start_header_id|>assistant<|end_header_id|>
        Assistant response<|eot_id|>
        """
        system = "You are an AI assistant practicing ethical communication with wisdom and compassion."

        # Build user prompt
        user_prompt = f"{context}"
        if person_state:
            mood = person_state.get('mood', 'neutral')
            vulnerability = person_state.get('vulnerability', 'low')
            if mood != 'neutral' or vulnerability != 'low':
                user_prompt += f"\n\nContext: Person is {mood}, vulnerability: {vulnerability}"

        formatted = (
            f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
            f"{system}<|eot_id|>\n"
            f"<|start_header_id|>user<|end_header_id|>\n"
            f"{user_prompt}<|eot_id|>\n"
            f"<|start_header_id|>assistant<|end_header_id|>\n"
            f"{response}<|eot_id|>"
        )
        return formatted

    def convert_to_sft(
        self,
        experiences: List[Dict],
        format_type: str = 'mistral',
        output_file: str = 'saige_training_data.csv'
    ):
        """
        Convert experiences to SFT CSV format.

        Args:
            experiences: List of experience dictionaries
            format_type: 'tinyllama', 'mistral', or 'llama3'
            output_file: Output CSV file path
        """
        print(f"\n📝 Converting {len(experiences)} experiences to SFT format...")
        print(f"   Format: {format_type}")
        print(f"   Output: {output_file}")

        # Select formatting function
        format_functions = {
            'tinyllama': self.format_for_tinyllama,
            'mistral': self.format_for_mistral,
            'llama3': self.format_for_llama3
        }

        format_fn = format_functions.get(format_type, self.format_for_mistral)

        # Convert each experience
        training_examples = []
        for exp in experiences:
            formatted_text = format_fn(
                exp['context'],
                exp['person_state'],
                exp['ai_response']
            )

            training_examples.append({
                'text': formatted_text,
                'harm_score': exp['actual_harm'],
                'buddhist_alignment': exp['buddhist_alignment'],
                'weighted_score': exp['weighted_score'],
                'difficulty': exp['difficulty_level'],
                'scenario_id': exp['scenario_id'],
                'experience_id': exp['id']
            })

        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['text', 'harm_score', 'buddhist_alignment', 'weighted_score', 'difficulty', 'scenario_id', 'experience_id']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(training_examples)

        print(f"✅ Wrote {len(training_examples)} training examples to {output_file}")

        # Print statistics
        self._print_statistics(training_examples)

        return training_examples

    def _print_statistics(self, examples: List[Dict]):
        """Print statistics about the training data."""
        if not examples:
            return

        print(f"\n📊 Training Data Statistics:")
        print(f"   Total Examples: {len(examples)}")

        # Harm statistics
        avg_harm = sum(ex['harm_score'] for ex in examples) / len(examples)
        min_harm = min(ex['harm_score'] for ex in examples)
        max_harm = max(ex['harm_score'] for ex in examples)
        print(f"   Harm Score: avg={avg_harm:.3f}, min={min_harm:.3f}, max={max_harm:.3f}")

        # Buddhist alignment statistics
        avg_buddhist = sum(ex['weighted_score'] for ex in examples) / len(examples)
        min_buddhist = min(ex['weighted_score'] for ex in examples)
        max_buddhist = max(ex['weighted_score'] for ex in examples)
        print(f"   Buddhist Score: avg={avg_buddhist:.2f}, min={min_buddhist:.2f}, max={max_buddhist:.2f}")

        # Alignment distribution
        alignment_counts = {}
        for ex in examples:
            alignment = ex['buddhist_alignment']
            alignment_counts[alignment] = alignment_counts.get(alignment, 0) + 1

        print(f"   Alignment Distribution:")
        for alignment in ['excellent', 'good', 'moderate', 'low']:
            count = alignment_counts.get(alignment, 0)
            if count > 0:
                pct = (count / len(examples)) * 100
                print(f"     - {alignment}: {count} ({pct:.1f}%)")

        # Difficulty distribution
        difficulty_counts = {}
        for ex in examples:
            diff = ex['difficulty']
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

        print(f"   Difficulty Distribution:")
        for diff in sorted(difficulty_counts.keys()):
            count = difficulty_counts[diff]
            pct = (count / len(examples)) * 100
            print(f"     - Level {diff}: {count} ({pct:.1f}%)")

        # Sample example
        if examples:
            print(f"\n📋 Sample Training Example:")
            sample = examples[0]
            print(f"   Text (first 200 chars): {sample['text'][:200]}...")
            print(f"   Harm: {sample['harm_score']:.3f}, Buddhist: {sample['weighted_score']:.2f}, Alignment: {sample['buddhist_alignment']}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Convert SAIGE experiences to SFT training format'
    )
    parser.add_argument(
        '--db',
        default='../saige.db',
        help='Path to SAIGE database (default: ../saige.db)'
    )
    parser.add_argument(
        '--output',
        default='saige_training_data.csv',
        help='Output CSV file (default: saige_training_data.csv)'
    )
    parser.add_argument(
        '--format',
        choices=['tinyllama', 'mistral', 'llama3'],
        default='mistral',
        help='Training format (default: mistral)'
    )
    parser.add_argument(
        '--max-harm',
        type=float,
        default=0.3,
        help='Maximum harm score to include (default: 0.3)'
    )
    parser.add_argument(
        '--min-buddhist',
        type=float,
        default=6.0,
        help='Minimum Buddhist weighted score (default: 6.0)'
    )
    parser.add_argument(
        '--min-alignment',
        choices=['moderate', 'good', 'excellent'],
        default='good',
        help='Minimum Buddhist alignment level (default: good)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of examples (default: unlimited)'
    )

    args = parser.parse_args()

    print("🧘 SAIGE RL-to-SFT Training Data Converter")
    print("=" * 60)
    print(f"Database: {args.db}")
    print(f"Filters:")
    print(f"  - Max Harm: {args.max_harm}")
    print(f"  - Min Buddhist Score: {args.min_buddhist}")
    print(f"  - Min Alignment: {args.min_alignment}")
    if args.limit:
        print(f"  - Limit: {args.limit} examples")
    print()

    # Convert
    converter = SAIGEToSFTConverter(args.db)

    try:
        converter.connect()

        # Query high-quality experiences
        experiences = converter.get_high_quality_experiences(
            max_harm=args.max_harm,
            min_buddhist_weighted=args.min_buddhist,
            min_buddhist_alignment=args.min_alignment,
            limit=args.limit
        )

        if not experiences:
            print("❌ No experiences found matching criteria")
            print("   Try relaxing the filters:")
            print(f"   - Increase --max-harm (currently {args.max_harm})")
            print(f"   - Decrease --min-buddhist (currently {args.min_buddhist})")
            print(f"   - Lower --min-alignment (currently {args.min_alignment})")
            return

        print(f"✅ Found {len(experiences)} high-quality experiences")

        # Convert to SFT format
        converter.convert_to_sft(
            experiences,
            format_type=args.format,
            output_file=args.output
        )

        print(f"\n🎉 Conversion complete!")
        print(f"   Training data ready: {args.output}")
        print(f"\n💡 Next steps:")
        print(f"   1. Upload {args.output} to your training platform (Colab, HuggingFace, etc.)")
        print(f"   2. Fine-tune TinyLlama or Mistral with this data")
        print(f"   3. Deploy the improved model back to SAIGE")

    except FileNotFoundError:
        print(f"❌ Database not found: {args.db}")
        print(f"   Make sure the SAIGE worker has been running and collecting experiences")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        converter.disconnect()


if __name__ == '__main__':
    main()
