#!/bin/bash

# Initialize the database with schema and seed data
echo "Initializing database..."

# Apply schema
npx wrangler d1 execute buddhist-ai-training --local --file=../schema.sql

# Apply seed data
npx wrangler d1 execute buddhist-ai-training --local --file=../sql/seed_scenarios.sql

echo "Database initialized!"