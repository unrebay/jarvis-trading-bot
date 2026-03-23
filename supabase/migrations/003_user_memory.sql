-- Migration 003: User memory / student portrait system
-- Each Telegram user gets one persistent memory row (JSONB)
-- Updated every N messages via Haiku extraction

CREATE TABLE IF NOT EXISTS user_memory (
  id           BIGSERIAL PRIMARY KEY,
  telegram_id  BIGINT UNIQUE NOT NULL,
  memory       JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_memory_telegram_id ON user_memory (telegram_id);

-- Auto-update updated_at on every write
CREATE TRIGGER update_user_memory_updated_at
  BEFORE UPDATE ON user_memory
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS: service role only (bot uses service key)
ALTER TABLE user_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_memory_service_all"
  ON user_memory
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');
