-- Run this in Supabase SQL Editor to create persistent storage table
-- Go to: https://supabase.com/dashboard → your project → SQL Editor

CREATE TABLE IF NOT EXISTS system_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE system_state ENABLE ROW LEVEL SECURITY;

-- Allow all operations (the trading bot uses service key)
CREATE POLICY "Allow all" ON system_state
    FOR ALL USING (true) WITH CHECK (true);

-- Create trades table for persistent trade history
CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    pair TEXT,
    direction TEXT,
    entry_price NUMERIC,
    exit_price NUMERIC,
    sl_price NUMERIC,
    tp_price NUMERIC,
    units INTEGER,
    pnl NUMERIC,
    pnl_pips NUMERIC,
    confidence NUMERIC,
    regime TEXT,
    session TEXT,
    outcome TEXT,
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- This table stores: RL agent state, agent weights, FinMem, all learning data
-- Data survives Render restarts because it's in Supabase cloud
