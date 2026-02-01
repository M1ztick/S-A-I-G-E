#!/usr/bin/env python3
"""Initialize SAIGE database with schema"""
import sqlite3
import sys

def init_database(db_path='saige.db', schema_path='schema.sql'):
    """Create database and execute schema"""
    try:
        # Read schema
        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        # Connect and execute
        conn = sqlite3.connect(db_path)
        conn.executescript(schema_sql)
        conn.commit()

        # Verify tables created
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        conn.close()

        print(f"✅ Database initialized: {db_path}")
        print(f"📊 Tables created: {', '.join(tables)}")
        return True

    except Exception as e:
        print(f"❌ Error initializing database: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)
