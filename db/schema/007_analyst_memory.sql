-- Long-term memory for analyst sessions
CREATE TABLE IF NOT EXISTS analyst_facts (
    id         SERIAL PRIMARY KEY,
    user_id    VARCHAR(255) NOT NULL,
    fact       TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, fact)
);

CREATE TABLE IF NOT EXISTS analyst_sessions (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    VARCHAR(255) NOT NULL,
    summary    TEXT NOT NULL,
    topics     TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analyst_facts_user ON analyst_facts(user_id);
CREATE INDEX idx_analyst_sessions_user ON analyst_sessions(user_id, created_at DESC);
