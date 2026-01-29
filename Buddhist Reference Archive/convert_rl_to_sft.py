#!/usr/bin/env python3
"""
convert_rl_to_sft.py

Convert reinforcement learning training data from Buddhist-AI-Training
to supervised fine-tuning format for LoRA adapter training.

Usage:
    python convert_rl_to_sft.py --input ../qwen3-vl:2b-instruct-buddhist-training.txt \
                                 --output buddhist_training_data.csv \
                                 --min_reward 7.0
"""

import json
import csv
import argparse
from pathlib import Path


def parse_rl_training_file(file_path):
    """
    Parse your RL training data file.
    Adapt this based on your actual file format.
    """
    examples = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # If it's JSON format
        try:
            data = json.loads(content)
            if isinstance(data, list):
                examples = data
            elif isinstance(data, dict) and 'examples' in data:
                examples = data['examples']
        except json.JSONDecodeError:
            # If it's line-delimited JSON
            for line in content.strip().split('\n'):
                if line.strip():
                    try:
                        examples.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    
    return examples


def score_buddhist_principles(response):
    """
    Score a response based on Buddhist ethical principles.
    This is a placeholder - you should implement your actual scoring logic.
    """
    keywords = {
        'non_harm': ['harm', 'ahimsa', 'non-violence', 'compassion', 'kindness'],
        'truthfulness': ['truth', 'honest', 'sacca', 'integrity'],
        'wisdom': ['wisdom', 'insight', 'panna', 'understanding', 'awareness'],
        'mindfulness': ['mindful', 'aware', 'present', 'attention', 'sati'],
        'compassion': ['compassion', 'karuna', 'loving-kindness', 'metta', 'empathy']
    }
    
    response_lower = response.lower()
    scores = {}
    
    for principle, words in keywords.items():
        score = sum(1 for word in words if word in response_lower)
        scores[principle] = min(score * 2, 10)  # Scale to 0-10
    
    return sum(scores.values()) / len(scores)


def format_for_mistral(scenario, response):
    """
    Format in Mistral instruction template.
    <s>[INST] prompt [/INST] response</s>
    """
    # Clean up the text
    scenario = scenario.strip()
    response = response.strip()
    
    # Wrap in quotes if contains newlines
    formatted = f'<s>[INST] {scenario} [/INST] {response}</s>'
    
    if '\n' in formatted:
        formatted = f'"{formatted}"'
    
    return formatted


def convert_rl_to_sft(input_file, output_file, min_reward=7.0, max_examples=None):
    """
    Main conversion function.
    """
    print(f"📖 Reading RL training data from: {input_file}")
    examples = parse_rl_training_file(input_file)
    print(f"   Found {len(examples)} examples")
    
    sft_examples = []
    skipped = 0
    
    for example in examples:
        # Adapt these keys to match your actual data structure
        scenario = example.get('scenario') or example.get('prompt') or example.get('situation')
        response = example.get('response') or example.get('completion') or example.get('output')
        reward = example.get('reward') or example.get('score')
        
        # If reward not present, calculate it
        if reward is None and response:
            reward = score_buddhist_principles(response)
        
        # Filter by reward threshold
        if reward and reward >= min_reward and scenario and response:
            formatted_text = format_for_mistral(scenario, response)
            sft_examples.append({'text': formatted_text})
        else:
            skipped += 1
    
    # Limit examples if specified
    if max_examples and len(sft_examples) > max_examples:
        sft_examples = sft_examples[:max_examples]
    
    # Write to CSV
    print(f"✍️  Writing {len(sft_examples)} examples to: {output_file}")
    print(f"   Skipped {skipped} examples below threshold")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['text'])
        writer.writeheader()
        writer.writerows(sft_examples)
    
    print(f"✅ Conversion complete!")
    print(f"   Output file: {output_file}")
    print(f"   Total examples: {len(sft_examples)}")
    
    # Print sample
    if sft_examples:
        print(f"\n📋 Sample example:")
        print(f"   {sft_examples[0]['text'][:200]}...")


def main():
    parser = argparse.ArgumentParser(
        description='Convert RL training data to SFT format for LoRA training'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Path to RL training data file'
    )
    parser.add_argument(
        '--output',
        default='buddhist_training_data.csv',
        help='Output CSV file path'
    )
    parser.add_argument(
        '--min-reward',
        type=float,
        default=7.0,
        help='Minimum reward threshold (0-10 scale)'
    )
    parser.add_argument(
        '--max-examples',
        type=int,
        default=None,
        help='Maximum number of examples to include'
    )
    
    args = parser.parse_args()
    
    convert_rl_to_sft(
        args.input,
        args.output,
        args.min_reward,
        args.max_examples
    )


if __name__ == '__main__':
    main()
