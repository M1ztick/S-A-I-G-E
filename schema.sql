-- schema.sql

-- Core scenarios table
CREATE TABLE IF NOT EXISTS scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context TEXT NOT NULL,
    person_state JSON NOT NULL,  -- emotional state, vulnerabilities, beliefs
    facts JSON,  -- known truths relevant to this scenario
    critical_info JSON,  -- information that must not be omitted
    difficulty_level INTEGER DEFAULT 1,  -- 1=simple, 5=complex
    harm_type TEXT,  -- primary harm risk: deception, harshness, omission, manipulation
    expected_response TEXT,  -- example of good response (for reference)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Experience tracking
CREATE TABLE IF NOT EXISTS experiences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id INTEGER NOT NULL,
    ai_response TEXT NOT NULL,
    predicted_harm REAL,
    actual_harm REAL NOT NULL,
    harm_breakdown JSON NOT NULL,  -- {deception: 0.1, harshness: 0.3, ...}
    learned_lesson TEXT,
    buddhist_scores JSON,  -- {ahimsa: 7.5, sacca: 8.2, karuna: 6.8, panna: 7.1, upekkha: 6.5}
    buddhist_alignment TEXT,  -- low, moderate, good, excellent
    model_version INTEGER DEFAULT 1,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scenario_id) REFERENCES scenarios(id)
);

-- Causal patterns the AI has learned
CREATE TABLE IF NOT EXISTS causal_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_name TEXT NOT NULL,
    pattern_type TEXT,  -- deception, harshness, omission, manipulation
    confidence REAL DEFAULT 0.5,
    example_count INTEGER DEFAULT 0,
    example_ids JSON,  -- array of experience IDs demonstrating this pattern
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Model checkpoint tracking
CREATE TABLE IF NOT EXISTS model_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_number INTEGER NOT NULL,
    episodes_trained INTEGER,
    avg_harm_last_100 REAL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_experiences_scenario ON experiences(scenario_id);
CREATE INDEX IF NOT EXISTS idx_experiences_timestamp ON experiences(timestamp);
CREATE INDEX IF NOT EXISTS idx_scenarios_difficulty ON scenarios(difficulty_level);
