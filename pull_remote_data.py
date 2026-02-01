#!/usr/bin/env python3
"""
pull_remote_data.py
Pulls experiences from the remote D1 database (via wrangler) into local saige.db.
Runs wrangler d1 execute --remote to fetch JSON, then inserts into local SQLite.
"""
import subprocess
import json
import sqlite3
import sys


def extract_json(text):
    """Extract the JSON array from wrangler's mixed output (status lines + JSON)."""
    # Find the first '[' which starts the JSON array
    start = text.find('[')
    if start == -1:
        return None
    # Find the matching closing ']' by tracking bracket depth
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '[':
            depth += 1
        elif text[i] == ']':
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i+1])
    return None


def fetch_remote_experiences(batch_size=50):
    """Fetch all experiences from remote D1 via wrangler in batches."""
    all_experiences = []
    offset = 0

    while True:
        query = (
            f"SELECT id, scenario_id, ai_response, predicted_harm, actual_harm, "
            f"harm_breakdown, learned_lesson, buddhist_scores, buddhist_alignment, "
            f"model_version, timestamp FROM experiences LIMIT {batch_size} OFFSET {offset}"
        )

        result = subprocess.run(
            [
                "wrangler", "d1", "execute", "buddhist-ai-training",
                "--remote", "--command", query
            ],
            capture_output=True, text=True,
            cwd="/home/m1styk/Projects/S-A-I-G-E/worker"
        )

        if result.returncode != 0:
            print(f"❌ wrangler error: {result.stderr}", file=sys.stderr)
            break

        # Extract JSON from mixed wrangler output
        data = extract_json(result.stdout)
        if not data:
            print(f"❌ Could not parse JSON from wrangler output", file=sys.stderr)
            break

        rows = data[0]["results"] if data else []

        if not rows:
            break

        all_experiences.extend(rows)
        print(f"   Fetched {len(all_experiences)} experiences so far...")
        offset += batch_size

    return all_experiences


def insert_into_local(experiences, db_path="saige.db"):
    """Insert fetched experiences into local SQLite database."""
    conn = sqlite3.connect(db_path)

    conn.executemany(
        """
        INSERT OR REPLACE INTO experiences
            (id, scenario_id, ai_response, predicted_harm, actual_harm,
             harm_breakdown, learned_lesson, buddhist_scores, buddhist_alignment,
             model_version, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row["scenario_id"],
                row["ai_response"],
                row["predicted_harm"],
                row["actual_harm"],
                row["harm_breakdown"],
                row["learned_lesson"],
                row["buddhist_scores"],
                row["buddhist_alignment"],
                row["model_version"],
                row["timestamp"],
            )
            for row in experiences
        ]
    )

    conn.commit()
    conn.close()
    return len(experiences)


def main():
    print("📥 Pulling remote D1 experiences into local saige.db...")
    print()

    experiences = fetch_remote_experiences()

    if not experiences:
        print("❌ No experiences found on remote database.")
        sys.exit(1)

    print(f"\n✅ Fetched {len(experiences)} experiences from remote D1")

    db_path = "/home/m1styk/Projects/S-A-I-G-E/saige.db"
    count = insert_into_local(experiences, db_path)
    print(f"✅ Inserted {count} experiences into local database: {db_path}")

    # Quick stats
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT COUNT(*), AVG(actual_harm), MIN(actual_harm), MAX(actual_harm) FROM experiences").fetchone()
    print(f"\n📊 Local DB Summary:")
    print(f"   Total experiences: {row[0]}")
    print(f"   Avg harm:  {row[1]:.3f}")
    print(f"   Min harm:  {row[2]:.3f}")
    print(f"   Max harm:  {row[3]:.3f}")

    # Alignment distribution
    rows = conn.execute(
        "SELECT buddhist_alignment, COUNT(*) FROM experiences GROUP BY buddhist_alignment ORDER BY COUNT(*) DESC"
    ).fetchall()
    print(f"   Alignment distribution:")
    for alignment, cnt in rows:
        print(f"     {alignment}: {cnt}")

    conn.close()


if __name__ == "__main__":
    main()
