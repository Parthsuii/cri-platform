CREATE TABLE IF NOT EXISTS cognitive_events (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cognitive_events_created_at ON cognitive_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cognitive_events_event_type ON cognitive_events (event_type);
CREATE INDEX IF NOT EXISTS idx_cognitive_events_payload_gin ON cognitive_events USING GIN (payload);
